from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ReviewCreate(BaseModel):
    reservation_id: int
    score: int = Field(ge=1, le=5)
    content: str | None = Field(default=None, max_length=500)


class ReviewRead(ORMModel):
    id: int
    user_id: int
    reservation_id: int
    score: int
    content: str | None = None
    created_at: datetime
