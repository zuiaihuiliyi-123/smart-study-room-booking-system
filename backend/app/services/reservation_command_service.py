"""预约命令服务（写操作）。

事务边界：每个公开命令函数只开启一个 ``transaction(db)``；校验在事务外只读，
业务异常原样抛出，成功提交后再发送站内通知。查询逻辑见 ``reservation_query_service``。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db_retry import run_with_db_retry
from app.core.exceptions import BusinessError
from app.core.transactions import transaction
from app.models.enums import MessageType, ReservationStatus
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.seat import Seat
from app.models.user import User
from app.schemas.reservation import CancelRequest, ForceCancelRequest, ReservationCreate
from app.services import audit_service, availability_service, notification_service
from app.services.reservation_query_service import get_reservation
from app.utils import time_utils


def _find_by_idempotency_key(
    db: Session, user_id: int, key: str
) -> Reservation | None:
    return db.scalar(
        select(Reservation)
        .where(
            Reservation.user_id == user_id,
            Reservation.idempotency_key == key,
        )
        .order_by(Reservation.id.desc())
    )


def _ensure_same_payload(existing: Reservation, payload: ReservationCreate) -> None:
    """同一幂等键只能对应同一「座位 + 时段」，否则拒绝（BR-021）。"""
    if (
        existing.seat_id != payload.seat_id
        or existing.reserve_date != payload.reserve_date
        or existing.start_time != payload.start_time
        or existing.end_time != payload.end_time
    ):
        raise BusinessError(
            "该幂等键已用于另一条预约请求，请使用新的幂等键",
            code="IDEMPOTENCY_KEY_REUSED",
            status_code=409,
        )


def release_slots(db: Session, reservation_id: int) -> None:
    """预约进入终态时删除占用槽位，使该时段自动重新可预约（LK-03 / LK-04）。"""
    db.execute(
        delete(ReservationSlot).where(
            ReservationSlot.reservation_id == reservation_id
        )
    )


def create_reservation(
    db: Session, user: User, payload: ReservationCreate
) -> Reservation:
    """M2 / FR-010：创建预约。"""
    existing = _find_by_idempotency_key(db, user.id, payload.idempotency_key)
    if existing is not None:
        _ensure_same_payload(existing, payload)
        return existing

    def operation() -> Reservation:
        with transaction(db):
            return _create_once(db, user, payload)

    reservation = run_with_db_retry(db, operation)
    db.refresh(reservation)
    notification_service.notify_safe(
        user_id=user.id,
        message_type=MessageType.RESERVATION,
        title="预约成功",
        content=(
            f"你已预约 {payload.reserve_date} "
            f"{payload.start_time.strftime('%H:%M')}-{payload.end_time.strftime('%H:%M')} 的座位，"
            f"请于开始前 {settings.checkin_early_minutes} 分钟至开始后 "
            f"{settings.checkin_late_minutes} 分钟内签到。"
        ),
        related_type="预约单",
        related_id=reservation.id,
    )
    return reservation


def _create_once(
    db: Session, user: User, payload: ReservationCreate
) -> Reservation:
    now = time_utils.now()

    existing = _find_by_idempotency_key(db, user.id, payload.idempotency_key)
    if existing is not None:
        _ensure_same_payload(existing, payload)
        return existing

    # 行锁：同一座位的预约串行化，同一用户的每日次数校验也串行化
    db.execute(
        select(Seat.id).where(Seat.id == payload.seat_id).with_for_update()
    )
    db.execute(select(User.id).where(User.id == user.id).with_for_update())

    availability_service.check_reservation_rules(
        db,
        user_id=user.id,
        seat_id=payload.seat_id,
        reserve_date=payload.reserve_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        now=now,
    )

    reservation = Reservation(
        user_id=user.id,
        seat_id=payload.seat_id,
        reserve_date=payload.reserve_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=ReservationStatus.PENDING.value,
        idempotency_key=payload.idempotency_key,
    )
    db.add(reservation)

    try:
        db.flush()  # 取预约单 id

        # 占用槽位：唯一约束 (seat_id, slot_start) / (user_id, slot_start)
        # 是 BR-005 / BR-006 / NFR-011 在持久层的最终保证
        cursor = datetime.combine(payload.reserve_date, payload.start_time)
        end_at = datetime.combine(payload.reserve_date, payload.end_time)
        while cursor < end_at:
            db.add(
                ReservationSlot(
                    reservation_id=reservation.id,
                    seat_id=payload.seat_id,
                    user_id=user.id,
                    slot_start=cursor,
                )
            )
            cursor += timedelta(minutes=settings.reservation_granularity_minutes)
        # 让唯一约束在事务内立即暴露，交给下方冲突分类；不要在这里 commit。
        db.flush()
    except IntegrityError:
        db.rollback()
        # 并发同幂等键：返回先落库的那一张
        existing = _find_by_idempotency_key(db, user.id, payload.idempotency_key)
        if existing is not None:
            _ensure_same_payload(existing, payload)
            return existing

        # 唯一约束冲突：区分座位占用（C3）与用户自身冲突（C4）
        seat_conflicts = availability_service._active_overlaps(
            db,
            seat_id=payload.seat_id,
            reserve_date=payload.reserve_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        if seat_conflicts:
            raise BusinessError(
                "该座位在所选时段已被占用",
                code="C3_BR-006",
                status_code=409,
                details={
                    "condition": "C3",
                    "rule": "BR-006",
                    "params": {
                        "conflicts": [
                            {
                                "reservation_id": item.id,
                                "start_time": item.start_time.isoformat(),
                                "end_time": item.end_time.isoformat(),
                            }
                            for item in seat_conflicts
                        ]
                    },
                },
            ) from None

        user_conflicts = availability_service._active_overlaps(
            db,
            user_id=user.id,
            reserve_date=payload.reserve_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        if user_conflicts:
            raise BusinessError(
                "你在该时段已有其他有效预约",
                code="C4_BR-005",
                status_code=409,
                details={
                    "condition": "C4",
                    "rule": "BR-005",
                    "params": {
                        "conflicts": [
                            {"reservation_id": item.id} for item in user_conflicts
                        ]
                    },
                },
            ) from None

        raise BusinessError(
            "该时段已被占用，请选择其他时段",
            code="ST-035",
            status_code=409,
        ) from None

    return reservation



def cancel_my_reservation(
    db: Session,
    user_id: int,
    reservation_id: int,
    payload: CancelRequest,
) -> Reservation:
    """M2 / FR-011：用户在开始前 30 分钟无损取消（ST-021）。"""
    reservation = get_reservation(db, reservation_id)

    if reservation.user_id != user_id:
        raise BusinessError(
            "只能取消本人的预约单", code="FORBIDDEN", status_code=403
        )
    if reservation.status != ReservationStatus.PENDING.value:
        message = (
            "该预约已取消"
            if reservation.status == ReservationStatus.CANCELLED.value
            else f"当前状态为「{reservation.status}」，不能取消"
        )
        raise BusinessError(
            message,
            code="ST-031",
            status_code=409,
            details={"status": reservation.status},
        )

    now = time_utils.now()
    if not time_utils.is_cancellable(
        now,
        reservation.reserve_date,
        reservation.start_time,
        settings.cancel_before_minutes,
    ):
        deadline = time_utils.cancel_deadline(
            reservation.reserve_date,
            reservation.start_time,
            settings.cancel_before_minutes,
        )
        raise BusinessError(
            f"已超过可取消时限（须在开始前 {settings.cancel_before_minutes} 分钟以上取消）",
            code="ST-029",
            status_code=422,
            details={
                "cancel_limit_minutes": settings.cancel_before_minutes,
                "cancel_deadline": deadline.isoformat(),
            },
        )

    reason = (payload.reason or "").strip() or None
    with transaction(db):
        reservation.status = ReservationStatus.CANCELLED.value
        reservation.cancel_time = now
        reservation.cancel_reason = reason
        release_slots(db, reservation.id)

    db.refresh(reservation)
    notification_service.notify_safe(
        user_id=reservation.user_id,
        message_type=MessageType.RESERVATION,
        title="预约已取消",
        content=f"你的预约（{reservation.reserve_date}）已取消，该时段已重新开放。",
        related_type="预约单",
        related_id=reservation.id,
    )
    return reservation


def force_cancel(
    db: Session,
    admin_id: int,
    reservation_id: int,
    payload: ForceCancelRequest,
) -> Reservation:
    """M2 / FR-011：管理员强制取消“待使用”预约，必须记录原因并审计（ST-022）。"""
    reason = (payload.reason or "").strip()
    if not reason:
        raise BusinessError(
            "请填写取消原因（必填）",
            code="REASON_REQUIRED",
            status_code=422,
        )

    reservation = get_reservation(db, reservation_id)
    if reservation.status != ReservationStatus.PENDING.value:
        details = {"status": reservation.status}
        if reservation.status == ReservationStatus.IN_USE.value:
            details["hint"] = "已开始使用的预约如需追责，请使用手动违约登记（FR-023）"
        raise BusinessError(
            f"当前状态为「{reservation.status}」，只能强制取消「待使用」的预约单",
            code="ST-022",
            status_code=409,
            details=details,
        )

    now = time_utils.now()
    before = {"status": reservation.status}
    with transaction(db):
        reservation.status = ReservationStatus.CANCELLED.value
        reservation.cancel_time = now
        reservation.cancel_reason = reason
        reservation.cancelled_by_id = admin_id
        release_slots(db, reservation.id)

        audit_service.record(
            db,
            operator_id=admin_id,
            action_type="RESERVATION_FORCE_CANCEL",
            target_type="reservation",
            target_id=reservation.id,
            reason=reason,
            before_value=str(before),
            after_value=str({"status": reservation.status}),
        )

    db.refresh(reservation)
    notification_service.notify_safe(
        user_id=reservation.user_id,
        message_type=MessageType.RESERVATION,
        title="预约已被管理员取消",
        content=f"你的预约（{reservation.reserve_date}）已被管理员取消，原因：{reason}",
        related_type="预约单",
        related_id=reservation.id,
    )
    return reservation

