"""HTTP 层回归：登录、预约闭环、管理端筛选与看板、新增资源接口。"""

from datetime import datetime, time, timedelta

import pytest

from app.core.security import hash_password
from app.models.enums import Role
from app.services import notification_service
from app.utils import time_utils

FIXED_NOW = datetime(2026, 11, 2, 10, 0)


@pytest.fixture(autouse=True)
def _fixed_now(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _login(api_client, student_no: str, password: str) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _accounts(make_user):
    student = make_user(
        student_no="S1001",
        name="学生甲",
        password_hash=hash_password("student123"),
    )
    admin = make_user(
        student_no="A1001",
        name="管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    return student, admin


def test_student_reservation_flow_over_http(
    api_client, db, make_user, make_room, make_seat
) -> None:
    student, _ = _accounts(make_user)
    room = make_room()
    seat = make_seat(room.id)
    headers = _login(api_client, "S1001", "student123")
    day = (FIXED_NOW.date() + timedelta(days=1)).isoformat()

    created = api_client.post(
        "/api/v1/reservations",
        headers=headers,
        json={
            "seat_id": seat.id,
            "reserve_date": day,
            "start_time": "14:00",
            "end_time": "16:00",
            "idempotency_key": "http-flow-key-0001",
        },
    )
    assert created.status_code == 200, created.text
    reservation_id = created.json()["id"]

    mine = api_client.get("/api/v1/reservations/me", headers=headers)
    assert mine.status_code == 200
    assert mine.json()["total"] == 1

    available = api_client.get(
        "/api/v1/reservations/available-seats",
        headers=headers,
        params={
            "room_id": room.id,
            "reserve_date": day,
            "start_time": "14:00",
            "end_time": "16:00",
        },
    )
    assert available.status_code == 200
    assert available.json() == []

    dashboard = api_client.get("/api/v1/dashboard/overview", headers=headers)
    assert dashboard.status_code == 403

    messages = api_client.get("/api/v1/messages/me", headers=headers)
    assert messages.status_code == 200
    assert messages.json()["total"] == 0  # 测试中通知写入被禁用

    assert reservation_id > 0 and student.id > 0


def test_admin_filters_and_resource_endpoints(
    api_client, db, make_user, make_room, make_seat, make_reservation
) -> None:
    student, _ = _accounts(make_user)
    room = make_room()
    seat = make_seat(room.id)
    reservation = make_reservation(
        student.id,
        seat.id,
        reserve_date=FIXED_NOW.date() + timedelta(days=1),
        start_time=time(14, 0),
        end_time=time(16, 0),
    )
    headers = _login(api_client, "A1001", "admin123")

    listed = api_client.get(
        "/api/v1/reservations",
        headers=headers,
        params={"room_id": room.id, "student_no": "S1001"},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1

    detail = api_client.get(
        f"/api/v1/reservations/{reservation.id}", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == reservation.id

    occupancy = api_client.get(
        "/api/v1/seats/occupancy",
        headers=headers,
        params={
            "room_id": room.id,
            "reserve_date": reservation.reserve_date.isoformat(),
            "start_time": "15:00",
            "end_time": "16:00",
        },
    )
    assert occupancy.status_code == 200, occupancy.text
    assert occupancy.json()[0]["occupied"] is True

    conflicts = api_client.get(
        "/api/v1/seats/conflicts",
        headers=headers,
        params={
            "seat_ids": str(seat.id),
            "start_at": f"{reservation.reserve_date.isoformat()}T14:00",
            "end_at": f"{reservation.reserve_date.isoformat()}T15:00",
        },
    )
    assert conflicts.status_code == 200, conflicts.text
    assert conflicts.json()[0]["id"] == reservation.id

    batch = api_client.patch(
        "/api/v1/seats/status",
        headers=headers,
        json={
            "seat_ids": [seat.id],
            "status": "维修中",
            "reason": "检修",
        },
    )
    assert batch.status_code == 200, batch.text
    assert batch.json()["updated"][0]["status"] == "维修中"

    close_preview = api_client.get(
        f"/api/v1/rooms/{room.id}/close-preview",
        headers=headers,
        params={
            "start_at": f"{reservation.reserve_date.isoformat()}T13:00",
            "end_at": f"{reservation.reserve_date.isoformat()}T17:00",
        },
    )
    assert close_preview.status_code == 200, close_preview.text
    assert close_preview.json()["reservations"][0]["id"] == reservation.id

    overview = api_client.get(
        "/api/v1/dashboard/overview", headers=headers, params={"room_id": room.id}
    )
    assert overview.status_code == 200
    assert overview.json()["seat_total"] == 0  # 座位已转为维修中

    slot_usage = api_client.get(
        "/api/v1/dashboard/seat-usage",
        headers=headers,
        params={
            "start_date": FIXED_NOW.date().isoformat(),
            "end_date": FIXED_NOW.date().isoformat(),
            "group_by": "slot",
        },
    )
    assert slot_usage.status_code == 200, slot_usage.text
    assert len(slot_usage.json()) == 7
