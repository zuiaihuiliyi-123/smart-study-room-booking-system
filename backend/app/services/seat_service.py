from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.room import Area, Room
from app.models.seat import Seat
from app.schemas.seat import SeatCreate, SeatStatusUpdate
from app.services import audit_service, availability_service, reservation_service
from app.utils import time_utils

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    SeatStatus.AVAILABLE.value: {
        SeatStatus.MAINTENANCE.value,
        SeatStatus.DISABLED.value,
    },
    SeatStatus.MAINTENANCE.value: {
        SeatStatus.AVAILABLE.value,
        SeatStatus.DISABLED.value,
    },
    SeatStatus.DISABLED.value: {SeatStatus.AVAILABLE.value},
}


def list_seats(db: Session, room_id: int) -> list[Seat]:
    """M1 / FR-003：按自习室查询座位（含资源状态）。"""
    room = db.get(Room, room_id)
    if room is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)
    return list(
        db.scalars(
            select(Seat).where(Seat.room_id == room_id).order_by(Seat.seat_no)
        ).all()
    )


def create_seat(db: Session, payload: SeatCreate) -> Seat:
    """M1 / FR-002：新增座位，默认资源状态“可用”。"""
    room = db.get(Room, payload.room_id)
    if room is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)

    if payload.area_id is not None:
        area = db.get(Area, payload.area_id)
        if area is None or area.room_id != room.id:
            raise BusinessError(
                "区域不存在或不属于该自习室",
                code="AREA_NOT_FOUND",
                status_code=404,
            )

    exists = db.scalar(
        select(Seat).where(
            Seat.room_id == room.id, Seat.seat_no == payload.seat_no.strip()
        )
    )
    if exists is not None:
        raise BusinessError(
            "该自习室内座位编号已存在", code="SEAT_NO_DUPLICATED", status_code=409
        )

    seat = Seat(
        room_id=room.id,
        area_id=payload.area_id,
        seat_no=payload.seat_no.strip(),
        seat_type=payload.seat_type,
        has_power=payload.has_power,
        status=SeatStatus.AVAILABLE.value,
    )
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return seat


def _future_conflicts(db: Session, seat_id: int, now: datetime) -> list[Reservation]:
    """该座位未来仍生效的预约（BR-019：仅提示，不自动取消）。"""
    rows = list(
        db.scalars(
            select(Reservation).where(
                Reservation.seat_id == seat_id,
                Reservation.status.in_(availability_service.ACTIVE_STATUSES),
            )
        ).all()
    )
    return [
        row
        for row in rows
        if time_utils.to_datetime(row.reserve_date, row.end_time) > now
    ]


def update_seat_status(
    db: Session,
    seat_id: int,
    payload: SeatStatusUpdate,
    operator_id: int,
) -> Seat:
    """M1 / FR-004：调整座位资源状态（ST-001～ST-005）。

    存在冲突的未来预约时按 BR-019 默认口径处理：**只提示、不自动取消**，
    冲突预约清单写入审计日志。
    """
    seat = db.get(Seat, seat_id)
    if seat is None:
        raise BusinessError("座位不存在", code="SEAT_NOT_FOUND", status_code=404)

    reason = (payload.reason or "").strip()
    if not reason:
        # NFR-009：座位资源状态调整须记录原因
        raise BusinessError(
            "请填写座位状态变更原因（必填）",
            code="REASON_REQUIRED",
            status_code=422,
        )

    target = payload.status.value
    if target == seat.status:
        raise BusinessError(
            f"座位当前已是「{seat.status}」，无需重复变更",
            code="ST-001",
            status_code=409,
        )
    if target not in _ALLOWED_TRANSITIONS.get(seat.status, set()):
        raise BusinessError(
            f"不允许从「{seat.status}」直接变更为「{target}」",
            code="ST-001",
            status_code=409,
            details={
                "from": seat.status,
                "to": target,
                "allowed": sorted(_ALLOWED_TRANSITIONS.get(seat.status, set())),
            },
        )

    now = time_utils.now()
    conflicts = (
        _future_conflicts(db, seat.id, now)
        if target in (SeatStatus.MAINTENANCE.value, SeatStatus.DISABLED.value)
        else []
    )

    cancelled: list[Reservation] = []
    if conflicts and payload.cancel_conflicts:
        if not payload.confirm:
            raise BusinessError(
                "批量取消影响多条预约，须先列出影响清单并二次确认",
                code="BR-022",
                status_code=422,
                details={
                    "rule": "BR-022",
                    "conflicts": [
                        {
                            "reservation_id": item.id,
                            "reserve_date": item.reserve_date.isoformat(),
                            "start_time": item.start_time.isoformat(),
                            "end_time": item.end_time.isoformat(),
                        }
                        for item in conflicts
                    ],
                },
            )
        for item in conflicts:
            item.status = ReservationStatus.CANCELLED.value
            item.cancel_time = now
            item.cancel_reason = f"场地关闭批量取消：{reason}"
            item.cancelled_by_id = operator_id
            reservation_service.release_slots(db, item.id)
            cancelled.append(item)

    before = seat.status
    seat.status = target
    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="SEAT_STATUS_CHANGE",
        target_type="seat",
        target_id=seat.id,
        reason=reason,
        before_value=str({"status": before}),
        after_value=str(
            {
                "status": target,
                "conflict_reservation_ids": [item.id for item in conflicts],
                "cancelled_reservation_ids": [item.id for item in cancelled],
            }
        ),
    )
    if cancelled:
        audit_service.record(
            db,
            operator_id=operator_id,
            action_type="BATCH_CANCEL",
            target_type="seat",
            target_id=seat.id,
            reason=reason,
            before_value=str({"reservation_ids": [item.id for item in conflicts]}),
            after_value=str(
                {
                    "cancelled_reservation_ids": [item.id for item in cancelled],
                    "second_confirmed": True,
                }
            ),
        )
    db.commit()
    db.refresh(seat)
    return seat
