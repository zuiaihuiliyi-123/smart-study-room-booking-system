import logging

from app.core.database import SessionLocal
from app.services import complaint_service

logger = logging.getLogger(__name__)


def close_stale_complaints() -> None:
    """ST-063：已处理但超过关闭期限的投诉自动关闭。

    业务逻辑在 complaint_service.close_stale，便于单测直接驱动。
    """
    with SessionLocal() as db:
        closed = complaint_service.close_stale(db)
    logger.info("投诉自动关闭：关闭 %s 条投诉", closed)
