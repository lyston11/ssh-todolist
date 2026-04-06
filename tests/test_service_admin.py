import tempfile
import unittest
from pathlib import Path

from backend.admin_activity import AdminActivityFeed
from backend.admin_config import build_default_admin_config_store
from backend.realtime import WebSocketHub
from backend.service import TodoService
from backend.store import TodoStore


class ServiceAdminTests(unittest.TestCase):
    def _build_service(self, tmpdir: str) -> TodoService:
        store = TodoStore(Path(tmpdir) / "todos.db")
        hub = WebSocketHub(store)
        config_store = build_default_admin_config_store(
            data_dir=Path(tmpdir),
            public_base_url="https://todo.example.com/",
            public_ws_base_url="wss://todo.example.com/",
            app_web_url="https://app.example.com/",
            app_deep_link_base="com.lyston11.sshtodolist://connect/",
            http_log_mode="errors",
        )
        activity_feed = AdminActivityFeed()
        return TodoService(
            store=store,
            hub=hub,
            host="0.0.0.0",
            port=8000,
            ws_port=8001,
            auth_token="secret-token",
            admin_config_store=config_store,
            admin_activity_feed=activity_feed,
        )

    def test_admin_config_payload_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = self._build_service(tmpdir)

            initial = service.get_admin_config_payload()
            self.assertTrue(initial["authRequired"])
            self.assertEqual(initial["publicBaseUrl"], "https://todo.example.com")
            self.assertEqual(initial["httpLogMode"], "errors")

            updated = service.update_admin_config(
                {
                    "publicBaseUrl": "https://todo-updated.example.com",
                    "httpLogMode": "all",
                }
            )
            self.assertEqual(updated["publicBaseUrl"], "https://todo-updated.example.com")
            self.assertEqual(updated["httpLogMode"], "all")

            connect_config = service.get_connect_config_payload()
            self.assertEqual(connect_config["serverUrl"], "https://todo-updated.example.com")

            activity = service.get_admin_activity_payload()
            self.assertEqual(activity["count"], 1)
            self.assertEqual(activity["items"][0]["kind"], "config.updated")
            self.assertIn("公共 HTTP 地址", activity["items"][0]["detail"])
            self.assertIn("HTTP 日志模式", activity["items"][0]["detail"])

    def test_activity_feed_collects_recent_service_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = self._build_service(tmpdir)

            created_list = service.create_list({"title": "工作", "id": "work-list"})
            created_todo = service.create_todo({"title": "联调同步", "listId": created_list["id"]})
            service.update_todo(created_todo["id"], {"completed": True})
            service.clear_completed_todos({"listId": created_list["id"]})

            activity = service.get_admin_activity_payload()
            self.assertEqual(activity["count"], 4)
            self.assertEqual(
                [item["kind"] for item in activity["items"]],
                [
                    "todo.cleared_completed",
                    "todo.updated",
                    "todo.created",
                    "list.created",
                ],
            )

    def test_activity_feed_uses_entity_titles_for_delete_and_clear_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = self._build_service(tmpdir)

            created_list = service.create_list({"title": "工作", "id": "work-list"})
            created_todo = service.create_todo({"title": "联调同步", "listId": created_list["id"]})
            service.delete_todo(created_todo["id"])
            service.clear_completed_todos({"listId": created_list["id"]})
            service.delete_list(created_list["id"])

            activity = service.get_admin_activity_payload()
            details_by_kind = {item["kind"]: item["detail"] for item in activity["items"]}
            self.assertIn("任务“联调同步”已删除。", details_by_kind["todo.deleted"])
            self.assertIn("清单“工作”中的 0 条已完成任务。", details_by_kind["todo.cleared_completed"])
            self.assertIn("清单“工作”已删除。", details_by_kind["list.deleted"])


if __name__ == "__main__":
    unittest.main()
