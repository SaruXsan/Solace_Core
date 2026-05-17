from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class MessageResponse(BaseModel):
    success: bool = True
    message: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
