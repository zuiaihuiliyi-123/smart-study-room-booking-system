from datetime import date, datetime, time, timedelta


def is_aligned(value: time, granularity_minutes: int) -> bool:
    """判断时间是否对齐预约粒度（BR-001，默认 30 分钟）。"""
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


def checkin_window(
    day: date,
    start_time: time,
    early_minutes: int,
    late_minutes: int,
) -> tuple[datetime, datetime]:
    """签到窗口 [s - early, s + late)（BR-007）。"""
    start_at = to_datetime(day, start_time)
    return (
        start_at - timedelta(minutes=early_minutes),
        start_at + timedelta(minutes=late_minutes),
    )


def is_cancellable(
    now: datetime,
    day: date,
    start_time: time,
    before_minutes: int,
) -> bool:
    """是否仍在无损取消时限内（开始前 N 分钟，默认 30 分钟）。"""
    return now <= to_datetime(day, start_time) - timedelta(minutes=before_minutes)
