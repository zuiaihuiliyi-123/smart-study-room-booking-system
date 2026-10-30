from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ReservationCreate(BaseModel):
    seat_id: int
    reserve_date: date
    start_time: time
    end_time: time
    idempotency_key: str = Field(min_length=8, max_length=64)


class ReservationRead(ORMModel):
    id: int
    user_id: int
    seat_id: int
    reserve_date: date
    start_time: time
    end_time: time
    status: str
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    cancel_time: datetime | None = None
    cancel_reason: str | None = None
    cancelled_by_id: int | None = None
    auto_completed: bool = False
    created_at: datetime


class CancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class ForceCancelRequest(BaseModel):
    """管理员强制取消必须填写原因（BR-011）。"""

    reason: str = Field(min_length=1, max_length=255)
