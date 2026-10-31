"""M5 投诉管理（FR-042/FR-043，状态机 SM-04）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus, ComplaintTargetType
from app.models.reservation import Reservation
from app.models.room import Room
from app.models.seat import Seat
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.complaint import ComplaintCreate, ComplaintHandle, ComplaintRead
from app.services import audit_service
from app.utils.pagination import to_offset

# SM-04（ST-060～ST-063）：允许的状态迁移
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    ComplaintStatus.PENDING.value: {
        ComplaintStatus.PROCESSING.value,  # ST-060 受理
        ComplaintStatus.REJECTED.value,  # ST-061 驳回
    },
    ComplaintStatus.PROCESSING.value: {
        ComplaintStatus.RESOLVED.value,  # ST-062 录入处理结果
    },
    ComplaintStatus.RESOLVED.value: {
        ComplaintStatus.CLOSED.value,  # ST-063 关闭
    },
    ComplaintStatus.REJECTED.value: set(),
    ComplaintStatus.CLOSED.value: set(),
}

_TARGET_MODELS = {
    ComplaintTargetType.SEAT.value: Seat,
    ComplaintTargetType.ROOM.value: Room,
    ComplaintTargetType.RESERVATION.value: Reservation,
    ComplaintTargetType.USER.value: User,
}


def _ensure_target_exists(db: Session, target_type: str, target_id: int) -> None:
    """投诉对象必须真实存在（DR-007）。"""
    model = _TARGET_MODELS.get(target_type)
    if model is None:
        raise BusinessError(
            "投诉对象类型不合法", code="COMPLAINT_TARGET_TYPE_INVALID", status_code=422
        )
    if db.get(model, target_id) is None:
        raise BusinessError(
            "投诉对象不存在", code="COMPLAINT_TARGET_NOT_FOUND", status_code=404
        )


def create_complaint(
    db: Session, user_id: int, payload: ComplaintCreate
) -> Complaint:
    """M5 / FR-042：提交投诉，初始状态“待处理”。"""
    target_type = (
        payload.target_type.value
        if isinstance(payload.target_type, ComplaintTargetType)
        else payload.target_type
    )
    _ensure_target_exists(db, target_type, payload.target_id)

    complaint = Complaint(
        user_id=user_id,
        target_type=target_type,
        target_id=payload.target_id,
        content=payload.content,
        status=ComplaintStatus.PENDING.value,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def list_my_complaints(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[ComplaintRead]:
    """M5 / FR-042：查询本人投诉进度与反馈（按提交时间倒序）。"""
    total = (
        db.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.user_id == user_id)
        )
        or 0
    )
    rows = db.scalars(
        select(Complaint)
        .where(Complaint.user_id == user_id)
        .order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .offset(to_offset(page, page_size))
        .limit(page_size)
    )
    return PageResult[ComplaintRead](
        items=[ComplaintRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_all_complaints(
    db: Session,
    page: int,
    page_size: int,
    *,
    status: str | None = None,
    target_type: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
) -> PageResult[ComplaintRead]:
    """M5 / FR-043：管理员查询投诉列表（按提交时间倒序）。"""
    conditions: list = []
    if status:
        conditions.append(Complaint.status == status)
    if target_type:
        conditions.append(Complaint.target_type == target_type)
    if created_from is not None:
        conditions.append(
            Complaint.created_at
            >= datetime.combine(created_from, datetime.min.time())
        )
    if created_to is not None:
        conditions.append(
            Complaint.created_at
            < datetime.combine(created_to, datetime.min.time())
            + timedelta(days=1)
        )

    total = (
        db.scalar(
            select(func.count()).select_from(Complaint).where(*conditions)
        )
        or 0
    )
    rows = db.scalars(
        select(Complaint)
        .where(*conditions)
        .order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .offset(to_offset(page, page_size))
        .limit(page_size)
    )
    return PageResult[ComplaintRead](
        items=[ComplaintRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def handle_complaint(
    db: Session, admin: User, complaint_id: int, payload: ComplaintHandle
) -> Complaint:
    """M5 / FR-043：受理、处理或驳回投诉。

    - 只允许 SM-04 中定义的迁移（待处理→处理中/已驳回；处理中→已处理；已处理→已关闭）；
    - 必须填写处理说明，记录处理人与处理时间（NFR-009 审计）。
    """
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise BusinessError("投诉不存在", code="COMPLAINT_NOT_FOUND", status_code=404)

    current = complaint.status
    target = (
        payload.status.value
        if isinstance(payload.status, ComplaintStatus)
        else payload.status
    )
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise BusinessError(
            f"投诉状态不能从“{current}”变更为“{target}”",
            code="COMPLAINT_STATE_INVALID",
            status_code=409,
        )

    complaint.status = target
    complaint.handler_id = admin.id
    complaint.handle_note = payload.handle_note
    complaint.handled_at = datetime.now()

    audit_service.record(
        db,
        operator_id=admin.id,
        action_type="COMPLAINT_HANDLE",
        target_type="COMPLAINT",
        target_id=complaint.id,
        reason=payload.handle_note,
        before_value=current,
        after_value=target,
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def close_stale(db: Session, now: datetime | None = None) -> int:
    """ST-063：已处理且超过关闭期限的投诉自动关闭。

    关闭期限为候选值（settings.complaint_close_days，默认 7 天；BR-014 相关，待确认）。
    返回本次关闭的投诉数。
    """
    current = now or datetime.now()
    deadline = current - timedelta(days=settings.complaint_close_days)
    stmt = select(Complaint).where(
        Complaint.status == ComplaintStatus.RESOLVED.value,
        Complaint.handled_at.is_not(None),
        Complaint.handled_at <= deadline,
    )
    rows = list(db.scalars(stmt))
    if not rows:
        return 0

    for row in rows:
        row.status = ComplaintStatus.CLOSED.value
    db.commit()
    return len(rows)
