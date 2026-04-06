from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.network import build_ws_url


DEFAULT_WS_PATH = "/ws"
DEFAULT_QR_SVG_PATH = "/api/connect-link/qr.svg"
DEFAULT_APP_DEEP_LINK_BASE = "com.lyston11.sshtodolist://connect"


def build_import_url(base_url: str | None, config64: str) -> str:
    normalized_base_url = normalize_link_base(base_url)
    if normalized_base_url is None:
        return ""

    parsed = urlsplit(normalized_base_url)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    query_items = [(key, value) for key, value in query_items if key != "config64"]
    query_items.append(("config64", config64))
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query_items),
            parsed.fragment,
        )
    )


def build_qr_svg_url(server_url: str) -> str:
    normalized_server_url = normalize_base_url(server_url)
    if normalized_server_url is None:
        return ""
    return f"{normalized_server_url}{DEFAULT_QR_SVG_PATH}"


def build_public_ws_url(
    *,
    server_url: str,
    ws_port: int,
    public_ws_base_url: str | None = None,
) -> str:
    normalized_public_ws_base = normalize_base_url(public_ws_base_url)
    if normalized_public_ws_base:
        parsed = urlsplit(normalized_public_ws_base)
        scheme = _normalize_ws_scheme(parsed.scheme)
        return urlunsplit((scheme, parsed.netloc, DEFAULT_WS_PATH, "", ""))

    parsed_server_url = urlsplit(server_url)
    scheme = "wss" if parsed_server_url.scheme == "https" else "ws"
    host = parsed_server_url.hostname or "127.0.0.1"
    return build_ws_url(host, ws_port, DEFAULT_WS_PATH).replace("ws://", f"{scheme}://", 1)


def extract_url_port(url: str) -> int | None:
    parsed = urlsplit(url)
    try:
        return parsed.port
    except ValueError:
        return None


def normalize_base_url(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().rstrip("/")
    return normalized or None


def normalize_link_base(value: str | None) -> str | None:
    normalized = normalize_base_url(value)
    if normalized is None:
        return None
    parsed = urlsplit(normalized)
    if not parsed.scheme:
        return None
    return normalized


def infer_request_base_url(headers) -> str | None:
    if headers is None:
        return None

    forwarded_host = _extract_first_header_value(headers.get("X-Forwarded-Host"))
    host = forwarded_host or _extract_first_header_value(headers.get("Host"))
    if host is None:
        return None

    forwarded_proto = _extract_first_header_value(headers.get("X-Forwarded-Proto"))
    scheme = forwarded_proto or "http"
    return normalize_base_url(f"{scheme}://{host}")


def _extract_first_header_value(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.split(",", 1)[0].strip()
    return normalized or None


def _normalize_ws_scheme(scheme: str) -> str:
    if scheme == "https":
        return "wss"
    if scheme == "http":
        return "ws"
    if scheme in {"ws", "wss"}:
        return scheme
    return "ws"
