import logging

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def release_expired_restrictions() -> None:
    """ST-042：自动限制到期后解除账户受限。

    注意：管理员手动加入的限制到期后不得由本任务自动解除（BR-010）。
    """
    with SessionLocal() as db:
        # TODO: 查询 mode=自动 且 expire_at <= now 的记录并解除
        _ = db
        logger.info("黑名单到期处理：骨架任务，业务逻辑待实现")
