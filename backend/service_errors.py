from http import HTTPStatus


class TodoServiceError(Exception):
    status_code = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(TodoServiceError):
    status_code = HTTPStatus.BAD_REQUEST


class NotFoundError(TodoServiceError):
    status_code = HTTPStatus.NOT_FOUND
