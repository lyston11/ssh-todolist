import tempfile
import unittest
from pathlib import Path

from backend.admin_dashboard import build_admin_overview
from backend.connection import build_connect_config, build_connect_link_payload
from backend.store import TodoStore, utc_ms


class DashboardTests(unittest.TestCase):
    def test_build_admin_overview_includes_totals_and_database_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "todos.db"
            store = TodoStore(db_path)
            second_list = store.create_list("工作台", list_id="work-list")
            store.create_todo("default-list", "默认任务", todo_id="todo-1")
            todo = store.create_todo(second_list["id"], "发布服务", todo_id="todo-2", due_at=4102444800000)
            store.update_todo(todo["id"], None, True)
            store.create_todo(second_list["id"], "今天巡检", todo_id="todo-4", due_at=utc_ms())
            store.create_todo(second_list["id"], "排查同步", todo_id="todo-3", due_at=946684800000)

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
                admin_entry_path="/",
                admin_alias_path="/admin",
            )

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["totals"]["lists"], 2)
            self.assertEqual(payload["totals"]["todos"], 4)
            self.assertEqual(payload["totals"]["activeTodos"], 3)
            self.assertEqual(payload["totals"]["completedTodos"], 1)
            self.assertEqual(payload["totals"]["scheduledTodos"], 2)
            self.assertEqual(payload["totals"]["unscheduledTodos"], 1)
            self.assertEqual(payload["totals"]["dueTodayTodos"], 1)
            self.assertEqual(payload["totals"]["overdueTodos"], 1)
            self.assertEqual(payload["defaultListId"], "default-list")
            self.assertTrue(payload["database"]["exists"])
            self.assertGreaterEqual(payload["database"]["sizeBytes"], 0)
            self.assertEqual(payload["server"]["wsPort"], 8001)
            self.assertIn("connectLink", payload)
            self.assertEqual(payload["runtime"]["adminUrl"], f"{connect_config['serverUrl']}/")
            self.assertEqual(payload["runtime"]["adminAliasUrl"], f"{connect_config['serverUrl']}/admin")
            self.assertEqual(payload["runtime"]["healthUrl"], f"{connect_config['serverUrl']}/api/health")
            self.assertEqual(payload["runtime"]["connectLinkUrl"], f"{connect_config['serverUrl']}/api/connect-link")
            self.assertEqual(payload["runtime"]["wsPort"], 8001)
            self.assertTrue(payload["runtime"]["authRequired"])
            self.assertEqual(payload["runtime"]["databasePath"], str(db_path))
            install_methods = payload["install"]["methods"]
            self.assertEqual([method["id"] for method in install_methods], ["script", "source", "docker", "compose"])
            self.assertEqual([method["title"] for method in install_methods], ["一键脚本", "源码运行", "Docker 单容器", "Docker Compose"])
            self.assertEqual([method["recommended"] for method in install_methods], [True, False, False, True])
            self.assertEqual(len(payload["recentTodos"]), 4)

            work_list_summary = next(item for item in payload["lists"] if item["id"] == "work-list")
            self.assertEqual(work_list_summary["todoCount"], 3)
            self.assertEqual(work_list_summary["dueTodayTodoCount"], 1)
            self.assertEqual(work_list_summary["overdueTodoCount"], 1)

            recent_due_buckets = {item["id"]: item["dueBucket"] for item in payload["recentTodos"]}
            self.assertEqual(recent_due_buckets["todo-2"], "completed")
            self.assertEqual(recent_due_buckets["todo-3"], "overdue")
            self.assertEqual(recent_due_buckets["todo-4"], "today")
            self.assertEqual(recent_due_buckets["todo-1"], "unscheduled")

            recent_list_titles = {item["id"]: item["listTitle"] for item in payload["recentTodos"]}
            self.assertEqual(recent_list_titles["todo-2"], "工作台")
            self.assertEqual(recent_list_titles["todo-3"], "工作台")
            self.assertEqual(recent_list_titles["todo-4"], "工作台")


if __name__ == "__main__":
    unittest.main()
