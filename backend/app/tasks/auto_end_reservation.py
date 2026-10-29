import logging

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def finish_expired_reservations() -> None:
    """ST-025：结束时间已到且状态仍为“使用中”的预约自动转为“已完成”。

    未签退不产生违约（课程版口径）。
    """
    with SessionLocal() as db:
        # TODO: 查询结束时间已到的“使用中”预约并批量完成
        _ = db
        logger.info("自动结束预约：骨架任务，业务逻辑待实现")
