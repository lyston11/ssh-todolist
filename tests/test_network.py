import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.network import _detect_tailscale_hosts, build_http_url, build_ws_url, classify_host


class NetworkTests(unittest.TestCase):
    def test_classify_host_recognizes_tailscale_ipv6(self) -> None:
        self.assertEqual(classify_host("fd7a:115c:a1e0::1"), "tailscale")

    def test_build_url_wraps_ipv6_hosts(self) -> None:
        self.assertEqual(build_http_url("fd7a:115c:a1e0::1", 8000), "http://[fd7a:115c:a1e0::1]:8000")
        self.assertEqual(build_ws_url("fd7a:115c:a1e0::1", 8001, "/ws"), "ws://[fd7a:115c:a1e0::1]:8001/ws")

    @patch("backend.network.shutil.which", return_value="/usr/bin/tailscale")
    @patch("backend.network.subprocess.run")
    def test_detect_tailscale_hosts_collects_ipv4_and_ipv6(self, mock_run, _mock_which) -> None:
        mock_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="100.88.77.66\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="fd7a:115c:a1e0::1\n", stderr=""),
        ]

        self.assertEqual(
            _detect_tailscale_hosts(),
            ["100.88.77.66", "fd7a:115c:a1e0::1"],
        )


if __name__ == "__main__":
    unittest.main()
