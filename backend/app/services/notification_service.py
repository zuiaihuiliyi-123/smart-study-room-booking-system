import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.enums import MessageType
from app.models.message import StationMessage

logger = logging.getLogger(__name__)


def notify(
    db: Session,
    *,
    user_id: int,
    message_type: MessageType,
    title: str,
    content: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    """M7 / FR-060：写入站内通知（不接短信/邮件/微信）。"""
    db.add(
        StationMessage(
            user_id=user_id,
            type=message_type.value,
            title=title,
            content=content,
            related_type=related_type,
            related_id=related_id,
        )
    )
    db.flush()


def notify_safe(**kwargs) -> None:
    """独立会话写入通知：失败只记日志，不回滚、不阻塞业务结果。"""
    try:
        with SessionLocal() as db:
            notify(db, **kwargs)
            db.commit()
    except Exception:  # pragma: no cover - 通知属非关键路径
        logger.exception("站内通知写入失败：%s", kwargs.get("title"))
