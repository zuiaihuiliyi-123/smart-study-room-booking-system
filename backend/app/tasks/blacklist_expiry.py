import logging

from app.core.database import SessionLocal
from app.services import blacklist_service

logger = logging.getLogger(__name__)


def release_expired_restrictions(now=None) -> int:
    """ST-042：自动限制到期后解除账户受限。

    管理员手动加入的限制（mode=手动）到期后**不得**由本任务自动解除（BR-010），
    必须由管理员显式调用解除接口（ST-043）。
    返回本次解除的限制记录数。
    """
    try:
        with SessionLocal() as db:
            count = blacklist_service.auto_release_expired(db, now)
        if count:
            logger.info("黑名单到期扫描完成：解除 %s 条自动限制", count)
        return count
    except Exception:  # pragma: no cover
        logger.exception("黑名单到期处理失败")
        return 0
