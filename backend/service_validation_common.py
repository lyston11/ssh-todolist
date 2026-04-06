from dataclasses import dataclass

from backend.service_errors import ValidationError
from backend.store import TodoStore


TODO_TITLE_LIMIT = 120
LIST_TITLE_LIMIT = 80
TAG_LIMIT = 40


@dataclass(frozen=True)
class ValidationContext:
    store: TodoStore

    def require_trimmed_text(
        self,
        payload: dict,
        key: str,
        error_message: str,
        *,
        max_length: int,
    ) -> str:
        value = str(payload.get(key, "")).strip()
        if not value:
            raise ValidationError(error_message)
        return value[:max_length]

    def normalize_optional_title(self, payload: dict) -> str | None:
        if "title" not in payload:
            return None
        return self.require_trimmed_text(
            payload,
            "title",
            "title cannot be empty",
            max_length=TODO_TITLE_LIMIT,
        )

    def normalize_optional_id(self, payload: dict) -> str | None:
        item_id = payload.get("id")
        if item_id is None:
            return None
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValidationError("id must be a non-empty string")
        return item_id.strip()

    def normalize_optional_tag(self, payload: dict) -> str | None:
        tag = payload.get("tag")
        if tag is None:
            return None

        normalized_tag = str(tag).strip()
        if not normalized_tag:
            return ""
        return normalized_tag[:TAG_LIMIT]

    def normalize_completed(self, payload: dict) -> bool | None:
        completed = payload.get("completed")
        if completed is None:
            return None

        if not isinstance(completed, bool):
            raise ValidationError("completed must be a boolean")
        return completed

    def normalize_optional_due_at(self, payload: dict) -> tuple[int | None, bool]:
        if "dueAt" not in payload:
            return None, False

        due_at = payload.get("dueAt")
        if due_at is None:
            return None, True

        if isinstance(due_at, bool) or not isinstance(due_at, int):
            raise ValidationError("dueAt must be an integer timestamp or null")
        if due_at < 0:
            raise ValidationError("dueAt must be greater than or equal to 0")
        return due_at, True

    def resolve_required_list_id(self, payload: dict) -> str:
        list_id = payload.get("listId")
        if not isinstance(list_id, str) or not list_id.strip():
            return self.store.get_default_list_id()
        return self.resolve_existing_list_id(list_id.strip())

    def resolve_optional_list_id(self, payload: dict) -> str | None:
        list_id = payload.get("listId")
        if list_id is None:
            return None
        if not isinstance(list_id, str) or not list_id.strip():
            raise ValidationError("listId must be a non-empty string")
        return self.resolve_existing_list_id(list_id.strip())

    def resolve_existing_list_id(self, list_id: str) -> str:
        resolved = self.store.get_list(list_id)
        if resolved is None:
            raise ValidationError("list not found")
        return resolved["id"]
