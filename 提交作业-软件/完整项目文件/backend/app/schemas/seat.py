from pydantic import BaseModel, Field

from app.models.enums import SeatStatus
from app.schemas.common import ORMModel
from app.schemas.reservation import ReservationRead


class SeatCreate(BaseModel):
    room_id: int
    area_id: int | None = None
    seat_no: str = Field(min_length=1, max_length=20)
    seat_type: str = "普通"
    has_power: bool = False
    near_window: bool = False


class SeatStatusUpdate(BaseModel):
    status: SeatStatus
    reason: str | None = Field(default=None, max_length=255)


class SeatRead(ORMModel):
    id: int
    room_id: int
    area_id: int | None = None
    seat_no: str
    seat_type: str
    has_power: bool
    near_window: bool
    status: str


class SeatOccupancyRead(BaseModel):
    """资源状态与「该时段占用」两个维度分别返回（FR-003 / FR-031）。"""

    seat: SeatRead
    occupied: bool
    reservation: ReservationRead | None = None


class SeatStatusBatchUpdate(BaseModel):
    seat_ids: list[int] = Field(min_length=1)
    status: SeatStatus
    reason: str = Field(min_length=1, max_length=255)


class SeatStatusBatchResult(BaseModel):
    updated: list[SeatRead]
    conflicts: list[ReservationRead] = Field(default_factory=list)
