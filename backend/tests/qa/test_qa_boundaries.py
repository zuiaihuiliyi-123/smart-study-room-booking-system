"""阶段 3 · 预约时间边界与规则用例（只读业务代码，仅新增测试）。

覆盖：跨日、0 分钟、结束早于开始、5 分钟对齐、4 小时上限、7/8 天窗口、
开放时间边界、相邻区间、每日 2 条、座位/自习室状态、幂等重放、受限用户。
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from app.core.security import hash_password
from app.models.enums import AccountStatus, Role, SeatStatus
from app.services import notification_service
from app.utils import time_utils

FIXED_NOW = datetime(2026, 11, 24, 10, 0)
D0 = FIXED_NOW.date()
D1 = D0 + timedelta(days=1)
D7 = D0 + timedelta(days=7)
D8 = D0 + timedelta(days=8)


@pytest.fixture(autouse=True)
def _freeze_and_silence(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _headers(api_client, student_no: str, password: str = "Ss123456") -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _student(make_user, student_no: str = "S0001", **kwargs):
    return make_user(
        student_no=student_no,
        name=f"学生{student_no}",
        password_hash=hash_password("Ss123456"),
        **kwargs,
    )


def _book(api_client, headers, seat_id: int, day, start: str, end: str, key: str):
    return api_client.post(
        "/api/v1/reservations",
        headers=headers,
        json={
            "seat_id": seat_id,
            "reserve_date": day.isoformat(),
            "start_time": start,
            "end_time": end,
            "idempotency_key": key,
        },
    )


def test_cross_day_interval_rejected(api_client, make_user, make_room, make_seat):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    response = _book(api_client, headers, seat.id, D0, "23:30", "01:00", "qa-cross-day-01")

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "C6_BR-020"
    assert api_client.get("/api/v1/reservations/me", headers=headers).json()["total"] == 0


def test_zero_and_reversed_duration_rejected(api_client, make_user, make_room, make_seat):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    zero = _book(api_client, headers, seat.id, D1, "14:00", "14:00", "qa-zero-0001")
    reversed_ = _book(api_client, headers, seat.id, D1, "15:00", "14:00", "qa-rev-00001")

    assert zero.status_code == 422, zero.text
    assert reversed_.status_code == 422, reversed_.text
    assert api_client.get("/api/v1/reservations/me", headers=headers).json()["total"] == 0


def test_start_and_end_must_align_to_five_minutes(
    api_client, make_user, make_room, make_seat
):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    bad_start = _book(api_client, headers, seat.id, D1, "14:02", "16:00", "qa-align-001")
    bad_end = _book(api_client, headers, seat.id, D1, "14:00", "15:58", "qa-align-002")
    okay = _book(api_client, headers, seat.id, D1, "14:05", "15:55", "qa-align-003")

    assert bad_start.status_code == 422, bad_start.text
    assert bad_end.status_code == 422, bad_end.text
    assert okay.status_code == 200, okay.text


def test_max_duration_four_hours(api_client, make_user, make_room, make_seat):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    four_hours = _book(api_client, headers, seat.id, D1, "10:00", "14:00", "qa-4h-00001")
    over = _book(api_client, headers, seat.id, D1, "14:05", "18:10", "qa-4h-00002")

    assert four_hours.status_code == 200, four_hours.text
    assert over.status_code == 422, over.text


def test_advance_window_d7_allowed_d8_rejected(
    api_client, make_user, make_room, make_seat
):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    d7 = _book(api_client, headers, seat.id, D7, "14:00", "15:00", "qa-d7-00001")
    d8 = _book(api_client, headers, seat.id, D8, "14:00", "15:00", "qa-d8-00001")
    past = _book(api_client, headers, seat.id, D0, "09:00", "10:00", "qa-past-0001")

    assert d7.status_code == 200, d7.text
    assert d8.status_code == 422, d8.text
    assert past.status_code == 422, past.text


def test_start_must_be_strictly_after_now(api_client, make_user, make_room, make_seat):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    same_minute = _book(api_client, headers, seat.id, D0, "10:00", "11:00", "qa-now-00001")
    next_slot = _book(api_client, headers, seat.id, D0, "10:05", "11:05", "qa-now-00002")

    assert same_minute.status_code == 422, same_minute.text
    assert next_slot.status_code == 200, next_slot.text


def test_room_open_hours_boundaries(api_client, make_user, make_room, make_seat):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    before_open = _book(api_client, headers, seat.id, D1, "07:55", "08:05", "qa-open-0001")
    left_edge = _book(api_client, headers, seat.id, D1, "08:00", "09:00", "qa-open-0002")
    close_edge = _book(api_client, headers, seat.id, D1, "21:55", "22:00", "qa-open-0003")
    after_close = _book(api_client, headers, seat.id, D1, "21:55", "22:05", "qa-open-0004")

    assert before_open.status_code == 409, before_open.text
    assert before_open.json()["code"] == "C2"
    assert left_edge.status_code == 200, left_edge.text
    assert close_edge.status_code == 200, close_edge.text
    assert after_close.status_code == 409, after_close.text
    assert after_close.json()["code"] == "C2"


def test_half_open_adjacent_intervals_allowed(
    api_client, make_user, make_room, make_seat
):
    _student(make_user, "S0001")
    _student(make_user, "S0002")
    seat = make_seat(make_room().id)
    headers1 = _headers(api_client, "S0001")
    headers2 = _headers(api_client, "S0002")

    first = _book(api_client, headers1, seat.id, D1, "14:00", "16:00", "qa-adj-00001")
    overlap = _book(api_client, headers2, seat.id, D1, "15:00", "17:00", "qa-adj-00002")
    adjacent = _book(api_client, headers2, seat.id, D1, "16:00", "17:00", "qa-adj-00003")

    assert first.status_code == 200, first.text
    assert overlap.status_code == 409, overlap.text
    assert overlap.json()["code"] == "C3_BR-006"
    assert adjacent.status_code == 200, adjacent.text


def test_same_user_overlap_rejected_but_adjacent_allowed(
    api_client, make_user, make_room, make_seat
):
    _student(make_user)
    room = make_room()
    seat1 = make_seat(room.id)
    seat2 = make_seat(room.id)
    headers = _headers(api_client, "S0001")

    first = _book(api_client, headers, seat1.id, D1, "14:00", "16:00", "qa-user-0001")
    overlap = _book(api_client, headers, seat2.id, D1, "15:00", "17:00", "qa-user-0002")
    adjacent = _book(api_client, headers, seat2.id, D1, "16:00", "17:00", "qa-user-0003")

    assert first.status_code == 200, first.text
    assert overlap.status_code == 409, overlap.text
    assert overlap.json()["code"] == "C4_BR-005"
    assert adjacent.status_code == 200, adjacent.text


def test_daily_limit_two_and_cancel_releases_quota(
    api_client, make_user, make_room, make_seat
):
    _student(make_user)
    room = make_room()
    seats = [make_seat(room.id) for _ in range(3)]
    headers = _headers(api_client, "S0001")

    first = _book(api_client, headers, seats[0].id, D1, "08:00", "09:00", "qa-daily-001")
    second = _book(api_client, headers, seats[1].id, D1, "10:00", "11:00", "qa-daily-002")
    third = _book(api_client, headers, seats[2].id, D1, "12:00", "13:00", "qa-daily-003")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert third.status_code == 422, third.text
    assert third.json()["code"] == "C6_BR-004"

    cancelled = api_client.post(
        f"/api/v1/reservations/{first.json()['id']}/cancel",
        headers=headers,
        json={"reason": "临时有事"},
    )
    assert cancelled.status_code == 200, cancelled.text

    retry = _book(api_client, headers, seats[2].id, D1, "12:00", "13:00", "qa-daily-004")
    assert retry.status_code == 200, retry.text


def test_seat_and_room_resource_states_block_booking(
    api_client, make_user, make_room, make_seat
):
    _student(make_user)
    room = make_room()
    fix = make_seat(room.id, status=SeatStatus.MAINTENANCE.value)
    off = make_seat(room.id, status=SeatStatus.DISABLED.value)
    disabled_room = make_room(enabled=False)
    disabled_seat = make_seat(disabled_room.id)
    headers = _headers(api_client, "S0001")

    fix_resp = _book(api_client, headers, fix.id, D1, "14:00", "15:00", "qa-fix-00001")
    off_resp = _book(api_client, headers, off.id, D1, "14:00", "15:00", "qa-off-00001")
    room_resp = _book(
        api_client, headers, disabled_seat.id, D1, "14:00", "15:00", "qa-room-0001"
    )

    assert fix_resp.status_code == 409, fix_resp.text
    assert fix_resp.json()["code"] == "C1_BR-017"
    assert off_resp.status_code == 409, off_resp.text
    assert room_resp.status_code == 409, room_resp.text


def test_restricted_and_disabled_accounts(api_client, make_user, make_room, make_seat):
    restricted = _student(make_user, "S0001", account_status=AccountStatus.RESTRICTED.value)
    _student(make_user, "S0002", account_status=AccountStatus.DISABLED.value)
    seat = make_seat(make_room().id)

    login_disabled = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S0002", "password": "Ss123456"},
    )
    assert login_disabled.status_code == 403, login_disabled.text

    headers = _headers(api_client, restricted.student_no)
    response = _book(api_client, headers, seat.id, D1, "14:00", "15:00", "qa-limit-001")
    assert response.status_code == 403, response.text


def test_idempotent_replay_and_key_reuse(api_client, make_user, make_room, make_seat):
    _student(make_user)
    seat = make_seat(make_room().id)
    headers = _headers(api_client, "S0001")

    first = _book(api_client, headers, seat.id, D1, "14:00", "16:00", "qa-idem-0001")
    replay = _book(api_client, headers, seat.id, D1, "14:00", "16:00", "qa-idem-0001")
    reused = _book(api_client, headers, seat.id, D1, "16:00", "17:00", "qa-idem-0001")
    short_key = _book(api_client, headers, seat.id, D1, "18:00", "19:00", "short")

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    assert reused.status_code == 409, reused.text
    assert reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert short_key.status_code == 422, short_key.text
    assert api_client.get("/api/v1/reservations/me", headers=headers).json()["total"] == 1


def test_available_seats_excludes_occupied_and_releases_after_cancel(
    api_client, make_user, make_room, make_seat
):
    _student(make_user, "S0001")
    _student(make_user, "S0002")
    room = make_room()
    seat = make_seat(room.id)
    headers1 = _headers(api_client, "S0001")
    headers2 = _headers(api_client, "S0002")

    created = _book(api_client, headers1, seat.id, D1, "14:00", "16:00", "qa-avail-001")
    assert created.status_code == 200, created.text

    params = {
        "room_id": room.id,
        "reserve_date": D1.isoformat(),
        "start_time": "14:00",
        "end_time": "16:00",
    }
    occupied = api_client.get(
        "/api/v1/reservations/available-seats", headers=headers2, params=params
    )
    assert occupied.status_code == 200, occupied.text
    assert seat.id not in {item["id"] for item in occupied.json()}

    api_client.post(
        f"/api/v1/reservations/{created.json()['id']}/cancel",
        headers=headers1,
        json={"reason": "test"},
    )
    freed = api_client.get(
        "/api/v1/reservations/available-seats", headers=headers2, params=params
    )
    assert freed.status_code == 200, freed.text
    assert seat.id in {item["id"] for item in freed.json()}


def test_registration_ignores_role_field(api_client):
    response = api_client.post(
        "/api/v1/auth/register",
        json={
            "name": "提权测试",
            "student_no": "QA9001",
            "password": "Ss123456",
            "role": Role.ADMIN.value,
        },
    )

    assert response.status_code == 201, response.text
    me = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["role"] == Role.STUDENT.value
