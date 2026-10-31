"""M1 座位资源：座位查询、新增与资源状态调整（FR-002/FR-003/FR-004）。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.room import Area, Room
from app.models.seat import Seat
from app.schemas.seat import SeatCreate, SeatStatusBatchUpdate, SeatStatusUpdate
from app.services import audit_service

# 座位资源状态只含“可用/维修中/停用”，不含“已预约/使用中”（§10.0 MD-01）
_UNAVAILABLE_STATUSES = {SeatStatus.MAINTENANCE.value, SeatStatus.DISABLED.value}


def list_seats(db: Session, room_id: int) -> list[Seat]:
    """M1 / FR-003：按自习室查询座位（含资源状态，按座位编号排序）。

    可预约与否不在本接口判定，由 availability 服务按 C1～C6 实时计算（§10.4.2）。
    """
    stmt = select(Seat).where(Seat.room_id == room_id).order_by(Seat.seat_no)
    return list(db.scalars(stmt))


def create_seat(db: Session, payload: SeatCreate) -> Seat:
    """M1 / FR-002：新增座位，默认资源状态“可用”。

    - 自习室须存在；若指定区域，区域须属于该自习室；
    - 座位编号在自习室内唯一（DR-003）。
    """
    if db.get(Room, payload.room_id) is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)

    if payload.area_id is not None:
        area = db.get(Area, payload.area_id)
        if area is None or area.room_id != payload.room_id:
            raise BusinessError(
                "区域不存在或不属于该自习室",
                code="AREA_NOT_IN_ROOM",
                status_code=404,
            )

    duplicated = db.scalar(
        select(Seat).where(
            Seat.room_id == payload.room_id, Seat.seat_no == payload.seat_no
        )
    )
    if duplicated is not None:
        raise BusinessError(
            "该自习室内座位编号已存在", code="SEAT_NO_DUPLICATED", status_code=409
        )

    seat = Seat(
        room_id=payload.room_id,
        area_id=payload.area_id,
        seat_no=payload.seat_no,
        seat_type=payload.seat_type,
        has_power=payload.has_power,
        near_window=payload.near_window,
        status=SeatStatus.AVAILABLE.value,
    )
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return seat


def _conflicting_future_reservations(db: Session, seat_id: int) -> list[Reservation]:
    """检索该座位“尚未结束”的有效预约（待使用）。

    有效预约 = 待使用 / 使用中（TM-18）；此处按 ST-006/ST-033 关注待使用。
    “尚未结束”= 预约日期在今天之后，或就在今天但结束时间晚于当前时刻。
    """
    now = datetime.now()
    stmt = (
        select(Reservation)
        .where(
            Reservation.seat_id == seat_id,
            Reservation.status == ReservationStatus.PENDING.value,
        )
        .where(
            (Reservation.reserve_date > now.date())
            | (
                (Reservation.reserve_date == now.date())
                & (Reservation.end_time > now.time())
            )
        )
        .order_by(Reservation.reserve_date, Reservation.start_time)
    )
    return list(db.scalars(stmt))


def update_seat_status(
    db: Session,
    seat_id: int,
    payload: SeatStatusUpdate,
    operator_id: int,
) -> Seat:
    """M1 / FR-004：调整座位资源状态。

    BR-019 口径：转为“维修中/停用”时若存在冲突的未来有效预约，
    **只识别并列出、不自动取消**，由管理员先处理预约后再操作；
    每次变更写入审计日志（NFR-009，含变更前后值）。
    """
    seat = db.get(Seat, seat_id)
    if seat is None:
        raise BusinessError("座位不存在", code="SEAT_NOT_FOUND", status_code=404)

    new_status = (
        payload.status.value if isinstance(payload.status, SeatStatus) else payload.status
    )
    old_status = seat.status
    if new_status == old_status:
        return seat

    if new_status in _UNAVAILABLE_STATUSES:
        conflicts = _conflicting_future_reservations(db, seat_id)
        if conflicts:
            preview = "、".join(str(item.id) for item in conflicts[:10])
            more = "" if len(conflicts) <= 10 else " 等"
            raise BusinessError(
                f"该座位存在 {len(conflicts)} 条尚未结束的有效预约（{preview}{more}），"
                "请先处理冲突预约；系统不会自动取消（BR-019）",
                code="SEAT_STATUS_CONFLICT",
                status_code=409,
            )

    seat.status = new_status
    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="SEAT_STATUS_UPDATE",
        target_type="SEAT",
        target_id=seat_id,
        reason=payload.reason,
        before_value=old_status,
        after_value=new_status,
    )
    db.commit()
    db.refresh(seat)
    return seat


def _overlapping_reservations(
    db: Session,
    seat_ids: set[int],
    start_at: datetime,
    end_at: datetime,
) -> list[Reservation]:
    if not seat_ids:
        return []
    records = list(
        db.scalars(
            select(Reservation)
            .where(
                Reservation.seat_id.in_(seat_ids),
                Reservation.status.in_(
                    (ReservationStatus.PENDING.value, ReservationStatus.IN_USE.value)
                ),
                Reservation.reserve_date >= start_at.date(),
                Reservation.reserve_date <= end_at.date(),
            )
            .order_by(Reservation.reserve_date, Reservation.start_time)
        ).all()
    )
    return [
        record
        for record in records
        if datetime.combine(record.reserve_date, record.start_time) < end_at
        and start_at < datetime.combine(record.reserve_date, record.end_time)
    ]


def list_occupancy(
    db: Session,
    room_id: int,
    reserve_date: date,
    start_time: time,
    end_time: time,
) -> list[dict]:
    """FR-003 / FR-031：座位资源状态 + 该时段占用（两个维度分开返回）。"""
    if end_time <= start_time:
        raise BusinessError(
            "查询时段不合法：结束时间必须晚于开始时间",
            code="INVALID_ARGUMENT",
            status_code=422,
        )
    seats = list(
        db.scalars(
            select(Seat)
            .where(Seat.room_id == room_id)
            .order_by(Seat.seat_no)
        ).all()
    )
    conflicts = _overlapping_reservations(
        db,
        {seat.id for seat in seats},
        datetime.combine(reserve_date, start_time),
        datetime.combine(reserve_date, end_time),
    )
    hit_by_seat = {record.seat_id: record for record in conflicts}
    return [
        {
            "seat": seat,
            "occupied": seat.id in hit_by_seat,
            "reservation": hit_by_seat.get(seat.id),
        }
        for seat in seats
    ]


def list_conflicts(
    db: Session,
    seat_ids: list[int],
    start_at: datetime,
    end_at: datetime,
) -> list[Reservation]:
    """BR-019：列出与「座位 + 调整窗口」冲突的有效预约，不自动取消。"""
    if not seat_ids:
        raise BusinessError(
            "请至少选择一个座位", code="INVALID_ARGUMENT", status_code=422
        )
    if start_at >= end_at:
        raise BusinessError(
            "调整窗口不合法：结束时间必须晚于开始时间",
            code="INVALID_ARGUMENT",
            status_code=422,
        )
    existing = set(
        db.scalars(select(Seat.id).where(Seat.id.in_(seat_ids))).all()
    )
    if len(existing) != len(set(seat_ids)):
        raise BusinessError(
            "部分座位不存在，请刷新后重试", code="SEAT_NOT_FOUND", status_code=404
        )
    return _overlapping_reservations(db, set(seat_ids), start_at, end_at)


def update_status_batch(
    db: Session,
    payload: SeatStatusBatchUpdate,
    operator_id: int,
) -> tuple[list[Seat], list[Reservation]]:
    """FR-004 + BR-022：批量调整资源状态。

    按 BR-019 口径不自动取消任何预约，只把冲突清单返回给调用方持续提示。
    """
    unique_ids = sorted(set(payload.seat_ids))
    seats = list(
        db.scalars(select(Seat).where(Seat.id.in_(unique_ids))).all()
    )
    if len(seats) != len(unique_ids):
        raise BusinessError(
            "部分座位不存在，请刷新后重试", code="SEAT_NOT_FOUND", status_code=404
        )

    new_status = (
        payload.status.value
        if isinstance(payload.status, SeatStatus)
        else payload.status
    )
    for seat in seats:
        seat.status = new_status

    conflicts: list[Reservation] = []
    if new_status != SeatStatus.AVAILABLE.value:
        now = datetime.now()
        conflicts = _overlapping_reservations(
            db,
            {seat.id for seat in seats},
            now,
            now + timedelta(days=settings.advance_booking_days),
        )

    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="SEAT_STATUS_BATCH",
        target_type="SEAT",
        target_id=None,
        reason=payload.reason,
        before_value=str({"seat_ids": unique_ids}),
        after_value=str(
            {
                "status": new_status,
                "conflict_reservation_ids": [item.id for item in conflicts],
            }
        ),
    )
    db.commit()
    for seat in seats:
        db.refresh(seat)
    return seats, conflicts
