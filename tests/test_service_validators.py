import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path

from backend.service_errors import NotFoundError, ValidationError
from backend.service_list_validators import CreateListPayloadValidator, UpdateListPayloadValidator
from backend.service_todo_validators import (
    ClearCompletedPayloadValidator,
    CreateTodoPayloadValidator,
    UpdateTodoPayloadValidator,
)
from backend.service_validation_common import ValidationContext
from backend.service_validators import ServiceValidators, TodoPayloadValidator
from backend.store import TodoStore


class ServiceValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.store = TodoStore(Path(self._tempdir.name) / "todos.db")
        self.context = ValidationContext(self.store)
        self.validator = TodoPayloadValidator(self.store)

    def tearDown(self) -> None:
        self._tempdir.cleanup()

    def test_service_validators_factory_builds_focused_validators(self) -> None:
        validators = ServiceValidators.from_store(self.store)

        self.assertIsInstance(validators.create_list, CreateListPayloadValidator)
        self.assertIsInstance(validators.update_list, UpdateListPayloadValidator)
        self.assertIsInstance(validators.create_todo, CreateTodoPayloadValidator)
        self.assertIsInstance(validators.update_todo, UpdateTodoPayloadValidator)
        self.assertIsInstance(validators.clear_completed, ClearCompletedPayloadValidator)

    def test_create_list_validator_trims_title_and_optional_id(self) -> None:
        payload = CreateListPayloadValidator(self.context).validate(
            {"title": "  工作区  ", "id": "  work-list  "}
        )

        self.assertEqual(payload.title, "工作区")
        self.assertEqual(payload.item_id, "work-list")

    def test_create_todo_validator_uses_default_list_and_trims_fields(self) -> None:
        payload = CreateTodoPayloadValidator(self.context).validate(
            {
                "title": "  整理同步日志  ",
                "tag": "  运维  ",
                "dueAt": 1760000000000,
            }
        )

        self.assertEqual(payload.title, "整理同步日志")
        self.assertEqual(payload.list_id, "default-list")
        self.assertEqual(payload.tag, "运维")
        self.assertEqual(payload.due_at, 1760000000000)
        self.assertTrue(payload.due_at_provided)

    def test_update_list_validator_rejects_blank_title(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            UpdateListPayloadValidator(self.context).validate({"title": "   "})

        self.assertEqual(ctx.exception.message, "list title is required")

    def test_update_todo_validator_rejects_invalid_list_id(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            UpdateTodoPayloadValidator(self.context).validate({"listId": "missing-list"})

        self.assertEqual(ctx.exception.message, "list not found")
        self.assertEqual(ctx.exception.status_code, HTTPStatus.BAD_REQUEST)

    def test_update_todo_validator_rejects_invalid_completed_and_due_at(self) -> None:
        with self.assertRaises(ValidationError) as completed_ctx:
            UpdateTodoPayloadValidator(self.context).validate({"completed": "yes"})
        self.assertEqual(completed_ctx.exception.message, "completed must be a boolean")

        with self.assertRaises(ValidationError) as due_at_ctx:
            UpdateTodoPayloadValidator(self.context).validate({"dueAt": -1})
        self.assertEqual(due_at_ctx.exception.message, "dueAt must be greater than or equal to 0")

    def test_clear_completed_validator_accepts_existing_list_and_rejects_blank_id(self) -> None:
        self.store.create_list("工作", list_id="work-list")

        payload = ClearCompletedPayloadValidator(self.context).validate({"listId": "work-list"})
        self.assertEqual(payload.list_id, "work-list")

        with self.assertRaises(ValidationError) as ctx:
            ClearCompletedPayloadValidator(self.context).validate({"listId": "   "})
        self.assertEqual(ctx.exception.message, "listId must be a non-empty string")

    def test_legacy_validator_facade_keeps_old_entrypoints(self) -> None:
        payload = self.validator.validate_create_list({"title": "  默认清单  "})

        self.assertEqual(payload.title, "默认清单")
        self.assertIsNone(payload.item_id)

    def test_service_error_status_codes_use_http_status(self) -> None:
        self.assertEqual(ValidationError("bad payload").status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(NotFoundError("missing").status_code, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
