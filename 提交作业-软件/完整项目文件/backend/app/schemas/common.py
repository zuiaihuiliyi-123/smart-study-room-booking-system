from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """可从 SQLAlchemy 对象直接构造的响应模型。"""

    model_config = ConfigDict(from_attributes=True)


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20


class MessageResponse(BaseModel):
    message: str = "ok"
