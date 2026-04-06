import base64
import json
from io import BytesIO

import segno

from backend.connection_urls import (
    DEFAULT_APP_DEEP_LINK_BASE,
    DEFAULT_QR_SVG_PATH,
    build_import_url,
    build_qr_svg_url,
    normalize_base_url,
    normalize_link_base,
)
from backend.store import utc_ms


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


def build_share_text(
    *,
    server_url: str,
    deep_link_url: str,
    web_import_url: str,
    auth_required: bool,
) -> str:
    lines = [
        "SSH Todo 导入链接",
        f"节点: {server_url}",
    ]
    if deep_link_url:
        lines.append(f"App 导入: {deep_link_url}")
    if web_import_url:
        lines.append(f"Web 导入: {web_import_url}")
    if auth_required:
        lines.append("注意: 链接内包含访问 token，只分享给自己的设备。")
    return "\n".join(lines)


def render_qr_svg(value: str, scale: int = 8, border: int = 2) -> str:
    qr = segno.make(value, error="m", micro=False)
    output = BytesIO()
    qr.save(output, kind="svg", scale=scale, border=border, xmldecl=False)
    return output.getvalue().decode("utf-8")
