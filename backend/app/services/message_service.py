from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.message import StationMessage
from app.schemas.common import PageResult
from app.schemas.message import MessageRead
from app.utils.pagination import to_offset


def list_my_messages(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[MessageRead]:
    """M7 / FR-060：查询本人站内通知（按时间倒序）。"""
    total = (
        db.scalar(
            select(func.count())
            .select_from(StationMessage)
            .where(StationMessage.user_id == user_id)
        )
        or 0
    )
    rows = db.scalars(
        select(StationMessage)
        .where(StationMessage.user_id == user_id)
        .order_by(StationMessage.created_at.desc(), StationMessage.id.desc())
        .offset(to_offset(page, page_size))
        .limit(page_size)
    )
    return PageResult[MessageRead](
        items=[MessageRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def unread_count(db: Session, user_id: int) -> int:
    """未读通知数（顶栏铃铛）。"""
    return (
        db.scalar(
            select(func.count())
            .select_from(StationMessage)
            .where(
                StationMessage.user_id == user_id,
                StationMessage.is_read.is_(False),
            )
        )
        or 0
    )


def mark_read(db: Session, user_id: int, message_id: int) -> StationMessage:
    """M7 / FR-060：将本人通知标记为已读（幂等）。"""
    message = db.get(StationMessage, message_id)
    if message is None:
        raise BusinessError(
            "通知不存在", code="MESSAGE_NOT_FOUND", status_code=404
        )
    if message.user_id != user_id:
        raise BusinessError(
            "只能操作本人的通知", code="FORBIDDEN", status_code=403
        )
    if not message.is_read:
        message.is_read = True
        db.commit()
        db.refresh(message)
    return message
