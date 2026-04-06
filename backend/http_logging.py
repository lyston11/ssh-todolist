import logging


HTTP_LOGGER_NAME = "ssh_todolist.http"
HTTP_LOG_MODE_OFF = "off"
HTTP_LOG_MODE_ERRORS = "errors"
HTTP_LOG_MODE_ALL = "all"
DEFAULT_HTTP_LOG_MODE = HTTP_LOG_MODE_ERRORS
HTTP_LOG_MODES = {
    HTTP_LOG_MODE_OFF,
    HTTP_LOG_MODE_ERRORS,
    HTTP_LOG_MODE_ALL,
}


def normalize_http_log_mode(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in HTTP_LOG_MODES:
        return normalized
    return DEFAULT_HTTP_LOG_MODE


def should_log_http_request(mode: str, status_code: int | None) -> bool:
    normalized_mode = normalize_http_log_mode(mode)
    if normalized_mode == HTTP_LOG_MODE_OFF:
        return False
    if normalized_mode == HTTP_LOG_MODE_ALL:
        return True
    return status_code is not None and status_code >= 400


def build_http_access_log_message(
    *,
    client_ip: str,
    method: str,
    path: str,
    status_code: int | None,
    size: int | None = None,
    duration_ms: float | None = None,
) -> str:
    parts = [
        "access",
        f'client="{client_ip}"',
        f'method="{method}"',
        f'path="{path}"',
        f"status={status_code if status_code is not None else '-'}",
    ]
    if size is not None:
        parts.append(f"size={size}")
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms:.2f}")
    return " ".join(parts)


def get_http_logger() -> logging.Logger:
    return logging.getLogger(HTTP_LOGGER_NAME)
