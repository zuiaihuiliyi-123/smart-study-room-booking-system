from datetime import date, datetime, time

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.user import User
from app.schemas.reservation import ReservationRead
from app.schemas.seat import (
    SeatCreate,
    SeatOccupancyRead,
    SeatRead,
    SeatStatusBatchResult,
    SeatStatusBatchUpdate,
    SeatStatusUpdate,
)
from app.services import seat_service

router = APIRouter(tags=["M1 座位资源"])


@router.get(
    "/rooms/{room_id}/seats",
    response_model=list[SeatRead],
    summary="按自习室查询座位",
)
def list_seats(room_id: int, db: Session = Depends(get_db)) -> list[Seat]:
    return seat_service.list_seats(db, room_id)


@router.get(
    "/seats/occupancy",
    response_model=list[SeatOccupancyRead],
    summary="座位资源状态与时段占用（管理员）",
)
def list_seat_occupancy(
    room_id: int,
    reserve_date: date,
    start_time: time,
    end_time: time,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict]:
    return seat_service.list_occupancy(
        db, room_id, reserve_date, start_time, end_time
    )


@router.get(
    "/seats/conflicts",
    response_model=list[ReservationRead],
    summary="座位调整冲突清单（管理员）",
)
def list_seat_conflicts(
    seat_ids: str,
    start_at: datetime,
    end_at: datetime,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[Reservation]:
    ids = []
    for item in seat_ids.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError:
            continue
    return seat_service.list_conflicts(db, ids, start_at, end_at)


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
    "/seats/status",
    response_model=SeatStatusBatchResult,
    summary="批量调整座位资源状态（管理员）",
)
def update_seat_status_batch(
    payload: SeatStatusBatchUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SeatStatusBatchResult:
    seats, conflicts = seat_service.update_status_batch(db, payload, admin.id)
    return SeatStatusBatchResult(updated=seats, conflicts=conflicts)


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
