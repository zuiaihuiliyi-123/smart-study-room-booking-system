import logging
from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import ReservationStatus
from app.models.reservation import Reservation
from app.services import violation_service
from app.utils import time_utils

logger = logging.getLogger(__name__)


def scan_auto_violations(now=None) -> int:
    """M3 / FR-022：扫描超时未签到的预约并登记违约。

    条件：当前时间 >= 预约开始 + 15 分钟，且状态仍为“待使用”。
    每条预约独立事务；重复执行幂等（ST-034），不重复创建记录或累加次数。
    返回本次新增的违约记录数。
    """
    now = now or time_utils.now()

    with SessionLocal() as db:
        candidate_ids = list(
            db.scalars(
                select(Reservation.id).where(
                    Reservation.status == ReservationStatus.PENDING.value,
                    Reservation.reserve_date <= now.date(),
                )
            ).all()
        )

    created = 0
    for reservation_id in candidate_ids:
        with SessionLocal() as db:
            try:
                reservation = db.get(Reservation, reservation_id)
                if reservation is None:
                    continue
                if reservation.status != ReservationStatus.PENDING.value:
                    continue

                deadline = time_utils.start_at(
                    reservation.reserve_date, reservation.start_time
                ) + timedelta(minutes=settings.checkin_late_minutes)
                if now < deadline:
                    continue

                record = violation_service.apply_auto_violation(
                    db, reservation_id, now
                )
                if record is not None:
                    created += 1
            except Exception:  # pragma: no cover - 单条失败不影响其它预约
                db.rollback()
                logger.exception("自动违约处理失败：reservation_id=%s", reservation_id)

    if created:
        logger.info("自动违约扫描完成：新增 %s 条违约记录", created)
    return created
