from datetime import date, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.user import User
from app.schemas.common import MessageResponse, PageResult
from app.schemas.reservation import (
    CancelRequest,
    ForceCancelRequest,
    ReservationCreate,
    ReservationRead,
)
from app.schemas.seat import SeatRead
from app.services import availability_service, reservation_service

router = APIRouter(prefix="/reservations", tags=["M2 预约管理"])


@router.post(
    "",
    response_model=ReservationRead,
    summary="创建预约",
)
def create_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reservation:
    return reservation_service.create_reservation(db, current_user, payload)


@router.get("/me", response_model=PageResult[ReservationRead], summary="本人预约记录")
def list_my_reservations(
    status: str | None = None,
    reserve_date_from: date | None = None,
    reserve_date_to: date | None = None,
    room_id: int | None = None,
    seat_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResult[ReservationRead]:
    return reservation_service.list_my_reservations(
        db,
        current_user.id,
        status=status,
        page=page,
        page_size=page_size,
        reserve_date_from=reserve_date_from,
        reserve_date_to=reserve_date_to,
        room_id=room_id,
        seat_id=seat_id,
    )


@router.get(
    "/available-seats",
    response_model=list[SeatRead],
    summary="查询时段内可预约座位",
)
def list_available_seats(
    room_id: int,
    reserve_date: date,
    start_time: time,
    end_time: time,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Seat]:
    return availability_service.list_available_seats(
        db,
        room_id,
        reserve_date,
        start_time,
        end_time,
        user_id=current_user.id,
    )


@router.get(
    "",
    response_model=PageResult[ReservationRead],
    summary="全部预约（管理员）",
)
def list_all_reservations(
    status: str | None = None,
    reserve_date_from: date | None = None,
    reserve_date_to: date | None = None,
    room_id: int | None = None,
    seat_id: int | None = None,
    student_no: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[ReservationRead]:
    return reservation_service.list_all_reservations(
        db,
        status=status,
        page=page,
        page_size=page_size,
        reserve_date_from=reserve_date_from,
        reserve_date_to=reserve_date_to,
        room_id=room_id,
        seat_id=seat_id,
        student_no=student_no,
    )


@router.get(
    "/{reservation_id}",
    response_model=ReservationRead,
    summary="预约单详情（管理员）",
)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Reservation:
    return reservation_service.get_reservation(db, reservation_id)


@router.post(
    "/{reservation_id}/cancel",
    response_model=MessageResponse,
    summary="取消本人预约",
)
def cancel_my_reservation(
    reservation_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    reservation_service.cancel_my_reservation(
        db, current_user.id, reservation_id, payload
    )
    return MessageResponse(message="预约已取消")


@router.post(
    "/{reservation_id}/force-cancel",
    response_model=MessageResponse,
    summary="强制取消预约（管理员）",
)
def force_cancel_reservation(
    reservation_id: int,
    payload: ForceCancelRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> MessageResponse:
    reservation_service.force_cancel(db, admin.id, reservation_id, payload)
    return MessageResponse(message="预约已强制取消")
