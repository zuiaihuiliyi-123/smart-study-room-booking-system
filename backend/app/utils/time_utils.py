from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings


def now() -> datetime:
    """返回统一业务时区（默认 Asia/Shanghai）的 naive datetime。

    需求 TB-12 / NFR-010：签到窗口、自动违约等判定统一以服务器时间为准，
    不使用客户端时间。MySQL 的 DATETIME 不保存时区，因此约定：
    - 数据库与后端业务时间统一存 Asia/Shanghai 的墙上时间；
    - 前端按本地展示；
    - JWT 等安全令牌仍使用 UTC（见 core/security.py），不与业务时间混用。
    """
    zone = ZoneInfo(settings.app_timezone)
    return datetime.now(zone).replace(tzinfo=None, microsecond=0)


def is_aligned(value: time, granularity_minutes: int) -> bool:
    """判断时间是否对齐预约粒度（BR-001，当前默认 5 分钟）。"""
    minutes = value.hour * 60 + value.minute
    return (
        value.second == 0
        and value.microsecond == 0
        and minutes % granularity_minutes == 0
    )


def intervals_overlap(
    start1: time,
    end1: time,
    start2: time,
    end2: time,
) -> bool:
    """左闭右开 [s, e) 的重叠判定（BR-020）：s1 < e2 且 s2 < e1。"""
    return start1 < end2 and start2 < end1


def to_datetime(day: date, value: time) -> datetime:
    return datetime.combine(day, value)


def start_at(day: date, start_time: time) -> datetime:
    return datetime.combine(day, start_time)


def end_at(day: date, end_time: time) -> datetime:
    return datetime.combine(day, end_time)


def duration(day: date, start_time: time, end_time: time) -> timedelta:
    return end_at(day, end_time) - start_at(day, start_time)


def checkin_window(
    day: date,
    start_time: time,
    early_minutes: int,
    late_minutes: int,
) -> tuple[datetime, datetime]:
    """签到窗口 [s - early, s + late)（BR-007）。"""
    start = start_at(day, start_time)
    return (
        start - timedelta(minutes=early_minutes),
        start + timedelta(minutes=late_minutes),
    )


def is_in_checkin_window(
    now: datetime,
    day: date,
    start_time: time,
    early_minutes: int,
    late_minutes: int,
) -> bool:
    window_start, window_end = checkin_window(
        day, start_time, early_minutes, late_minutes
    )
    return window_start <= now < window_end


def is_cancellable(
    now: datetime,
    day: date,
    start_time: time,
    before_minutes: int,
) -> bool:
    """是否仍在无损取消时限内（TB-09：提交时刻 < s − N 分钟）。"""
    return now < start_at(day, start_time) - timedelta(minutes=before_minutes)


def cancel_deadline(day: date, start_time: time, before_minutes: int) -> datetime:
    return start_at(day, start_time) - timedelta(minutes=before_minutes)
