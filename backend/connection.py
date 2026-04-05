import base64
import json
from io import BytesIO
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import segno

from backend.auth import is_auth_enabled, normalize_token
from backend.network import build_http_url, build_ws_url, discover_bind_hosts
from backend.store import utc_ms


DEFAULT_WS_PATH = "/ws"
DEFAULT_APP_DEEP_LINK_BASE = "com.lyston11.sshtodolist://connect"
DEFAULT_QR_SVG_PATH = "/api/connect-link/qr.svg"
TRUSTED_REMOTE_SOURCES = {"configured-public-base-url", "request-host", "tailscale"}
TRUSTED_REMOTE_KINDS = {"public", "tailscale"}
TRUSTED_BIND_KINDS = {"lan", "public", "tailscale"}


def build_connect_config(
    *,
    bind_host: str,
    http_port: int,
    ws_port: int,
    auth_token: str | None,
    request_headers=None,
    public_base_url: str | None = None,
    public_ws_base_url: str | None = None,
    include_token: bool = False,
) -> dict:
    candidates = []
    seen_server_urls: set[str] = set()

    configured_candidate = _build_configured_candidate(
        public_base_url=public_base_url,
        http_port=http_port,
        ws_port=ws_port,
        public_ws_base_url=public_ws_base_url,
    )
    if configured_candidate is not None:
        _append_candidate(candidates, seen_server_urls, configured_candidate)

    request_candidate = _build_request_candidate(
        request_headers=request_headers,
        ws_port=ws_port,
        public_ws_base_url=public_ws_base_url,
    )
    if request_candidate is not None:
        _append_candidate(candidates, seen_server_urls, request_candidate)

    for host_candidate in discover_bind_hosts(bind_host):
        _append_candidate(
            candidates,
            seen_server_urls,
            {
                "kind": host_candidate["kind"],
                "source": host_candidate["source"],
                "host": host_candidate["host"],
                "serverUrl": build_http_url(host_candidate["host"], http_port),
                "wsUrl": build_ws_url(host_candidate["host"], ws_port, DEFAULT_WS_PATH),
            },
        )

    if not candidates:
        fallback_server_url = normalize_base_url(public_base_url) or build_http_url("127.0.0.1", http_port)
        candidates.append(
            {
                "kind": "fallback",
                "source": "fallback",
                "host": "127.0.0.1",
                "serverUrl": fallback_server_url,
                "wsUrl": build_public_ws_url(
                    server_url=fallback_server_url,
                    ws_port=ws_port,
                    public_ws_base_url=public_ws_base_url,
                ),
            }
        )

    preferred = candidates[0]
    normalized_token = normalize_token(auth_token)
    token_required = is_auth_enabled(auth_token)

    return {
        "serverUrl": preferred["serverUrl"],
        "token": normalized_token if include_token and normalized_token is not None else "",
        "authRequired": token_required,
        "wsUrl": preferred["wsUrl"],
        "wsPort": extract_url_port(preferred["wsUrl"]),
        "wsPath": DEFAULT_WS_PATH,
        "candidates": candidates,
        "time": utc_ms(),
    }


def build_connect_link_payload(
    *,
    connect_config: dict,
    app_web_url: str | None = None,
    app_deep_link_base: str | None = None,
) -> dict:
    encoded_config = encode_connect_config(connect_config)
    normalized_app_web_url = normalize_base_url(app_web_url)
    normalized_deep_link_base = normalize_link_base(app_deep_link_base or DEFAULT_APP_DEEP_LINK_BASE)
    web_import_url = build_import_url(normalized_app_web_url, encoded_config)
    deep_link_url = build_import_url(normalized_deep_link_base, encoded_config)
    qr_value = deep_link_url or web_import_url or encoded_config
    qr_svg_url = build_qr_svg_url(connect_config.get("serverUrl", ""))
    short_text = build_share_text(
        server_url=connect_config.get("serverUrl", ""),
        deep_link_url=deep_link_url,
        web_import_url=web_import_url,
        auth_required=connect_config.get("authRequired") is True,
    )

    return {
        "config64": encoded_config,
        "deepLinkUrl": deep_link_url,
        "webImportUrl": web_import_url,
        "qrValue": qr_value,
        "qrSvgPath": DEFAULT_QR_SVG_PATH,
        "qrSvgUrl": qr_svg_url,
        "shortText": short_text,
        "time": utc_ms(),
    }


def encode_connect_config(connect_config: dict) -> str:
    payload = json.dumps(connect_config, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


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


def build_share_text(
    *,
    server_url: str,
    deep_link_url: str,
    web_import_url: str,
    auth_required: bool,
) -> str:
    lines = [
        "Focus List 导入链接",
        f"节点: {server_url}",
    ]
    if deep_link_url:
        lines.append(f"App 导入: {deep_link_url}")
    if web_import_url:
        lines.append(f"Web 导入: {web_import_url}")
    if auth_required:
        lines.append("注意: 链接内包含访问 token，只分享给自己的设备。")
    return "\n".join(lines)


def build_qr_svg_url(server_url: str) -> str:
    normalized_server_url = normalize_base_url(server_url)
    if normalized_server_url is None:
        return ""
    return f"{normalized_server_url}{DEFAULT_QR_SVG_PATH}"


def render_qr_svg(value: str, scale: int = 8, border: int = 2) -> str:
    qr = segno.make(value, error="m", micro=False)
    output = BytesIO()
    qr.save(output, kind="svg", scale=scale, border=border, xmldecl=False)
    return output.getvalue().decode("utf-8")


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


def has_trustworthy_remote_candidate(candidates: list[dict] | None) -> bool:
    for candidate in candidates or []:
        source = str(candidate.get("source", "")).strip()
        kind = str(candidate.get("kind", "")).strip()
        if source in TRUSTED_REMOTE_SOURCES:
            return True
        if kind in TRUSTED_REMOTE_KINDS:
            return True
        if source == "bind" and kind in TRUSTED_BIND_KINDS:
            return True
    return False


def _append_candidate(candidates: list[dict], seen_server_urls: set[str], candidate: dict) -> None:
    server_url = candidate["serverUrl"]
    if server_url in seen_server_urls:
        return

    seen_server_urls.add(server_url)
    candidates.append(candidate)


def _build_configured_candidate(
    *,
    public_base_url: str | None,
    http_port: int,
    ws_port: int,
    public_ws_base_url: str | None,
) -> dict | None:
    normalized_public_base_url = normalize_base_url(public_base_url)
    if normalized_public_base_url is None:
        return None

    parsed = urlsplit(normalized_public_base_url)
    host = parsed.hostname or "configured-host"
    return {
        "kind": "configured",
        "source": "configured-public-base-url",
        "host": host,
        "serverUrl": normalized_public_base_url,
        "wsUrl": build_public_ws_url(
            server_url=normalized_public_base_url,
            ws_port=ws_port,
            public_ws_base_url=public_ws_base_url,
        ),
    }


def _build_request_candidate(*, request_headers, ws_port: int, public_ws_base_url: str | None) -> dict | None:
    request_base_url = infer_request_base_url(request_headers)
    if request_base_url is None:
        return None

    parsed = urlsplit(request_base_url)
    return {
        "kind": "request",
        "source": "request-host",
        "host": parsed.hostname or "request-host",
        "serverUrl": request_base_url,
        "wsUrl": build_public_ws_url(
            server_url=request_base_url,
            ws_port=ws_port,
            public_ws_base_url=public_ws_base_url,
        ),
    }


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
