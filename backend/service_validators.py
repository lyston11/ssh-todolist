from dataclasses import dataclass, field

from backend.service_list_validators import (
    CreateListPayload,
    CreateListPayloadValidator,
    UpdateListPayload,
    UpdateListPayloadValidator,
)
from backend.service_todo_validators import (
    ClearCompletedPayload,
    ClearCompletedPayloadValidator,
    CreateTodoPayload,
    CreateTodoPayloadValidator,
    UpdateTodoPayload,
    UpdateTodoPayloadValidator,
)
from backend.service_validation_common import (
    LIST_TITLE_LIMIT,
    TAG_LIMIT,
    TODO_TITLE_LIMIT,
    ValidationContext,
)
from backend.store import TodoStore


@dataclass(frozen=True)
class ServiceValidators:
    create_list: CreateListPayloadValidator
    update_list: UpdateListPayloadValidator
    create_todo: CreateTodoPayloadValidator
    update_todo: UpdateTodoPayloadValidator
    clear_completed: ClearCompletedPayloadValidator

    @classmethod
    def from_store(cls, store: TodoStore) -> "ServiceValidators":
        context = ValidationContext(store)
        return cls(
            create_list=CreateListPayloadValidator(context),
            update_list=UpdateListPayloadValidator(context),
            create_todo=CreateTodoPayloadValidator(context),
            update_todo=UpdateTodoPayloadValidator(context),
            clear_completed=ClearCompletedPayloadValidator(context),
        )


@dataclass
class TodoPayloadValidator:
    store: TodoStore
    validators: ServiceValidators = field(init=False)

    def __post_init__(self) -> None:
        self.validators = ServiceValidators.from_store(self.store)

    def validate_create_list(self, payload: dict) -> CreateListPayload:
        return self.validators.create_list.validate(payload)

    def validate_update_list(self, payload: dict) -> UpdateListPayload:
        return self.validators.update_list.validate(payload)

    def validate_create_todo(self, payload: dict) -> CreateTodoPayload:
        return self.validators.create_todo.validate(payload)

    def validate_update_todo(self, payload: dict) -> UpdateTodoPayload:
        return self.validators.update_todo.validate(payload)

    def validate_clear_completed(self, payload: dict | None) -> ClearCompletedPayload:
        return self.validators.clear_completed.validate(payload)
