from typing import Generic, TypeVar
from pydantic import BaseModel

DataT = TypeVar("DataT")


class Response(BaseModel, Generic[DataT]):
    """Standard envelope for all API responses."""
    success: bool = True
    message: str = "OK"
    data: DataT | None = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "OK"
    data: list[DataT]
    total: int
    page: int
    page_size: int
    has_next: bool
