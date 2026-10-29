from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BlacklistCreate(BaseModel):
    user_id: int
    reason: str = Field(min_length=1, max_length=255)
    expire_at: datetime | None = None


class BlacklistRead(ORMModel):
    id: int
    user_id: int
    reason: str
    mode: str
    start_at: datetime
    expire_at: datetime | None = None
    released_at: datetime | None = None
    operator_id: int | None = None
