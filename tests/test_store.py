import tempfile
import unittest
from pathlib import Path

from backend.service import TodoService
from backend.store import TodoStore


class DummyHub:
    def broadcast_snapshot_sync(self) -> None:
        return


class TodoStoreTests(unittest.TestCase):
    def test_create_todo_without_list_id_uses_default_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TodoStore(Path(tmpdir) / "todos.db")
            service = TodoService(store=store, hub=DummyHub(), host="0.0.0.0", port=8000, ws_port=8001)
            store.create_list("第二个清单", list_id="second-list")

            todo = service.create_todo({"title": "未显式指定清单"})

            self.assertEqual(store.get_default_list_id(), "default-list")
            self.assertEqual(todo["listId"], "default-list")


if __name__ == "__main__":
    unittest.main()
