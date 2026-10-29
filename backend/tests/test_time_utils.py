from datetime import date, datetime, time

from app.utils.time_utils import (
    checkin_window,
    intervals_overlap,
    is_aligned,
    is_cancellable,
)


def test_adjacent_intervals_do_not_overlap() -> None:
    assert not intervals_overlap(time(14, 0), time(16, 0), time(16, 0), time(18, 0))


def test_partial_overlap_is_detected() -> None:
    assert intervals_overlap(time(14, 0), time(16, 0), time(15, 0), time(17, 0))


def test_granularity_alignment() -> None:
    assert is_aligned(time(14, 0), 30)
    assert is_aligned(time(14, 30), 30)
    assert not is_aligned(time(14, 15), 30)


def test_checkin_window() -> None:
    start, end = checkin_window(date(2026, 10, 29), time(14, 0), 15, 15)
    assert start == datetime(2026, 10, 29, 13, 45)
    assert end == datetime(2026, 10, 29, 14, 15)


def test_cancel_deadline() -> None:
    day = date(2026, 10, 29)
    assert is_cancellable(datetime(2026, 10, 29, 13, 30), day, time(14, 0), 30)
    assert not is_cancellable(datetime(2026, 10, 29, 13, 31), day, time(14, 0), 30)
