from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "OK"
    data: T | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: str = "INTERNAL_ERROR"


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "OK"
    data: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
