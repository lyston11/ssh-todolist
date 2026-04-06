from http import HTTPStatus
from importlib.resources import files
from pathlib import Path

from backend.http_responses import HttpResponsePayload, build_bytes_response


ADMIN_ROOT = files("backend.admin")
ADMIN_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


class AdminAssetNotFoundError(Exception):
    status_code = HTTPStatus.NOT_FOUND

    def __init__(self, message: str = "admin asset not found") -> None:
        super().__init__(message)
        self.message = message


def build_admin_asset_response(relative_path: str) -> HttpResponsePayload:
    normalized_path = (relative_path or "index.html").strip().lstrip("/")
    asset = ADMIN_ROOT.joinpath(normalized_path)
    if not asset.is_file():
        raise AdminAssetNotFoundError()

    return build_bytes_response(
        asset.read_bytes(),
        content_type=ADMIN_CONTENT_TYPES.get(Path(normalized_path).suffix, "application/octet-stream"),
        status=HTTPStatus.OK,
    )
