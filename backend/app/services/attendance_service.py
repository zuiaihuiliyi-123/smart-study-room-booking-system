from sqlalchemy.orm import Session

from app.models.reservation import Reservation


def check_in(db: Session, user_id: int, reservation_id: int) -> Reservation:
    """M3 / FR-020：在 [s-15min, s+15min) 窗口内签到，状态 → 使用中。

    重复签到须幂等，不覆盖首次签到时间（FR-015）。
    """
    raise NotImplementedError("签到待实现")


def check_out(db: Session, user_id: int, reservation_id: int) -> Reservation:
    """M3 / FR-021：签退，状态“使用中” → “已完成”。

    未签退不产生违约；到达结束时间由定时任务自动完成（ST-025）。
    """
    raise NotImplementedError("签退待实现")
