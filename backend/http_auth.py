from backend.auth import AuthError, ensure_token, extract_token_from_request


def require_api_request_auth(expected_token: str | None, headers, path: str) -> None:
    provided_token = extract_token_from_request(headers, path)
    ensure_token(expected_token, provided_token)
