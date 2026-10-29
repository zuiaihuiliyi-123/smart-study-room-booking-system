import logging

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def scan_auto_violations() -> None:
    """M3 / FR-022：扫描超时未签到的预约并登记违约。

    条件：当前时间 >= 预约开始 + 15 分钟，且状态仍为“待使用”。
    重复执行必须幂等（ST-034），不得重复创建记录或累加次数。
    """
    with SessionLocal() as db:
        # TODO: 查询超时预约 → violation_service.apply_auto_violation
        _ = db
        logger.info("自动违约扫描：骨架任务，业务逻辑待实现")
