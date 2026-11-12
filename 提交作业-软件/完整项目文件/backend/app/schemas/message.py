from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class MessageRead(ORMModel):
    id: int
    type: str
    title: str
    content: str
    related_type: str | None = None
    related_id: int | None = None
    is_read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    count: int
