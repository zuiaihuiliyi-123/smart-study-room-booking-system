from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.seat import Seat
from app.models.user import User
from app.schemas.seat import SeatCreate, SeatRead, SeatStatusUpdate
from app.services import seat_service

router = APIRouter(tags=["M1 座位资源"])


@router.get(
    "/rooms/{room_id}/seats",
    response_model=list[SeatRead],
    summary="按自习室查询座位",
)
def list_seats(room_id: int, db: Session = Depends(get_db)) -> list[Seat]:
    return seat_service.list_seats(db, room_id)


@router.post(
    "/seats",
    response_model=SeatRead,
    status_code=status.HTTP_201_CREATED,
    summary="新增座位（管理员）",
)
def create_seat(
    payload: SeatCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Seat:
    return seat_service.create_seat(db, payload)


@router.patch(
    "/seats/{seat_id}/status",
    response_model=SeatRead,
    summary="调整座位资源状态（管理员）",
)
def update_seat_status(
    seat_id: int,
    payload: SeatStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Seat:
    return seat_service.update_seat_status(db, seat_id, payload, admin.id)
