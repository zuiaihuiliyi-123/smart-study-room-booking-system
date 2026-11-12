"""预约查询服务（只读）。

事务边界约定：本模块所有函数只读，不 commit / rollback。
命令写入见 ``reservation_command_service``。
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.reservation import ReservationRead, ReservationStatusCounts

#: 有效预约状态（TM-18）
ACTIVE_STATUSES = (
    ReservationStatus.PENDING.value,
    ReservationStatus.IN_USE.value,
)

VALID_STATUSES = {item.value for item in ReservationStatus}


def get_reservation(db: Session, reservation_id: int) -> Reservation:
    """查询预约单详情（管理员）；不存在时抛 404。"""
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise BusinessError(
            "预约单不存在", code="RESERVATION_NOT_FOUND", status_code=404
        )
    return reservation


def _validate_status_filter(status: str | None) -> None:
    if status is not None and status not in VALID_STATUSES:
        raise BusinessError(
            f"未知的预约状态：{status}",
            code="INVALID_STATUS",
            status_code=422,
        )


def _list_conditions(
    *,
    status: str | None,
    reserve_date_from: date | None,
    reserve_date_to: date | None,
    room_id: int | None,
    seat_id: int | None,
    student_no: str | None,
) -> list:
    _validate_status_filter(status)
    conditions: list = []
    if status:
        conditions.append(Reservation.status == status)
    if reserve_date_from is not None:
        conditions.append(Reservation.reserve_date >= reserve_date_from)
    if reserve_date_to is not None:
        conditions.append(Reservation.reserve_date <= reserve_date_to)
    if room_id is not None:
        conditions.append(
            Reservation.seat_id.in_(
                select(Seat.id).where(Seat.room_id == room_id)
            )
        )
    if seat_id is not None:
        conditions.append(Reservation.seat_id == seat_id)
    if student_no:
        conditions.append(
            Reservation.user_id.in_(
                select(User.id).where(User.student_no == student_no)
            )
        )
    return conditions


def _page(
    db: Session, conditions: list, page: int, page_size: int
) -> PageResult[ReservationRead]:
    total = (
        db.scalar(
            select(func.count()).select_from(Reservation).where(*conditions)
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(Reservation)
            .where(*conditions)
            .order_by(
                Reservation.reserve_date.desc(),
                Reservation.start_time.desc(),
                Reservation.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PageResult[ReservationRead](
        items=[ReservationRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_my_reservations(
    db: Session,
    user_id: int,
    *,
    status: str | None,
    page: int,
    page_size: int,
    reserve_date_from: date | None = None,
    reserve_date_to: date | None = None,
    room_id: int | None = None,
    seat_id: int | None = None,
) -> PageResult[ReservationRead]:
    """M4 / FR-030：查询本人预约记录。"""
    conditions = [
        Reservation.user_id == user_id,
        *_list_conditions(
            status=status,
            reserve_date_from=reserve_date_from,
            reserve_date_to=reserve_date_to,
            room_id=room_id,
            seat_id=seat_id,
            student_no=None,
        ),
    ]
    return _page(db, conditions, page, page_size)


def count_my_reservations(
    db: Session,
    user_id: int,
    *,
    reserve_date_from: date | None = None,
    reserve_date_to: date | None = None,
    room_id: int | None = None,
    seat_id: int | None = None,
) -> ReservationStatusCounts:
    """M4 / FR-030：本人预约按状态分组计数。"""
    conditions = [
        Reservation.user_id == user_id,
        *_list_conditions(
            status=None,
            reserve_date_from=reserve_date_from,
            reserve_date_to=reserve_date_to,
            room_id=room_id,
            seat_id=seat_id,
            student_no=None,
        ),
    ]
    rows = db.execute(
        select(Reservation.status, func.count())
        .where(*conditions)
        .group_by(Reservation.status)
    ).all()

    counts = {item.value: 0 for item in ReservationStatus}
    for status_value, total in rows:
        counts[status_value] = int(total)
    return ReservationStatusCounts(counts=counts, total=sum(counts.values()))


def list_all_reservations(
    db: Session,
    *,
    status: str | None,
    page: int,
    page_size: int,
    reserve_date_from: date | None = None,
    reserve_date_to: date | None = None,
    room_id: int | None = None,
    seat_id: int | None = None,
    student_no: str | None = None,
) -> PageResult[ReservationRead]:
    """M4 / FR-031：管理员查询全部预约。"""
    conditions = _list_conditions(
        status=status,
        reserve_date_from=reserve_date_from,
        reserve_date_to=reserve_date_to,
        room_id=room_id,
        seat_id=seat_id,
        student_no=student_no,
    )
    return _page(db, conditions, page, page_size)
