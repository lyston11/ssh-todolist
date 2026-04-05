import unittest
from unittest.mock import patch

from backend.connection import (
    build_connect_config,
    build_connect_link_payload,
    build_import_url,
    build_public_ws_url,
    encode_connect_config,
    has_trustworthy_remote_candidate,
    infer_request_base_url,
    render_qr_svg,
)


class ConnectionConfigTests(unittest.TestCase):
    @patch("backend.connection.discover_bind_hosts")
    def test_prefers_configured_public_base_url(self, mock_discover_bind_hosts) -> None:
        mock_discover_bind_hosts.return_value = [{"host": "100.88.77.66", "kind": "tailscale", "source": "tailscale"}]

        payload = build_connect_config(
            bind_host="0.0.0.0",
            http_port=8000,
            ws_port=8001,
            auth_token="secret-token",
            public_base_url="https://todo.example.com/",
            public_ws_base_url="wss://todo.example.com",
        )

        self.assertEqual(payload["serverUrl"], "https://todo.example.com")
        self.assertEqual(payload["wsUrl"], "wss://todo.example.com/ws")
        self.assertEqual(payload["wsPort"], None)
        self.assertTrue(payload["authRequired"])
        self.assertEqual(payload["token"], "")

    @patch("backend.connection.discover_bind_hosts")
    def test_prefers_request_host_when_present(self, mock_discover_bind_hosts) -> None:
        mock_discover_bind_hosts.return_value = [{"host": "100.88.77.66", "kind": "tailscale", "source": "tailscale"}]

        payload = build_connect_config(
            bind_host="0.0.0.0",
            http_port=8000,
            ws_port=8001,
            auth_token=None,
            request_headers={
                "Host": "100.88.77.66:8000",
                "X-Forwarded-Proto": "http",
            },
        )

        self.assertEqual(payload["serverUrl"], "http://100.88.77.66:8000")
        self.assertEqual(payload["wsUrl"], "ws://100.88.77.66:8001/ws")
        self.assertEqual(payload["candidates"][0]["source"], "request-host")

    @patch("backend.connection.discover_bind_hosts")
    def test_can_include_token_for_terminal_output(self, mock_discover_bind_hosts) -> None:
        mock_discover_bind_hosts.return_value = [{"host": "100.88.77.66", "kind": "tailscale", "source": "tailscale"}]

        payload = build_connect_config(
            bind_host="0.0.0.0",
            http_port=8000,
            ws_port=8001,
            auth_token="secret-token",
            include_token=True,
        )

        self.assertEqual(payload["token"], "secret-token")
        self.assertEqual(payload["serverUrl"], "http://100.88.77.66:8000")
        self.assertEqual(payload["wsUrl"], "ws://100.88.77.66:8001/ws")

    @patch("backend.connection.discover_bind_hosts")
    def test_builds_ipv6_candidate_urls_with_brackets(self, mock_discover_bind_hosts) -> None:
        mock_discover_bind_hosts.return_value = [{"host": "fd7a:115c:a1e0::1", "kind": "tailscale", "source": "tailscale"}]

        payload = build_connect_config(
            bind_host="0.0.0.0",
            http_port=8000,
            ws_port=8001,
            auth_token=None,
        )

        self.assertEqual(payload["serverUrl"], "http://[fd7a:115c:a1e0::1]:8000")
        self.assertEqual(payload["wsUrl"], "ws://[fd7a:115c:a1e0::1]:8001/ws")

    def test_infer_request_base_url_uses_forwarded_headers(self) -> None:
        self.assertEqual(
            infer_request_base_url(
                {
                    "Host": "127.0.0.1:8000",
                    "X-Forwarded-Host": "todo.example.com",
                    "X-Forwarded-Proto": "https",
                }
            ),
            "https://todo.example.com",
        )

    def test_build_public_ws_url_can_upgrade_http_scheme(self) -> None:
        self.assertEqual(
            build_public_ws_url(
                server_url="https://todo.example.com",
                ws_port=8001,
                public_ws_base_url="https://todo.example.com",
            ),
            "wss://todo.example.com/ws",
        )

    def test_can_encode_connect_config_for_import_link(self) -> None:
        self.assertEqual(
            encode_connect_config({"serverUrl": "http://100.88.77.66:8000", "token": "secret-token"}),
            "eyJzZXJ2ZXJVcmwiOiJodHRwOi8vMTAwLjg4Ljc3LjY2OjgwMDAiLCJ0b2tlbiI6InNlY3JldC10b2tlbiJ9",
        )

    def test_can_build_import_urls(self) -> None:
        config64 = "eyJzZXJ2ZXJVcmwiOiJodHRwOi8vMTAwLjg4Ljc3LjY2OjgwMDAifQ"
        self.assertEqual(
            build_import_url("https://app.example.com", config64),
            f"https://app.example.com?config64={config64}",
        )
        self.assertEqual(
            build_import_url("com.lyston11.sshtodolist://connect", config64),
            f"com.lyston11.sshtodolist://connect?config64={config64}",
        )

    def test_can_build_connect_link_payload(self) -> None:
        payload = build_connect_link_payload(
            connect_config={
                "serverUrl": "http://100.88.77.66:8000",
                "token": "secret-token",
                "authRequired": True,
                "wsUrl": "ws://100.88.77.66:8001/ws",
                "wsPort": 8001,
                "wsPath": "/ws",
                "candidates": [],
            },
            app_web_url="https://app.example.com",
            app_deep_link_base="com.lyston11.sshtodolist://connect",
        )

        self.assertIn("config64", payload)
        self.assertEqual(
            payload["deepLinkUrl"],
            f"com.lyston11.sshtodolist://connect?config64={payload['config64']}",
        )
        self.assertEqual(
            payload["webImportUrl"],
            f"https://app.example.com?config64={payload['config64']}",
        )
        self.assertEqual(payload["qrValue"], payload["deepLinkUrl"])
        self.assertEqual(
            payload["qrSvgUrl"],
            "http://100.88.77.66:8000/api/connect-link/qr.svg",
        )
        self.assertIn("Focus List 导入链接", payload["shortText"])

    def test_detects_trustworthy_remote_candidate(self) -> None:
        self.assertTrue(
            has_trustworthy_remote_candidate(
                [{"source": "configured-public-base-url", "kind": "configured"}]
            )
        )
        self.assertFalse(
            has_trustworthy_remote_candidate(
                [{"source": "hostname", "kind": "hostname"}]
            )
        )

    def test_can_render_qr_svg(self) -> None:
        svg = render_qr_svg("com.lyston11.sshtodolist://connect?config64=abc123")
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)


if __name__ == "__main__":
    unittest.main()
