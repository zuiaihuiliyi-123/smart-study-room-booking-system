import logging

from app.core.database import SessionLocal
from app.services import blacklist_service

logger = logging.getLogger(__name__)


def release_expired_restrictions() -> None:
    """ST-042：自动限制到期后解除账户受限。

    注意：管理员手动加入的限制到期后不得由本任务自动解除（BR-010）。
    业务逻辑在 blacklist_service.release_expired，便于单测直接驱动。
    """
    with SessionLocal() as db:
        released = blacklist_service.release_expired(db)
    logger.info("黑名单到期处理：解除 %s 条自动限制", released)
