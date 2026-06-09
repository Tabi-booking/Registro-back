from __future__ import annotations

from fastapi import HTTPException, status


class TabiException(Exception):
    """Base exception for Tabi application."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(TabiException):
    def __init__(self, resource: str = "Resource", resource_id: str | int | None = None):
        msg = f"{resource} not found"
        if resource_id is not None:
            msg = f"{resource} with id '{resource_id}' not found"
        super().__init__(msg, "NOT_FOUND", 404)


class ConflictError(TabiException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, "CONFLICT", 409)


class UnauthorizedError(TabiException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ForbiddenError(TabiException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "FORBIDDEN", 403)


class ValidationError(TabiException):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, "VALIDATION_ERROR", 422)


class BadRequestError(TabiException):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, "BAD_REQUEST", 400)


class RateLimitError(TabiException):
    def __init__(self, message: str = "Too many requests"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", 429)


class StorageError(TabiException):
    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(message, "STORAGE_ERROR", 500)
