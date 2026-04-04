import tempfile
import unittest
from pathlib import Path

from backend.admin_dashboard import build_admin_overview
from backend.connection import build_connect_config, build_connect_link_payload
from backend.store import TodoStore


class DashboardTests(unittest.TestCase):
    def test_build_admin_overview_includes_totals_and_database_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "todos.db"
            store = TodoStore(db_path)
            second_list = store.create_list("工作台", list_id="work-list")
            store.create_todo("default-list", "默认任务", todo_id="todo-1")
            todo = store.create_todo(second_list["id"], "发布服务", todo_id="todo-2")
            store.update_todo(todo["id"], None, True)

            snapshot = {
                "lists": store.list_lists(),
                "items": store.list_todos(),
                "defaultListId": store.get_default_list_id(),
            }
            connect_config = build_connect_config(
                bind_host="0.0.0.0",
                http_port=8000,
                ws_port=8001,
                auth_token="secret-token",
                include_token=True,
            )
            connect_link = build_connect_link_payload(connect_config=connect_config)

            payload = build_admin_overview(
                snapshot=snapshot,
                connect_config=connect_config,
                connect_link=connect_link,
                auth_required=True,
                db_path=db_path,
                ws_port=8001,
            )

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["totals"]["lists"], 2)
            self.assertEqual(payload["totals"]["todos"], 2)
            self.assertEqual(payload["totals"]["activeTodos"], 1)
            self.assertEqual(payload["totals"]["completedTodos"], 1)
            self.assertTrue(payload["database"]["exists"])
            self.assertGreaterEqual(payload["database"]["sizeBytes"], 0)
            self.assertEqual(payload["server"]["wsPort"], 8001)
            self.assertIn("connectLink", payload)
            self.assertEqual(len(payload["recentTodos"]), 2)


if __name__ == "__main__":
    unittest.main()
