from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.schemas.reservation import ReservationRead
from app.schemas.seat import SeatRead


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=100)
    open_time: str = Field(
        default="08:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    close_time: str = Field(
        default="22:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    capacity: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "RoomCreate":
        if self.open_time >= self.close_time:
            raise ValueError("开放时间必须早于关闭时间")
        return self


class RoomRead(ORMModel):
    id: int
    name: str
    location: str
    open_time: str
    close_time: str
    capacity: int
    enabled: bool


class AreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class AreaRead(ORMModel):
    id: int
    room_id: int
    name: str


class RoomUpdate(BaseModel):
    """管理员修改自习室属性；reason 为审计事由（NFR-009）。"""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    location: str | None = Field(default=None, min_length=1, max_length=100)
    open_time: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    close_time: str | None = Field(
        default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    capacity: int | None = Field(default=None, ge=0)
    enabled: bool | None = None
    reason: str | None = Field(default=None, max_length=255)


class ConflictPreview(BaseModel):
    """场地临时关闭 / 批量状态调整前的影响清单（BR-019 / BR-022）。"""

    seats: list[SeatRead]
    reservations: list[ReservationRead]


class RoomCloseRequest(BaseModel):
    """BR-022：先预览、二次确认后才执行关闭。"""

    start_at: datetime
    end_at: datetime
    area_id: int | None = None
    reason: str = Field(min_length=1, max_length=255)
    cancel_affected: bool = False
    expected_reservation_ids: list[int] = Field(default_factory=list)


class RoomCloseResult(BaseModel):
    closed_seats: int
    cancelled: int
    kept: int

