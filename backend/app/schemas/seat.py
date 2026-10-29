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
    """调整座位资源状态（FR-004 / FR-016）。

    BR-019 本版口径：存在冲突的未来预约时**默认保留**（只提示、不自动取消）；
    仅当管理员显式 ``cancel_conflicts=True`` 且 ``confirm=True`` 时批量取消，
    不计违约、不补偿（BR-022 二次确认）。
    """

    status: SeatStatus
    reason: str | None = Field(default=None, max_length=255)
    cancel_conflicts: bool = False
    confirm: bool = False


class SeatRead(ORMModel):
    id: int
    room_id: int
    area_id: int | None = None
    seat_no: str
    seat_type: str
    has_power: bool
    status: str
