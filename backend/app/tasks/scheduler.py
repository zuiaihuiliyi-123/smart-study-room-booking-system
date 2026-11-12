from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.tasks.auto_end_reservation import finish_expired_reservations
from app.tasks.auto_violation import scan_auto_violations
from app.tasks.blacklist_expiry import release_expired_restrictions
from app.tasks.complaint_auto_close import close_stale_complaints
from app.tasks.runtime import run_scheduled_task

scheduler = BackgroundScheduler(timezone=settings.app_timezone)


def _job(task_name: str, operation):
    return lambda: run_scheduled_task(task_name, operation)


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        return
    if scheduler.running:
        return
    common_options = {
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": settings.scheduler_misfire_grace_seconds,
        "replace_existing": True,
    }
    scheduler.add_job(
        _job("auto_violation", scan_auto_violations),
        "interval",
        minutes=1,
        id="auto_violation",
        name="自动违约扫描",
        **common_options,
    )
    scheduler.add_job(
        _job("auto_end_reservation", finish_expired_reservations),
        "interval",
        minutes=1,
        id="auto_end_reservation",
        name="自动结束预约",
        **common_options,
    )
    scheduler.add_job(
        _job("blacklist_expiry", release_expired_restrictions),
        "interval",
        minutes=10,
        id="blacklist_expiry",
        name="黑名单到期解除",
        **common_options,
    )
    scheduler.add_job(
        _job("complaint_auto_close", close_stale_complaints),
        "interval",
        hours=1,
        id="complaint_auto_close",
        name="投诉超时关闭",
        **common_options,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
