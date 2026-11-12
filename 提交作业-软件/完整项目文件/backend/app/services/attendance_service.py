from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus
from app.models.reservation import Reservation
from app.services import reservation_service
from app.utils import time_utils


def _get_reservation(db: Session, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise BusinessError(
            "预约单不存在", code="RESERVATION_NOT_FOUND", status_code=404
        )
    return reservation


def check_in(db: Session, user_id: int, reservation_id: int) -> Reservation:
    """M3 / FR-020：在 [s-15min, s+15min) 窗口内签到，状态 → 使用中。

    重复签到拒绝且不覆盖首次签到时间（ST-030，FR-015）。
    """
    reservation = _get_reservation(db, reservation_id)
    if reservation.user_id != user_id:
        raise BusinessError(
            "只能对本人的预约单签到", code="FORBIDDEN", status_code=403
        )

    if reservation.status == ReservationStatus.IN_USE.value:
        raise BusinessError(
            f"已签到（签到时间：{reservation.check_in_time}），无需重复签到",
            code="ST-030",
            status_code=409,
            details={
                "status": reservation.status,
                "check_in_time": (
                    reservation.check_in_time.isoformat()
                    if reservation.check_in_time
                    else None
                ),
            },
        )
    if reservation.status != ReservationStatus.PENDING.value:
        raise BusinessError(
            f"该预约已结束（当前状态：{reservation.status}），无法签到",
            code="ST-031",
            status_code=409,
            details={"status": reservation.status},
        )

    now = time_utils.now()
    window_start, window_end = time_utils.checkin_window(
        reservation.reserve_date,
        reservation.start_time,
        settings.checkin_early_minutes,
        settings.checkin_late_minutes,
    )
    if now < window_start:
        raise BusinessError(
            f"签到尚未开放，签到窗口为 {window_start:%Y-%m-%d %H:%M} ~ {window_end:%Y-%m-%d %H:%M}",
            code="ST-027",
            status_code=422,
            details={
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            },
        )
    if now >= window_end:
        raise BusinessError(
            f"已超过签到截止时间（{window_end:%Y-%m-%d %H:%M}），无法签到",
            code="ST-027",
            status_code=422,
            details={
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            },
        )

    reservation.status = ReservationStatus.IN_USE.value
    reservation.check_in_time = now
    db.commit()
    db.refresh(reservation)
    return reservation


def check_out(db: Session, user_id: int, reservation_id: int) -> Reservation:
    """M3 / FR-021：签退，状态“使用中” → “已完成”（ST-024）。

    未签退不产生违约；到达结束时间由定时任务自动完成（ST-025）。
    """
    reservation = _get_reservation(db, reservation_id)
    if reservation.user_id != user_id:
        raise BusinessError(
            "只能对本人的预约单签退", code="FORBIDDEN", status_code=403
        )

    if reservation.status == ReservationStatus.PENDING.value:
        raise BusinessError(
            "该预约尚未签到，请先签到后再签退",
            code="ST-031",
            status_code=409,
            details={"status": reservation.status},
        )
    if reservation.status != ReservationStatus.IN_USE.value:
        raise BusinessError(
            f"该预约已结束（当前状态：{reservation.status}），无法签退",
            code="ST-031",
            status_code=409,
            details={"status": reservation.status},
        )

    reservation.status = ReservationStatus.COMPLETED.value
    reservation.check_out_time = time_utils.now()
    reservation_service.release_slots(db, reservation.id)
    db.commit()
    db.refresh(reservation)
    return reservation
