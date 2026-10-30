from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.message import StationMessage
from app.schemas.common import PageResult


def list_my_messages(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[StationMessage]:
    """M7 / FR-060：查询本人站内通知。"""
    raise NotImplementedError("站内通知查询待实现")


def mark_read(db: Session, user_id: int, message_id: int) -> StationMessage:
    """M7 / FR-060：将本人通知标记为已读。"""
    raise NotImplementedError("通知已读待实现")
