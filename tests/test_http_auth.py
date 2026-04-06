import unittest

from backend.auth import AuthError
from backend.http_auth import require_api_request_auth


class HttpAuthTests(unittest.TestCase):
    def test_allows_request_when_auth_is_disabled(self) -> None:
        require_api_request_auth(None, {}, "/api/meta")

    def test_allows_valid_bearer_token(self) -> None:
        require_api_request_auth(
            "secret-token",
            {"Authorization": "Bearer secret-token"},
            "/api/meta",
        )

    def test_rejects_missing_token_when_auth_is_enabled(self) -> None:
        with self.assertRaises(AuthError) as ctx:
            require_api_request_auth("secret-token", {}, "/api/meta")

        self.assertEqual(ctx.exception.message, "missing or invalid token")


if __name__ == "__main__":
    unittest.main()
