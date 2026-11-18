"""Domain errors mapped to the consistent API error format."""

from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class BudgetExceededError(AppError):
    status_code = 503
    code = "budget_exceeded"


class StructuredOutputError(AppError):
    status_code = 502
    code = "structured_output_error"


class UploadError(AppError):
    status_code = 400
    code = "invalid_upload"
