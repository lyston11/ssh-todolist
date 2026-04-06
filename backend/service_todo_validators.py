from dataclasses import dataclass

from backend.service_validation_common import TODO_TITLE_LIMIT, ValidationContext


@dataclass(frozen=True)
class CreateTodoPayload:
    title: str
    list_id: str
    item_id: str | None
    tag: str | None
    due_at: int | None
    due_at_provided: bool


@dataclass(frozen=True)
class UpdateTodoPayload:
    title: str | None
    completed: bool | None
    list_id: str | None
    tag: str | None
    due_at: int | None
    due_at_provided: bool


@dataclass(frozen=True)
class ClearCompletedPayload:
    list_id: str | None


@dataclass(frozen=True)
class CreateTodoPayloadValidator:
    context: ValidationContext

    def validate(self, payload: dict) -> CreateTodoPayload:
        due_at, due_at_provided = self.context.normalize_optional_due_at(payload)
        return CreateTodoPayload(
            title=self.context.require_trimmed_text(
                payload,
                "title",
                "title is required",
                max_length=TODO_TITLE_LIMIT,
            ),
            list_id=self.context.resolve_required_list_id(payload),
            item_id=self.context.normalize_optional_id(payload),
            tag=self.context.normalize_optional_tag(payload),
            due_at=due_at,
            due_at_provided=due_at_provided,
        )


@dataclass(frozen=True)
class UpdateTodoPayloadValidator:
    context: ValidationContext

    def validate(self, payload: dict) -> UpdateTodoPayload:
        due_at, due_at_provided = self.context.normalize_optional_due_at(payload)
        return UpdateTodoPayload(
            title=self.context.normalize_optional_title(payload),
            completed=self.context.normalize_completed(payload),
            list_id=self.context.resolve_optional_list_id(payload),
            tag=self.context.normalize_optional_tag(payload),
            due_at=due_at,
            due_at_provided=due_at_provided,
        )


@dataclass(frozen=True)
class ClearCompletedPayloadValidator:
    context: ValidationContext

    def validate(self, payload: dict | None) -> ClearCompletedPayload:
        return ClearCompletedPayload(
            list_id=self.context.resolve_optional_list_id(payload or {})
        )
