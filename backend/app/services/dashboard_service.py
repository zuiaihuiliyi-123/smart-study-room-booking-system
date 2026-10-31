from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import false, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import AccountStatus, ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.room import Room
from app.models.seat import Seat
from app.models.user import User
from app.models.violation import ViolationRecord
from app.schemas.dashboard import ChartItem, SeatUsageSlotRow, StatOverview, TrendPoint
from app.utils import time_utils

#: 图 1 的时段桶（左闭右开，与原型 UC-14 的 08-10 / 10-12 … 对齐）
SLOT_BUCKETS: list[tuple[str, int, int]] = [
    ("08:00-10:00", 8 * 60, 10 * 60),
    ("10:00-12:00", 10 * 60, 12 * 60),
    ("12:00-14:00", 12 * 60, 14 * 60),
    ("14:00-16:00", 14 * 60, 16 * 60),
    ("16:00-18:00", 16 * 60, 18 * 60),
    ("18:00-20:00", 18 * 60, 20 * 60),
    ("20:00-22:00", 20 * 60, 22 * 60),
]

#: 占用座位时段的预约状态：已取消 / 已违约不占用（AGENTS §4「有效预约」）
OCCUPIED_STATUSES = (
    ReservationStatus.PENDING.value,
    ReservationStatus.IN_USE.value,
    ReservationStatus.COMPLETED.value,
)

MAX_TREND_DAYS = 31


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _scoped_seat_ids(db: Session, room_id: int | None) -> set[int] | None:
    """room_id 缺省返回 None（全部自习室）；否则返回该房间的座位 id 集合。"""
    if room_id is None:
        return None
    return set(db.scalars(select(Seat.id).where(Seat.room_id == room_id)).all())


def get_overview(db: Session, room_id: int | None = None) -> StatOverview:
    """M6 / FR-052：座位总数、使用中、今日预约、今日违约、受限账户数。"""
    now = time_utils.now()
    today = now.date()
    seat_ids = _scoped_seat_ids(db, room_id)

    seat_stmt = select(func.count()).select_from(Seat).where(
        Seat.status == SeatStatus.AVAILABLE.value
    )
    if room_id is not None:
        seat_stmt = seat_stmt.where(Seat.room_id == room_id)
    seat_total = db.scalar(seat_stmt) or 0

    reservation_conditions = []
    if seat_ids is not None:
        reservation_conditions.append(Reservation.seat_id.in_(seat_ids))

    in_use_count = 0
    in_use_rows = db.scalars(
        select(Reservation).where(
            Reservation.status == ReservationStatus.IN_USE.value,
            Reservation.reserve_date == today,
            *reservation_conditions,
        )
    )
    current_minutes = _minutes(now.time())
    for row in in_use_rows:
        if _minutes(row.start_time) <= current_minutes < _minutes(row.end_time):
            in_use_count += 1

    today_start = datetime.combine(today, datetime.min.time())
    today_end = today_start + timedelta(days=1)

    today_reservations = (
        db.scalar(
            select(func.count())
            .select_from(Reservation)
            .where(
                Reservation.created_at >= today_start,
                Reservation.created_at < today_end,
                Reservation.status != ReservationStatus.CANCELLED.value,
                *reservation_conditions,
            )
        )
        or 0
    )

    violation_conditions = [
        ViolationRecord.created_at >= today_start,
        ViolationRecord.created_at < today_end,
    ]
    if seat_ids is not None:
        violation_conditions.append(
            ViolationRecord.reservation_id.in_(
                select(Reservation.id).where(Reservation.seat_id.in_(seat_ids))
            )
        )
    today_violations = (
        db.scalar(
            select(func.count())
            .select_from(ViolationRecord)
            .where(*violation_conditions)
        )
        or 0
    )

    # ⑤ 账户不归属自习室：按自习室筛选时仍保持全局口径
    restricted_accounts = (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.account_status == AccountStatus.RESTRICTED.value)
        )
        or 0
    )

    return StatOverview(
        seat_total=seat_total,
        in_use=in_use_count,
        today_reservations=today_reservations,
        today_violations=today_violations,
        restricted_accounts=restricted_accounts,
    )


def get_seat_usage(
    db: Session,
    start_date: date,
    end_date: date,
    room_id: int | None = None,
) -> list[ChartItem]:
    """M6 / FR-050：统计周期内各座位的已使用时段数（柱状图）。"""
    slots: dict[int, int] = {}
    stmt = select(Reservation).where(
        Reservation.status == ReservationStatus.COMPLETED.value,
        Reservation.reserve_date >= start_date,
        Reservation.reserve_date <= end_date,
    )
    if room_id is not None:
        stmt = stmt.where(
            Reservation.seat_id.in_(select(Seat.id).where(Seat.room_id == room_id))
        )
    for record in db.scalars(stmt):
        count = (
            _minutes(record.end_time) - _minutes(record.start_time)
        ) // settings.reservation_granularity_minutes
        if count > 0:
            slots[record.seat_id] = slots.get(record.seat_id, 0) + count

    seat_stmt = select(Seat)
    if room_id is not None:
        seat_stmt = seat_stmt.where(Seat.room_id == room_id)
    items = [
        ChartItem(name=seat.seat_no, value=slots.get(seat.id, 0))
        for seat in db.scalars(seat_stmt)
    ]
    items.sort(key=lambda item: (-item.value, item.name))
    return items


def get_seat_usage_by_slot(
    db: Session,
    start_date: date,
    end_date: date,
    room_id: int | None = None,
) -> list[SeatUsageSlotRow]:
    """图 1：各自习室各时段座位占用率。"""
    days = (end_date - start_date).days + 1
    if days <= 0:
        return []

    room_stmt = select(Room)
    if room_id is not None:
        room_stmt = room_stmt.where(Room.id == room_id)
    rooms = list(db.scalars(room_stmt.order_by(Room.id)).all())
    rows: list[SeatUsageSlotRow] = []

    for room in rooms:
        seats = list(db.scalars(select(Seat).where(Seat.room_id == room.id)).all())
        seat_ids = {seat.id for seat in seats}
        records = list(
            db.scalars(
                select(Reservation).where(
                    Reservation.seat_id.in_(seat_ids) if seat_ids else false(),
                    Reservation.status.in_(OCCUPIED_STATUSES),
                    Reservation.reserve_date >= start_date,
                    Reservation.reserve_date <= end_date,
                )
            ).all()
        ) if seat_ids else []

        for label, bucket_start, bucket_end in SLOT_BUCKETS:
            occupied = 0
            for record in records:
                record_start = _minutes(record.start_time)
                record_end = _minutes(record.end_time)
                overlap = min(record_end, bucket_end) - max(record_start, bucket_start)
                if overlap > 0:
                    occupied += overlap // settings.reservation_granularity_minutes
            capacity = len(seats) * ((bucket_end - bucket_start) // 30) * days
            rate = round(occupied / capacity, 4) if capacity > 0 else 0.0
            rows.append(
                SeatUsageSlotRow(
                    room_id=room.id,
                    room_name=room.name,
                    slot=label,
                    occupied=occupied,
                    capacity=capacity,
                    rate=rate,
                )
            )
    return rows


def get_trend(
    db: Session,
    start_date: date,
    end_date: date,
    room_id: int | None = None,
) -> list[TrendPoint]:
    """M6 / FR-051：按日统计有效预约数与违约数（折线图）。"""
    total_days = (end_date - start_date).days
    if total_days < 0 or total_days > MAX_TREND_DAYS:
        return []

    reservation_stmt = select(Reservation).where(
        Reservation.created_at >= datetime.combine(start_date, datetime.min.time()),
        Reservation.created_at < datetime.combine(
            end_date + timedelta(days=1), datetime.min.time()
        ),
    )
    if room_id is not None:
        reservation_stmt = reservation_stmt.where(
            Reservation.seat_id.in_(select(Seat.id).where(Seat.room_id == room_id))
        )
    reservations = list(db.scalars(reservation_stmt).all())

    violation_stmt = select(ViolationRecord).where(
        ViolationRecord.created_at
        >= datetime.combine(start_date, datetime.min.time()),
        ViolationRecord.created_at
        < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
    )
    if room_id is not None:
        violation_stmt = violation_stmt.where(
            ViolationRecord.reservation_id.in_(
                select(Reservation.id).where(
                    Reservation.seat_id.in_(
                        select(Seat.id).where(Seat.room_id == room_id)
                    )
                )
            )
        )
    violations = list(db.scalars(violation_stmt).all())

    points: list[TrendPoint] = []
    for offset in range(total_days + 1):
        day = start_date + timedelta(days=offset)
        points.append(
            TrendPoint(
                date=day,
                reservations=sum(
                    1
                    for item in reservations
                    if item.created_at.date() == day
                    and item.status != ReservationStatus.CANCELLED.value
                ),
                violations=sum(
                    1 for item in violations if item.created_at.date() == day
                ),
            )
        )
    return points
