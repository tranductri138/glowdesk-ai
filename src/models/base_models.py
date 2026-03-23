from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base model with camelCase alias for JSON serialization."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class BaseResponse(CamelModel, Generic[T]):
    success: bool
    data: T | None = None
    meta: dict[str, Any] | None = None


class ErrorDetail(CamelModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(CamelModel):
    success: bool = False
    error: ErrorDetail
