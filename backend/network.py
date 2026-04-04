import ipaddress
import shutil
import socket
import subprocess


TAILSCALE_IPV4_NETWORK = ipaddress.ip_network("100.64.0.0/10")
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

    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
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
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = ipaddress.ip_address(line)
        except ValueError:
            continue
        if parsed.version == 4:
            hosts.append(line)
    return hosts


def _detect_hostname_hosts() -> list[str]:
    names = {socket.gethostname(), socket.getfqdn()}
    hosts: list[str] = []
    seen: set[str] = set()

    for name in names:
        if not name:
            continue
        try:
            infos = socket.getaddrinfo(name, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
        except OSError:
            continue

        for info in infos:
            host = info[4][0].strip()
            if not host or host in seen or host.startswith("127."):
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
