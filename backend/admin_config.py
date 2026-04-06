import json
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

from backend.connection_urls import DEFAULT_APP_DEEP_LINK_BASE, normalize_base_url, normalize_link_base
from backend.http_logging import DEFAULT_HTTP_LOG_MODE, HTTP_LOG_MODES, normalize_http_log_mode
from backend.service_errors import ValidationError
from backend.store import utc_ms


CONFIG_FILENAME = "service-settings.json"


@dataclass(frozen=True)
class AdminConfigSnapshot:
    public_base_url: str | None = None
    public_ws_base_url: str | None = None
    app_web_url: str | None = None
    app_deep_link_base: str = DEFAULT_APP_DEEP_LINK_BASE
    http_log_mode: str = DEFAULT_HTTP_LOG_MODE


class AdminConfigStore:
    def __init__(self, path: Path, defaults: AdminConfigSnapshot | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._snapshot = defaults or AdminConfigSnapshot()
        self._load()

    def snapshot(self) -> AdminConfigSnapshot:
        with self._lock:
            return replace(self._snapshot)

    def to_payload(self) -> dict:
        snapshot = self.snapshot()
        return {
            "publicBaseUrl": snapshot.public_base_url or "",
            "publicWsBaseUrl": snapshot.public_ws_base_url or "",
            "appWebUrl": snapshot.app_web_url or "",
            "appDeepLinkBase": snapshot.app_deep_link_base,
            "httpLogMode": snapshot.http_log_mode,
            "configPath": str(self.path),
            "time": utc_ms(),
        }

    def update(self, payload: dict) -> dict:
        normalized_payload = payload if isinstance(payload, dict) else {}
        with self._lock:
            self._snapshot = _build_snapshot_from_payload(normalized_payload, fallback=self._snapshot)
            self._save_locked()

        return self.to_payload()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(payload, dict):
            return

        try:
            self._snapshot = _build_snapshot_from_payload(payload, fallback=self._snapshot)
        except ValidationError:
            return

    def _save_locked(self) -> None:
        snapshot = self._snapshot
        payload = {
            "publicBaseUrl": snapshot.public_base_url or "",
            "publicWsBaseUrl": snapshot.public_ws_base_url or "",
            "appWebUrl": snapshot.app_web_url or "",
            "appDeepLinkBase": snapshot.app_deep_link_base,
            "httpLogMode": snapshot.http_log_mode,
            "configPath": str(self.path),
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def build_default_admin_config_store(
    *,
    data_dir: Path,
    public_base_url: str | None,
    public_ws_base_url: str | None,
    app_web_url: str | None,
    app_deep_link_base: str | None,
    http_log_mode: str,
) -> AdminConfigStore:
    defaults = AdminConfigSnapshot(
        public_base_url=_coerce_http_url(public_base_url, field_name="publicBaseUrl"),
        public_ws_base_url=_coerce_ws_url(public_ws_base_url, field_name="publicWsBaseUrl"),
        app_web_url=_coerce_http_url(app_web_url, field_name="appWebUrl"),
        app_deep_link_base=_coerce_deep_link_base(app_deep_link_base or DEFAULT_APP_DEEP_LINK_BASE),
        http_log_mode=_coerce_http_log_mode(http_log_mode),
    )
    return AdminConfigStore(data_dir / CONFIG_FILENAME, defaults=defaults)


def _build_snapshot_from_payload(
    payload: dict,
    *,
    fallback: AdminConfigSnapshot,
) -> AdminConfigSnapshot:
    return AdminConfigSnapshot(
        public_base_url=_coerce_http_url(
            payload.get("publicBaseUrl", fallback.public_base_url),
            field_name="publicBaseUrl",
        ),
        public_ws_base_url=_coerce_ws_url(
            payload.get("publicWsBaseUrl", fallback.public_ws_base_url),
            field_name="publicWsBaseUrl",
        ),
        app_web_url=_coerce_http_url(
            payload.get("appWebUrl", fallback.app_web_url),
            field_name="appWebUrl",
        ),
        app_deep_link_base=_coerce_deep_link_base(
            payload.get("appDeepLinkBase", fallback.app_deep_link_base),
        ),
        http_log_mode=_coerce_http_log_mode(
            payload.get("httpLogMode", fallback.http_log_mode),
        ),
    )


def _coerce_http_url(value: object, *, field_name: str) -> str | None:
    normalized = normalize_base_url(_coerce_optional_string(value))
    if normalized is None:
        return None

    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(f"{field_name} 必须是合法的 http(s) 地址")
    return normalized


def _coerce_ws_url(value: object, *, field_name: str) -> str | None:
    normalized = normalize_link_base(_coerce_optional_string(value))
    if normalized is None:
        return None

    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https", "ws", "wss"} or not parsed.netloc:
        raise ValidationError(f"{field_name} 必须是合法的 ws/wss/http/https 地址")
    return normalized


def _coerce_deep_link_base(value: object) -> str:
    normalized = normalize_link_base(_coerce_optional_string(value))
    if normalized is None:
        raise ValidationError("appDeepLinkBase 不能为空，且必须是合法的导入链接基址")
    return normalized


def _coerce_http_log_mode(value: object) -> str:
    raw_value = _coerce_optional_string(value)
    if raw_value is None:
        return DEFAULT_HTTP_LOG_MODE

    normalized = raw_value.lower()
    if normalized not in HTTP_LOG_MODES:
        raise ValidationError("httpLogMode 非法")
    return normalized


def _coerce_optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
