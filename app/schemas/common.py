"""Schemas comuns: paginação e envelope de lista."""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
