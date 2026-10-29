from sqlalchemy.orm import Session

from app.models.seat import Seat
from app.schemas.seat import SeatCreate, SeatStatusUpdate


def list_seats(db: Session, room_id: int) -> list[Seat]:
    """M1 / FR-003：按自习室查询座位（含资源状态）。"""
    raise NotImplementedError("座位列表查询待实现")


def create_seat(db: Session, payload: SeatCreate) -> Seat:
    """M1 / FR-002：新增座位，默认资源状态“可用”。"""
    raise NotImplementedError("座位创建待实现")


def update_seat_status(
    db: Session,
    seat_id: int,
    payload: SeatStatusUpdate,
    operator_id: int,
) -> Seat:
    """M1 / FR-004：调整座位资源状态。

    需同步识别冲突的未来预约（BR-019），并写审计日志。
    """
    raise NotImplementedError("座位资源状态调整待实现")
