import logging

from app.core.database import SessionLocal
from app.services import auth_service

logger = logging.getLogger(__name__)


def cleanup_login_attempts() -> int:
    """Q4-02(E)：清理超过保留期的登录失败计数，返回删除行数。

    业务逻辑在 ``auth_service.cleanup_login_attempts``，便于单测直接驱动。
    """
    with SessionLocal() as db:
        removed = auth_service.cleanup_login_attempts(db)
    logger.info("登录失败计数清理：删除 %s 条", removed)
    return removed
