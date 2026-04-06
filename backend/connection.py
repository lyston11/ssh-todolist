from backend.auth import is_auth_enabled, normalize_token
from backend.connection_links import (
    build_connect_link_payload,
    build_share_text,
    encode_connect_config,
    render_qr_svg,
)
from backend.connection_urls import (
    DEFAULT_APP_DEEP_LINK_BASE,
    DEFAULT_QR_SVG_PATH,
    DEFAULT_WS_PATH,
    build_import_url,
    build_public_ws_url,
    build_qr_svg_url,
    extract_url_port,
    infer_request_base_url,
    normalize_base_url,
    normalize_link_base,
)
from backend.network import build_http_url, build_ws_url, discover_bind_hosts
from backend.store import utc_ms


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
    ws_port: int,
    public_ws_base_url: str | None,
) -> dict | None:
    normalized_public_base_url = normalize_base_url(public_base_url)
    if normalized_public_base_url is None:
        return None

    host = _extract_hostname(normalized_public_base_url) or "configured-host"
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

    return {
        "kind": "request",
        "source": "request-host",
        "host": _extract_hostname(request_base_url) or "request-host",
        "serverUrl": request_base_url,
        "wsUrl": build_public_ws_url(
            server_url=request_base_url,
            ws_port=ws_port,
            public_ws_base_url=public_ws_base_url,
        ),
    }


def _extract_hostname(url: str) -> str | None:
    normalized = normalize_link_base(url)
    if normalized is None:
        return None

    from urllib.parse import urlsplit

    parsed = urlsplit(normalized)
    return parsed.hostname


__all__ = [
    "DEFAULT_APP_DEEP_LINK_BASE",
    "DEFAULT_QR_SVG_PATH",
    "DEFAULT_WS_PATH",
    "TRUSTED_BIND_KINDS",
    "TRUSTED_REMOTE_KINDS",
    "TRUSTED_REMOTE_SOURCES",
    "build_connect_config",
    "build_connect_link_payload",
    "build_import_url",
    "build_public_ws_url",
    "build_qr_svg_url",
    "build_share_text",
    "encode_connect_config",
    "extract_url_port",
    "has_trustworthy_remote_candidate",
    "infer_request_base_url",
    "normalize_base_url",
    "normalize_link_base",
    "render_qr_svg",
]
