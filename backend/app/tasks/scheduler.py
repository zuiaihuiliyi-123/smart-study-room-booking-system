from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.tasks.auto_end_reservation import finish_expired_reservations
from app.tasks.auto_violation import scan_auto_violations
from app.tasks.blacklist_expiry import release_expired_restrictions
from app.tasks.complaint_auto_close import close_stale_complaints

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        return
    if scheduler.running:
        return
    scheduler.add_job(
        scan_auto_violations,
        "interval",
        minutes=1,
        id="auto_violation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        finish_expired_reservations,
        "interval",
        minutes=1,
        id="auto_end_reservation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        release_expired_restrictions,
        "interval",
        minutes=10,
        id="blacklist_expiry",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        close_stale_complaints,
        "interval",
        hours=1,
        id="complaint_auto_close",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
