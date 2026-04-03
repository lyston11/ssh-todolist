import unittest

from backend.auth import (
    extract_token_from_authorization_header,
    normalize_token,
    validate_token,
)


class AuthTests(unittest.TestCase):
    def test_extracts_bearer_token(self) -> None:
        self.assertEqual(
            extract_token_from_authorization_header("Bearer abc123"),
            "abc123",
        )

    def test_rejects_non_bearer_header(self) -> None:
        self.assertIsNone(extract_token_from_authorization_header("Basic abc123"))

    def test_normalize_token_strips_whitespace(self) -> None:
        self.assertEqual(normalize_token("  hello  "), "hello")
        self.assertIsNone(normalize_token("   "))

    def test_validate_token(self) -> None:
        self.assertTrue(validate_token("secret", "secret"))
        self.assertFalse(validate_token("secret", "wrong"))


if __name__ == "__main__":
    unittest.main()
