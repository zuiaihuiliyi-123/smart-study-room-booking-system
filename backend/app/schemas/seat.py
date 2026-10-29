from pydantic import BaseModel, Field

from app.models.enums import SeatStatus
from app.schemas.common import ORMModel


class SeatCreate(BaseModel):
    room_id: int
    area_id: int | None = None
    seat_no: str = Field(min_length=1, max_length=20)
    seat_type: str = "普通"
    has_power: bool = False


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
    status: str
