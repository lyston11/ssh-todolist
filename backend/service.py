from dataclasses import dataclass

from backend.auth import is_auth_enabled
from backend.realtime import WebSocketHub
from backend.store import TodoStore, utc_ms


class TodoServiceError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(TodoServiceError):
    status_code = 400


class NotFoundError(TodoServiceError):
    status_code = 404


@dataclass
class TodoService:
    store: TodoStore
    hub: WebSocketHub
    ws_port: int
    auth_token: str | None = None

    def get_health_payload(self) -> dict:
        return {
            "status": "ok",
            "time": utc_ms(),
            "wsPort": self.ws_port,
            "authRequired": is_auth_enabled(self.auth_token),
        }

    def get_meta_payload(self) -> dict:
        return {
            "wsPort": self.ws_port,
            "wsPath": "/ws",
            "time": utc_ms(),
            "authRequired": is_auth_enabled(self.auth_token),
        }

    def get_snapshot_payload(self) -> dict:
        lists = self.store.list_lists()
        default_list_id = self.store.get_default_list_id() if lists else None
        return {
            "lists": lists,
            "items": self.store.list_todos(),
            "defaultListId": default_list_id,
            "time": utc_ms(),
        }

    def list_todos_payload(self) -> dict:
        snapshot = self.get_snapshot_payload()
        return {
            "items": snapshot["items"],
            "lists": snapshot["lists"],
            "defaultListId": snapshot["defaultListId"],
            "time": snapshot["time"],
        }

    def list_lists_payload(self) -> dict:
        snapshot = self.get_snapshot_payload()
        return {
            "items": snapshot["lists"],
            "defaultListId": snapshot["defaultListId"],
            "time": snapshot["time"],
        }

    def create_list(self, payload: dict) -> dict:
        title = self._normalize_list_title(payload)
        todo_list = self.store.create_list(title, list_id=self._normalize_optional_id(payload))
        self.hub.broadcast_snapshot_sync()
        return todo_list

    def update_list(self, list_id: str, payload: dict) -> dict:
        title = self._normalize_list_title(payload)
        todo_list = self.store.update_list(list_id, title)
        if todo_list is None:
            raise NotFoundError("list not found")

        self.hub.broadcast_snapshot_sync()
        return todo_list

    def delete_list(self, list_id: str) -> dict:
        lists = self.store.list_lists()
        if len(lists) <= 1:
            raise ValidationError("至少保留一个清单")

        deleted = self.store.delete_list(list_id)
        if not deleted:
            raise NotFoundError("list not found")

        self.hub.broadcast_snapshot_sync()
        return {"deleted": True}

    def create_todo(self, payload: dict) -> dict:
        title = self._normalize_create_title(payload)
        list_id = self._normalize_list_id(payload)
        todo = self.store.create_todo(list_id, title, todo_id=self._normalize_optional_id(payload))
        self.hub.broadcast_snapshot_sync()
        return todo

    def update_todo(self, todo_id: str, payload: dict) -> dict:
        title = self._normalize_update_title(payload)
        completed = self._normalize_completed(payload)
        list_id = self._normalize_optional_list_id(payload)

        todo = self.store.update_todo(todo_id, title, completed, list_id=list_id)
        if todo is None:
            raise NotFoundError("todo not found")

        self.hub.broadcast_snapshot_sync()
        return todo

    def delete_todo(self, todo_id: str) -> dict:
        deleted = self.store.delete_todo(todo_id)
        if not deleted:
            raise NotFoundError("todo not found")

        self.hub.broadcast_snapshot_sync()
        return {"deleted": True}

    def clear_completed_todos(self, payload: dict | None = None) -> dict:
        payload = payload or {}
        deleted = self.store.clear_completed(self._normalize_optional_list_id(payload))
        self.hub.broadcast_snapshot_sync()
        return {"deleted": deleted}

    def _normalize_create_title(self, payload: dict) -> str:
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ValidationError("title is required")
        return title[:120]

    def _normalize_list_title(self, payload: dict) -> str:
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ValidationError("list title is required")
        return title[:80]

    def _normalize_update_title(self, payload: dict) -> str | None:
        title = payload.get("title")
        if title is None:
            return None

        title = str(title).strip()
        if not title:
            raise ValidationError("title cannot be empty")
        return title[:120]

    def _normalize_completed(self, payload: dict) -> bool | None:
        completed = payload.get("completed")
        if completed is None:
            return None

        if not isinstance(completed, bool):
            raise ValidationError("completed must be a boolean")
        return completed

    def _normalize_list_id(self, payload: dict) -> str:
        list_id = payload.get("listId")
        if not isinstance(list_id, str) or not list_id.strip():
            return self.store.get_default_list_id()

        resolved = self.store.get_list(list_id.strip())
        if resolved is None:
            raise ValidationError("list not found")
        return resolved["id"]

    def _normalize_optional_list_id(self, payload: dict) -> str | None:
        list_id = payload.get("listId")
        if list_id is None:
            return None
        if not isinstance(list_id, str) or not list_id.strip():
            raise ValidationError("listId must be a non-empty string")

        resolved = self.store.get_list(list_id.strip())
        if resolved is None:
            raise ValidationError("list not found")
        return resolved["id"]

    def _normalize_optional_id(self, payload: dict) -> str | None:
        item_id = payload.get("id")
        if item_id is None:
            return None
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValidationError("id must be a non-empty string")
        return item_id.strip()
