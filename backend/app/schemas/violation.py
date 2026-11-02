from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ManualViolationCreate(BaseModel):
    reservation_id: int
    reason: str = Field(min_length=1, max_length=255)


class ViolationRead(ORMModel):
    id: int
    user_id: int
    reservation_id: int
    type: str
    reason: str
    operator_id: int | None = None
    created_at: datetime
