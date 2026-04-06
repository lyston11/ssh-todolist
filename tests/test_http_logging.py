import unittest
from unittest.mock import patch

from backend.http_logging import (
    HTTP_LOG_MODE_ALL,
    HTTP_LOG_MODE_ERRORS,
    HTTP_LOG_MODE_OFF,
    build_http_access_log_message,
    normalize_http_log_mode,
    should_log_http_request,
)
from backend.http_server import create_http_server


class HttpLoggingTests(unittest.TestCase):
    def test_normalize_http_log_mode_defaults_to_errors(self) -> None:
        self.assertEqual(normalize_http_log_mode(None), HTTP_LOG_MODE_ERRORS)
        self.assertEqual(normalize_http_log_mode(" ALL "), HTTP_LOG_MODE_ALL)
        self.assertEqual(normalize_http_log_mode("invalid"), HTTP_LOG_MODE_ERRORS)

    def test_should_log_http_request_honors_mode(self) -> None:
        self.assertFalse(should_log_http_request(HTTP_LOG_MODE_OFF, 500))
        self.assertFalse(should_log_http_request(HTTP_LOG_MODE_ERRORS, 200))
        self.assertTrue(should_log_http_request(HTTP_LOG_MODE_ERRORS, 404))
        self.assertTrue(should_log_http_request(HTTP_LOG_MODE_ALL, 200))

    def test_build_http_access_log_message_contains_core_fields(self) -> None:
        message = build_http_access_log_message(
            client_ip="127.0.0.1",
            method="GET",
            path="/api/health",
            status_code=200,
            size=128,
            duration_ms=12.5,
        )

        self.assertIn('client="127.0.0.1"', message)
        self.assertIn('method="GET"', message)
        self.assertIn('path="/api/health"', message)
        self.assertIn("status=200", message)
        self.assertIn("size=128", message)
        self.assertIn("duration_ms=12.50", message)

    @patch("backend.http_server.SyncHTTPServer")
    def test_create_http_server_forwards_http_log_mode(self, mock_server_class) -> None:
        create_http_server(
            "127.0.0.1",
            8000,
            store=object(),
            hub=object(),
            ws_port=8001,
            http_log_mode="ALL",
        )

        self.assertEqual(mock_server_class.call_args.kwargs["http_log_mode"], "ALL")


if __name__ == "__main__":
    unittest.main()
