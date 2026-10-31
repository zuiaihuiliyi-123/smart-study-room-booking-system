from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.enums import MessageType, ReservationStatus, ViolationType
from app.models.reservation import Reservation
from app.models.user import User
from app.models.violation import ViolationRecord
from app.schemas.common import PageResult
from app.schemas.violation import ManualViolationCreate, ViolationRead
from app.services import (
    audit_service,
    blacklist_service,
    notification_service,
    reservation_service,
)
from app.utils import time_utils


def _get_reservation(db: Session, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise BusinessError(
            "预约单不存在", code="RESERVATION_NOT_FOUND", status_code=404
        )
    return reservation


def _find_violation(
    db: Session, reservation_id: int, violation_type: ViolationType
) -> ViolationRecord | None:
    return db.scalar(
        select(ViolationRecord).where(
            ViolationRecord.reservation_id == reservation_id,
            ViolationRecord.type == violation_type.value,
        )
    )


def _page(
    db: Session, conditions: list, page: int, page_size: int
) -> PageResult[ViolationRead]:
    total = (
        db.scalar(
            select(func.count()).select_from(ViolationRecord).where(*conditions)
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(ViolationRecord)
            .where(*conditions)
            .order_by(ViolationRecord.created_at.desc(), ViolationRecord.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PageResult[ViolationRead](
        items=[ViolationRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_my_violations(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[ViolationRead]:
    """M4 / FR-032：学生查询本人违约记录。"""
    return _page(db, [ViolationRecord.user_id == user_id], page, page_size)


def list_all_violations(
    db: Session,
    page: int,
    page_size: int,
    *,
    violation_type: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    student_no: str | None = None,
) -> PageResult[ViolationRead]:
    """M4 / FR-032：管理员查询全部违约记录。"""
    conditions: list = []
    if violation_type:
        conditions.append(ViolationRecord.type == violation_type)
    if created_from is not None:
        conditions.append(ViolationRecord.created_at >= datetime.combine(
            created_from, datetime.min.time()
        ))
    if created_to is not None:
        conditions.append(ViolationRecord.created_at < datetime.combine(
            created_to, datetime.min.time()
        ) + timedelta(days=1))
    if student_no:
        conditions.append(
            ViolationRecord.user_id.in_(
                select(User.id).where(User.student_no == student_no)
            )
        )
    return _page(db, conditions, page, page_size)


def _apply(
    db: Session,
    reservation: Reservation,
    *,
    violation_type: ViolationType,
    reason: str,
    operator_id: int | None,
    now: datetime,
) -> ViolationRecord:
    """写入违约记录、推进状态并触发阈值判定（幂等：预约单 + 类型）。

    调用方负责事务提交与站内通知。
    """
    existing = _find_violation(db, reservation.id, violation_type)
    if existing is not None:
        return existing

    record = ViolationRecord(
        user_id=reservation.user_id,
        reservation_id=reservation.id,
        type=violation_type.value,
        reason=reason,
        operator_id=operator_id,
        created_at=now,
    )
    db.add(record)
    reservation.status = ReservationStatus.VIOLATED.value
    reservation_service.release_slots(db, reservation.id)
    db.flush()

    # 回写累计有效违约次数；达到阈值时创建自动黑名单记录（BR-009 / ST-040）
    blacklist_service.restrict_if_threshold(db, reservation.user_id, now=now)
    return record


def register_manual(
    db: Session, admin: User, payload: ManualViolationCreate
) -> ViolationRecord:
    """M3 / FR-023 / ST-026：管理员对“使用中”预约登记违约，必须填写原因。

    与强制取消（ST-022）互斥：未开始的预约只能强制取消，不登记违约。
    """
    reason = (payload.reason or "").strip()
    if not reason:
        raise BusinessError(
            "请填写违约原因（必填）", code="REASON_REQUIRED", status_code=422
        )

    reservation = _get_reservation(db, payload.reservation_id)

    if reservation.status == ReservationStatus.VIOLATED.value:
        existing = _find_violation(db, reservation.id, ViolationType.MANUAL)
        if existing is not None:
            return existing  # 幂等：重复登记返回原记录，不重复累加
        raise BusinessError(
            "该预约已因自动违约被登记，不能重复登记",
            code="ST-026",
            status_code=409,
            details={"status": reservation.status},
        )

    if reservation.status != ReservationStatus.IN_USE.value:
        details = {"status": reservation.status}
        if reservation.status == ReservationStatus.PENDING.value:
            details["hint"] = "尚未开始的预约请使用强制取消（FR-011 / ST-022）"
        raise BusinessError(
            "手动违约登记只适用于「使用中」的预约单",
            code="ST-026",
            status_code=409,
            details=details,
        )

    user = db.get(User, reservation.user_id)
    if user is None:  # pragma: no cover - 外键保证
        raise BusinessError("预约单对应的用户不存在", code="USER_NOT_FOUND", status_code=404)

    before = {
        "status": reservation.status,
        "violation_count": user.violation_count,
    }
    now = time_utils.now()
    record = _apply(
        db,
        reservation,
        violation_type=ViolationType.MANUAL,
        reason=reason,
        operator_id=admin.id,
        now=now,
    )

    audit_service.record(
        db,
        operator_id=admin.id,
        action_type="MANUAL_VIOLATION",
        target_type="reservation",
        target_id=reservation.id,
        reason=reason,
        before_value=str(before),
        after_value=str(
            {
                "status": reservation.status,
                "violation_id": record.id,
                "violation_count": user.violation_count,
                "account_status": user.account_status,
            }
        ),
    )
    db.commit()
    db.refresh(record)

    notification_service.notify_safe(
        user_id=reservation.user_id,
        message_type=MessageType.VIOLATION,
        title="违约登记通知",
        content=f"你的预约（{reservation.reserve_date}）被管理员登记违约，原因：{reason}",
        related_type="违约记录",
        related_id=record.id,
    )
    return record


def apply_auto_violation(
    db: Session, reservation_id: int, now: datetime | None = None
) -> ViolationRecord | None:
    """M3 / FR-022 / ST-023：自动违约登记（幂等，按预约单 + 类型去重）。

    条件：当前时间 >= 预约开始 + 15 分钟，且状态仍为“待使用”。
    重复执行返回原记录或 None，不重复累加次数（ST-034）。
    """
    now = now or time_utils.now()
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        return None

    existing = _find_violation(db, reservation_id, ViolationType.AUTO)
    if reservation.status != ReservationStatus.PENDING.value:
        return existing

    deadline = time_utils.start_at(
        reservation.reserve_date, reservation.start_time
    ) + timedelta(minutes=settings.checkin_late_minutes)
    if now < deadline:
        return None

    if existing is not None:
        return existing

    record = _apply(
        db,
        reservation,
        violation_type=ViolationType.AUTO,
        reason=(
            f"超过签到截止时间（开始后 {settings.checkin_late_minutes} 分钟）仍未签到，"
            "系统自动判定违约"
        ),
        operator_id=None,
        now=now,
    )
    db.commit()
    db.refresh(record)

    notification_service.notify_safe(
        user_id=reservation.user_id,
        message_type=MessageType.VIOLATION,
        title="自动违约通知",
        content=(
            f"你预约的 {reservation.reserve_date} "
            f"{reservation.start_time.strftime('%H:%M')} 场次未按时签到，已记录违约。"
        ),
        related_type="违约记录",
        related_id=record.id,
    )
    return record
