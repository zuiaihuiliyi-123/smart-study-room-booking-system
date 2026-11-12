from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ComplaintStatus, ComplaintTargetType
from app.schemas.common import ORMModel


class ComplaintCreate(BaseModel):
    target_type: ComplaintTargetType
    target_id: int
    content: str = Field(min_length=1, max_length=1000)


class ComplaintHandle(BaseModel):
    status: ComplaintStatus
    handle_note: str = Field(min_length=1, max_length=500)


class ComplaintRead(ORMModel):
    id: int
    user_id: int
    target_type: str
    target_id: int
    content: str
    status: str
    handler_id: int | None = None
    handle_note: str | None = None
    handled_at: datetime | None = None
    created_at: datetime
