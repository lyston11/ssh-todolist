import hmac
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse


class AuthError(Exception):
    status_code = HTTPStatus.UNAUTHORIZED

    def __init__(self, message: str = "missing or invalid token") -> None:
        super().__init__(message)
        self.message = message


def normalize_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def is_auth_enabled(expected_token: str | None) -> bool:
    return normalize_token(expected_token) is not None


def extract_token_from_authorization_header(header_value: str | None) -> str | None:
    if not header_value:
        return None

    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return normalize_token(token)


def extract_token_from_request(headers, path: str) -> str | None:
    header_token = extract_token_from_authorization_header(headers.get("Authorization"))
    if header_token is not None:
        return header_token

    query_token = parse_qs(urlparse(path).query).get("token", [None])[0]
    return normalize_token(query_token)


def validate_token(expected_token: str | None, provided_token: str | None) -> bool:
    normalized_expected = normalize_token(expected_token)
    if normalized_expected is None:
        return True

    normalized_provided = normalize_token(provided_token)
    if normalized_provided is None:
        return False

    return hmac.compare_digest(normalized_expected, normalized_provided)


def ensure_token(expected_token: str | None, provided_token: str | None) -> None:
    if not validate_token(expected_token, provided_token):
        raise AuthError()
