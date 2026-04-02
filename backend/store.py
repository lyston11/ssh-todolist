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
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    completed_at INTEGER
                )
                """
            )
            connection.commit()

    def list_todos(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, completed, created_at, updated_at, completed_at
                FROM todos
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [self._row_to_todo(row) for row in rows]

    def create_todo(self, title: str) -> dict:
        todo_id = str(uuid4())
        now = utc_ms()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO todos (id, title, completed, created_at, updated_at, completed_at)
                VALUES (?, ?, 0, ?, ?, NULL)
                """,
                (todo_id, title, now, now),
            )
            connection.commit()
        return self.get_todo(todo_id)

    def get_todo(self, todo_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, completed, created_at, updated_at, completed_at
                FROM todos
                WHERE id = ?
                """,
                (todo_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_todo(row)

    def update_todo(self, todo_id: str, title: str | None, completed: bool | None) -> dict | None:
        existing = self.get_todo(todo_id)
        if existing is None:
            return None

        next_title = title if title is not None else existing["title"]
        next_completed = completed if completed is not None else existing["completed"]
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
                SET title = ?, completed = ?, updated_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (next_title, int(next_completed), now, next_completed_at, todo_id),
            )
            connection.commit()

        return self.get_todo(todo_id)

    def delete_todo(self, todo_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            connection.commit()
        return cursor.rowcount > 0

    def clear_completed(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM todos WHERE completed = 1")
            connection.commit()
        return cursor.rowcount

    @staticmethod
    def _row_to_todo(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "completed": bool(row["completed"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "completedAt": row["completed_at"],
        }
