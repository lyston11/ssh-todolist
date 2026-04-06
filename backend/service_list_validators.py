from dataclasses import dataclass

from backend.service_validation_common import LIST_TITLE_LIMIT, ValidationContext


@dataclass(frozen=True)
class CreateListPayload:
    title: str
    item_id: str | None


@dataclass(frozen=True)
class UpdateListPayload:
    title: str


@dataclass(frozen=True)
class CreateListPayloadValidator:
    context: ValidationContext

    def validate(self, payload: dict) -> CreateListPayload:
        return CreateListPayload(
            title=self.context.require_trimmed_text(
                payload,
                "title",
                "list title is required",
                max_length=LIST_TITLE_LIMIT,
            ),
            item_id=self.context.normalize_optional_id(payload),
        )


@dataclass(frozen=True)
class UpdateListPayloadValidator:
    context: ValidationContext

    def validate(self, payload: dict) -> UpdateListPayload:
        return UpdateListPayload(
            title=self.context.require_trimmed_text(
                payload,
                "title",
                "list title is required",
                max_length=LIST_TITLE_LIMIT,
            )
        )
