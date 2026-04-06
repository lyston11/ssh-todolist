import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.service import TodoService
from backend.store import TODO_COMPLETED_LIST_INDEX, TODO_LIST_ID_INDEX, TodoStore


class DummyHub:
    def broadcast_snapshot_sync(self) -> None:
        return


class TodoStoreTests(unittest.TestCase):
    def test_store_enables_foreign_keys_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "todos.db"
            store = TodoStore(db_path)

            with store._connect() as connection:
                foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
                indexes = {
                    row["name"]
                    for row in connection.execute("PRAGMA index_list('todos')").fetchall()
                }

            self.assertEqual(foreign_keys, 1)
            self.assertIn(TODO_LIST_ID_INDEX, indexes)
            self.assertIn(TODO_COMPLETED_LIST_INDEX, indexes)

    def test_store_rejects_todo_for_missing_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TodoStore(Path(tmpdir) / "todos.db")

            with self.assertRaises(sqlite3.IntegrityError):
                store.create_todo("missing-list", "不应该创建成功")

    def test_store_list_and_todo_crud_and_clear_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TodoStore(Path(tmpdir) / "todos.db")
            work_list = store.create_list("工作", list_id="work-list")

            todo = store.create_todo(work_list["id"], "写接口测试", todo_id="todo-1", tag="开发")
            self.assertEqual(todo["title"], "写接口测试")
            self.assertEqual(todo["tag"], "开发")

            updated = store.update_todo(
                todo["id"],
                "写 HTTP 接口测试",
                True,
                due_at=1760086400000,
                due_at_provided=True,
            )
            self.assertEqual(updated["title"], "写 HTTP 接口测试")
            self.assertTrue(updated["completed"])
            self.assertEqual(updated["dueAt"], 1760086400000)

            active_todo = store.create_todo(work_list["id"], "保留任务", todo_id="todo-2")
            cleared_count = store.clear_completed(work_list["id"])
            self.assertEqual(cleared_count, 1)
            self.assertIsNone(store.get_todo(todo["id"]))
            self.assertIsNotNone(store.get_todo(active_todo["id"]))

            self.assertTrue(store.delete_todo(active_todo["id"]))
            self.assertIsNone(store.get_todo(active_todo["id"]))

            renamed = store.update_list(work_list["id"], "工作台")
            self.assertEqual(renamed["title"], "工作台")
            self.assertTrue(store.delete_list(work_list["id"]))
            self.assertIsNone(store.get_list(work_list["id"]))

    def test_create_todo_without_list_id_uses_default_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TodoStore(Path(tmpdir) / "todos.db")
            service = TodoService(store=store, hub=DummyHub(), host="0.0.0.0", port=8000, ws_port=8001)
            store.create_list("第二个清单", list_id="second-list")

            todo = service.create_todo({"title": "未显式指定清单"})

            self.assertEqual(store.get_default_list_id(), "default-list")
            self.assertEqual(todo["listId"], "default-list")

    def test_create_and_update_todo_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TodoStore(Path(tmpdir) / "todos.db")
            service = TodoService(store=store, hub=DummyHub(), host="0.0.0.0", port=8000, ws_port=8001)

            todo = service.create_todo({"title": "整理节点配置", "tag": "系统"})
            self.assertEqual(todo["tag"], "系统")

            updated = service.update_todo(todo["id"], {"tag": "工作"})
            self.assertEqual(updated["tag"], "工作")

            cleared = service.update_todo(todo["id"], {"tag": ""})
            self.assertEqual(cleared["tag"], "")

    def test_create_and_update_todo_due_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TodoStore(Path(tmpdir) / "todos.db")
            service = TodoService(store=store, hub=DummyHub(), host="0.0.0.0", port=8000, ws_port=8001)

            todo = service.create_todo({"title": "准备周会", "dueAt": 1760000000000})
            self.assertEqual(todo["dueAt"], 1760000000000)

            updated = service.update_todo(todo["id"], {"dueAt": 1760086400000})
            self.assertEqual(updated["dueAt"], 1760086400000)

            cleared = service.update_todo(todo["id"], {"dueAt": None})
            self.assertIsNone(cleared["dueAt"])


if __name__ == "__main__":
    unittest.main()
