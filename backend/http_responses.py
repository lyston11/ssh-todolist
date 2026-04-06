import json
from dataclasses import dataclass
from http import HTTPStatus


JSON_CONTENT_TYPE = "application/json; charset=utf-8"
SVG_CONTENT_TYPE = "image/svg+xml; charset=utf-8"


@dataclass(frozen=True)
class HttpResponsePayload:
    body: bytes
    content_type: str
    status: HTTPStatus = HTTPStatus.OK


class JsonBodyError(Exception):
    status_code = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def parse_json_object(raw_body: bytes) -> dict:
    try:
        parsed = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as error:
        raise JsonBodyError("invalid json") from error

    if not isinstance(parsed, dict):
        raise JsonBodyError("json body must be an object")

    return parsed


def build_bytes_response(
    payload: bytes,
    *,
    content_type: str,
    status: HTTPStatus = HTTPStatus.OK,
) -> HttpResponsePayload:
    return HttpResponsePayload(
        body=payload,
        content_type=content_type,
        status=status,
    )


def build_text_response(
    payload: str,
    *,
    content_type: str,
    status: HTTPStatus = HTTPStatus.OK,
) -> HttpResponsePayload:
    return build_bytes_response(
        payload.encode("utf-8"),
        content_type=content_type,
        status=status,
    )


def build_json_response(payload: dict, status: HTTPStatus = HTTPStatus.OK) -> HttpResponsePayload:
    return build_text_response(
        json.dumps(payload, ensure_ascii=False),
        content_type=JSON_CONTENT_TYPE,
        status=status,
    )


def build_json_error_response(status: HTTPStatus, message: str) -> HttpResponsePayload:
    return build_json_response({"error": message}, status=status)
