import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.enums import ReservationStatus
from app.models.reservation import Reservation
from app.services import reservation_service
from app.utils import time_utils

logger = logging.getLogger(__name__)


def finish_expired_reservations(now=None) -> int:
    """ST-025：结束时间已到且状态仍为“使用中”的预约自动转为“已完成”。

    未签退不产生违约（课程版口径，Q-005）。
    返回本次自动完成的预约数。
    """
    now = now or time_utils.now()

    with SessionLocal() as db:
        candidate_ids = list(
            db.scalars(
                select(Reservation.id).where(
                    Reservation.status == ReservationStatus.IN_USE.value,
                    Reservation.reserve_date <= now.date(),
                )
            ).all()
        )

    completed = 0
    for reservation_id in candidate_ids:
        with SessionLocal() as db:
            try:
                reservation = db.get(Reservation, reservation_id)
                if reservation is None:
                    continue
                if reservation.status != ReservationStatus.IN_USE.value:
                    continue

                end_at = time_utils.to_datetime(
                    reservation.reserve_date, reservation.end_time
                )
                if end_at > now:
                    continue

                reservation.status = ReservationStatus.COMPLETED.value
                reservation.auto_completed = True
                reservation.check_out_time = end_at
                reservation_service.release_slots(db, reservation.id)
                db.commit()
                completed += 1
            except Exception:  # pragma: no cover
                db.rollback()
                logger.exception("自动结束预约失败：reservation_id=%s", reservation_id)

    if completed:
        logger.info("自动结束扫描完成：结束 %s 条预约", completed)
    return completed
