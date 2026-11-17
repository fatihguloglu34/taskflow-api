from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Sayfalanmış liste cevabı."""

    items: List[T]
    total: int
    limit: int
    offset: int
