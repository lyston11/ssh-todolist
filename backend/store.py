import sqlite3
import time
from pathlib import Path
from uuid import uuid4


def utc_ms() -> int:
    return int(time.time() * 1000)


class TodoStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS todo_lists (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    list_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    completed_at INTEGER,
                    FOREIGN KEY (list_id) REFERENCES todo_lists (id)
                )
                """
            )
            self._migrate_todos_schema(connection)
            self._ensure_default_list(connection)
            connection.commit()

    def list_lists(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM todo_lists
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [self._row_to_list(row) for row in rows]

    def list_todos(self, list_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            if list_id is None:
                rows = connection.execute(
                    """
                    SELECT id, list_id, title, completed, created_at, updated_at, completed_at
                    FROM todos
                    ORDER BY created_at DESC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, list_id, title, completed, created_at, updated_at, completed_at
                    FROM todos
                    WHERE list_id = ?
                    ORDER BY created_at DESC
                    """,
                    (list_id,),
                ).fetchall()
        return [self._row_to_todo(row) for row in rows]

    def get_default_list_id(self) -> str:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM todo_lists
                ORDER BY CASE WHEN id = 'default-list' THEN 0 ELSE 1 END, created_at ASC
                LIMIT 1
                """
            ).fetchone()
        return row["id"]

    def create_list(self, title: str, list_id: str | None = None) -> dict:
        list_id = list_id or str(uuid4())
        now = utc_ms()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO todo_lists (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (list_id, title, now, now),
            )
            connection.commit()
        return self.get_list(list_id)

    def get_list(self, list_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM todo_lists
                WHERE id = ?
                """,
                (list_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_list(row)

    def update_list(self, list_id: str, title: str) -> dict | None:
        now = utc_ms()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE todo_lists
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, now, list_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get_list(list_id)

    def delete_list(self, list_id: str) -> bool:
        with self._connect() as connection:
            connection.execute("DELETE FROM todos WHERE list_id = ?", (list_id,))
            cursor = connection.execute("DELETE FROM todo_lists WHERE id = ?", (list_id,))
            connection.commit()
        return cursor.rowcount > 0

    def create_todo(self, list_id: str, title: str, todo_id: str | None = None) -> dict:
        todo_id = todo_id or str(uuid4())
        now = utc_ms()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO todos (id, list_id, title, completed, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, 0, ?, ?, NULL)
                """,
                (todo_id, list_id, title, now, now),
            )
            connection.commit()
        return self.get_todo(todo_id)

    def get_todo(self, todo_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, list_id, title, completed, created_at, updated_at, completed_at
                FROM todos
                WHERE id = ?
                """,
                (todo_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_todo(row)

    def update_todo(
        self,
        todo_id: str,
        title: str | None,
        completed: bool | None,
        list_id: str | None = None,
    ) -> dict | None:
        existing = self.get_todo(todo_id)
        if existing is None:
            return None

        next_title = title if title is not None else existing["title"]
        next_completed = completed if completed is not None else existing["completed"]
        next_list_id = list_id if list_id is not None else existing["listId"]
        next_completed_at = existing["completedAt"]
        if completed is True:
            next_completed_at = utc_ms()
        if completed is False:
            next_completed_at = None

        now = utc_ms()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE todos
                SET list_id = ?, title = ?, completed = ?, updated_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (next_list_id, next_title, int(next_completed), now, next_completed_at, todo_id),
            )
            connection.commit()

        return self.get_todo(todo_id)

    def delete_todo(self, todo_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            connection.commit()
        return cursor.rowcount > 0

    def clear_completed(self, list_id: str | None = None) -> int:
        with self._connect() as connection:
            if list_id is None:
                cursor = connection.execute("DELETE FROM todos WHERE completed = 1")
            else:
                cursor = connection.execute(
                    "DELETE FROM todos WHERE completed = 1 AND list_id = ?",
                    (list_id,),
                )
            connection.commit()
        return cursor.rowcount

    @staticmethod
    def _row_to_todo(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "listId": row["list_id"],
            "title": row["title"],
            "completed": bool(row["completed"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "completedAt": row["completed_at"],
        }

    @staticmethod
    def _row_to_list(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def _ensure_default_list(self, connection: sqlite3.Connection) -> None:
        row = connection.execute("SELECT id FROM todo_lists LIMIT 1").fetchone()
        if row is not None:
            return

        now = utc_ms()
        connection.execute(
            """
            INSERT INTO todo_lists (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            ("default-list", "默认清单", now, now),
        )

    def _migrate_todos_schema(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(todos)").fetchall()
        }
        if "list_id" in columns:
            return

        connection.execute("ALTER TABLE todos ADD COLUMN list_id TEXT")
        default_list_id = "default-list"
        connection.execute(
            """
            UPDATE todos
            SET list_id = ?
            WHERE list_id IS NULL
            """,
            (default_list_id,),
        )
