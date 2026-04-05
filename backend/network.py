import ipaddress
import shutil
import socket
import subprocess


TAILSCALE_IPV4_NETWORK = ipaddress.ip_network("100.64.0.0/10")
TAILSCALE_IPV6_NETWORK = ipaddress.ip_network("fd7a:115c:a1e0::/48")
WILDCARD_HOSTS = {"", "0.0.0.0", "::", "[::]"}


def discover_bind_hosts(bind_host: str | None) -> list[dict]:
    normalized_bind_host = (bind_host or "").strip()
    if normalized_bind_host and normalized_bind_host not in WILDCARD_HOSTS:
        return [_build_host_candidate(normalized_bind_host, source="bind")]

    hosts: list[dict] = []
    seen: set[str] = set()

    for host in _detect_tailscale_hosts():
        _append_candidate(hosts, seen, host, source="tailscale")

    for host in _detect_hostname_hosts():
        _append_candidate(hosts, seen, host, source="hostname")

    for host in ("127.0.0.1", "localhost"):
        _append_candidate(hosts, seen, host, source="loopback")

    return hosts


def build_http_url(host: str, port: int) -> str:
    return f"http://{_format_host_for_url(host)}:{port}"


def build_ws_url(host: str, port: int, path: str) -> str:
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"ws://{_format_host_for_url(host)}:{port}{normalized_path}"


def classify_host(host: str) -> str:
    normalized_host = host.strip()
    if not normalized_host:
        return "unknown"

    if normalized_host == "localhost":
        return "loopback"

    try:
        parsed = ipaddress.ip_address(normalized_host)
    except ValueError:
        return "hostname"

    if parsed.version == 4 and parsed in TAILSCALE_IPV4_NETWORK:
        return "tailscale"
    if parsed.version == 6 and parsed in TAILSCALE_IPV6_NETWORK:
        return "tailscale"
    if parsed.is_loopback:
        return "loopback"
    if parsed.is_private:
        return "lan"
    return "public"


def _append_candidate(hosts: list[dict], seen: set[str], host: str, source: str) -> None:
    normalized_host = host.strip()
    if not normalized_host or normalized_host in seen or normalized_host in WILDCARD_HOSTS:
        return

    seen.add(normalized_host)
    hosts.append(_build_host_candidate(normalized_host, source=source))


def _build_host_candidate(host: str, source: str) -> dict:
    return {
        "host": host,
        "kind": classify_host(host),
        "source": source,
    }


def _detect_tailscale_hosts() -> list[str]:
    if shutil.which("tailscale") is None:
        return []

    hosts: list[str] = []
    seen: set[str] = set()
    for flag in ("-4", "-6"):
        for host in _run_tailscale_ip_command(flag):
            if host in seen:
                continue
            seen.add(host)
            hosts.append(host)
    return hosts


def _run_tailscale_ip_command(flag: str) -> list[str]:
    try:
        result = subprocess.run(
            ["tailscale", "ip", flag],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0:
        return []

    hosts: list[str] = []
    for raw_line in result.stdout.splitlines():
        line = _normalize_detected_host(raw_line)
        if not line:
            continue
        try:
            ipaddress.ip_address(line)
        except ValueError:
            continue
        hosts.append(line)
    return hosts


def _detect_hostname_hosts() -> list[str]:
    names = {socket.gethostname(), socket.getfqdn()}
    hosts: list[str] = []
    seen: set[str] = set()

    for name in names:
        if not name:
            continue
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                infos = socket.getaddrinfo(name, None, family=family, type=socket.SOCK_STREAM)
            except OSError:
                continue

            for info in infos:
                host = _normalize_detected_host(info[4][0])
                if not host or host in seen:
                    continue

                try:
                    parsed = ipaddress.ip_address(host)
                except ValueError:
                    parsed = None

                if parsed is not None and (parsed.is_loopback or parsed.is_link_local or parsed.is_unspecified):
                    continue

                seen.add(host)
                hosts.append(host)

    return hosts


def _format_host_for_url(host: str) -> str:
    try:
        parsed = ipaddress.ip_address(host)
    except ValueError:
        return host
    if parsed.version == 6:
        return f"[{host}]"
    return host


def _normalize_detected_host(host: str) -> str:
    return host.strip().split("%", 1)[0]
