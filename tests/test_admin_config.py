import json
import tempfile
import unittest
from pathlib import Path

from backend.admin_config import AdminConfigSnapshot, AdminConfigStore, build_default_admin_config_store
from backend.service_errors import ValidationError


class AdminConfigStoreTests(unittest.TestCase):
    def test_default_store_uses_defaults_and_persists_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            store = build_default_admin_config_store(
                data_dir=data_dir,
                public_base_url="https://todo.example.com/",
                public_ws_base_url="wss://todo.example.com/",
                app_web_url="https://app.example.com/",
                app_deep_link_base="com.lyston11.sshtodolist://connect/",
                http_log_mode="errors",
            )

            self.assertEqual(store.snapshot().public_base_url, "https://todo.example.com")
            self.assertEqual(store.snapshot().public_ws_base_url, "wss://todo.example.com")
            self.assertEqual(store.snapshot().app_web_url, "https://app.example.com")
            self.assertEqual(store.snapshot().app_deep_link_base, "com.lyston11.sshtodolist://connect")
            self.assertEqual(store.snapshot().http_log_mode, "errors")

            updated = store.update(
                {
                    "publicBaseUrl": "https://todo-updated.example.com/",
                    "publicWsBaseUrl": "wss://todo-updated.example.com/",
                    "appWebUrl": "https://app-updated.example.com/",
                    "appDeepLinkBase": "com.lyston11.sshtodolist://import/",
                    "httpLogMode": "all",
                }
            )

            self.assertEqual(updated["publicBaseUrl"], "https://todo-updated.example.com")
            self.assertEqual(updated["publicWsBaseUrl"], "wss://todo-updated.example.com")
            self.assertEqual(updated["appWebUrl"], "https://app-updated.example.com")
            self.assertEqual(updated["appDeepLinkBase"], "com.lyston11.sshtodolist://import")
            self.assertEqual(updated["httpLogMode"], "all")

            reloaded = AdminConfigStore(
                store.path,
                defaults=AdminConfigSnapshot(),
            )
            self.assertEqual(reloaded.snapshot().public_base_url, "https://todo-updated.example.com")
            self.assertEqual(reloaded.snapshot().public_ws_base_url, "wss://todo-updated.example.com")
            self.assertEqual(reloaded.snapshot().app_web_url, "https://app-updated.example.com")
            self.assertEqual(reloaded.snapshot().app_deep_link_base, "com.lyston11.sshtodolist://import")
            self.assertEqual(reloaded.snapshot().http_log_mode, "all")

    def test_invalid_persisted_config_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config_path = data_dir / "service-settings.json"
            config_path.write_text(
                json.dumps(
                    {
                        "publicBaseUrl": "not-a-valid-url",
                        "httpLogMode": "definitely-invalid",
                    }
                ),
                encoding="utf-8",
            )

            store = build_default_admin_config_store(
                data_dir=data_dir,
                public_base_url="https://todo.example.com/",
                public_ws_base_url=None,
                app_web_url=None,
                app_deep_link_base="com.lyston11.sshtodolist://connect/",
                http_log_mode="errors",
            )

            self.assertEqual(store.snapshot().public_base_url, "https://todo.example.com")
            self.assertIsNone(store.snapshot().public_ws_base_url)
            self.assertEqual(store.snapshot().http_log_mode, "errors")

    def test_update_rejects_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = build_default_admin_config_store(
                data_dir=Path(tmpdir),
                public_base_url=None,
                public_ws_base_url=None,
                app_web_url=None,
                app_deep_link_base="com.lyston11.sshtodolist://connect/",
                http_log_mode="errors",
            )

            with self.assertRaises(ValidationError):
                store.update({"publicBaseUrl": "ftp://todo.example.com"})

            with self.assertRaises(ValidationError):
                store.update({"httpLogMode": "verbose"})


if __name__ == "__main__":
    unittest.main()
