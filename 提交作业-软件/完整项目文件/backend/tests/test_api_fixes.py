"""回归：权限边界、投诉确认关闭、限制解除时间与参数校验。"""

from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.enums import Role
from app.services import blacklist_service, notification_service
from app.utils import time_utils

FIXED_NOW = datetime(2026, 11, 2, 10, 0)


@pytest.fixture(autouse=True)
def _fixed_now_and_silent_notifications(monkeypatch):
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
        student_no="S9001",
        name="学生",
        password_hash=hash_password("student123"),
    )
    admin = make_user(
        student_no="A9001",
        name="管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    return student, admin


def test_admin_cannot_create_reservation_or_complaint(
    api_client, db, make_user
) -> None:
    _, _ = _accounts(make_user)
    admin_headers = _login(api_client, "A9001", "admin123")
    day = (FIXED_NOW.date() + timedelta(days=1)).isoformat()

    reserved = api_client.post(
        "/api/v1/reservations",
        headers=admin_headers,
        json={
            "seat_id": 1,
            "reserve_date": day,
            "start_time": "14:00",
            "end_time": "16:00",
            "idempotency_key": "admin-booking-key",
        },
    )
    assert reserved.status_code == 403, reserved.text

    complaint = api_client.post(
        "/api/v1/complaints",
        headers=admin_headers,
        json={"target_type": "自习室", "target_id": 1, "content": "管理员不应提交"},
    )
    assert complaint.status_code == 403, complaint.text


def test_complaint_owner_confirms_close_over_http(
    api_client, db, make_user, make_room
) -> None:
    student, _ = _accounts(make_user)
    room = make_room()
    student_headers = _login(api_client, "S9001", "student123")
    admin_headers = _login(api_client, "A9001", "admin123")

    created = api_client.post(
        "/api/v1/complaints",
        headers=student_headers,
        json={"target_type": "自习室", "target_id": room.id, "content": "空调太冷"},
    )
    assert created.status_code == 201, created.text
    complaint_id = created.json()["id"]

    for target, note in (("处理中", "已受理"), ("已处理", "已调整")):
        handled = api_client.patch(
            f"/api/v1/complaints/{complaint_id}",
            headers=admin_headers,
            json={"status": target, "handle_note": note},
        )
        assert handled.status_code == 200, handled.text

    # ST-063：管理员不能直接关闭
    denied = api_client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers=admin_headers,
        json={"status": "已关闭", "handle_note": "管理员关闭"},
    )
    assert denied.status_code == 409, denied.text

    confirmed = api_client.post(
        f"/api/v1/complaints/{complaint_id}/confirm", headers=student_headers
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "已关闭"


def test_auth_me_exposes_restrict_until_for_auto_restriction(
    api_client, db, make_user
) -> None:
    student = make_user(
        student_no="S9002",
        password_hash=hash_password("student123"),
        violation_count=settings.violation_threshold,
    )
    entry = blacklist_service.restrict_if_threshold(db, student.id)
    assert entry is not None

    headers = _login(api_client, "S9002", "student123")
    profile = api_client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["account_status"] == "受限"
    assert profile.json()["restrict_until"] is not None


def test_room_close_rejects_area_from_another_room(
    api_client, db, make_user, make_room, make_area
) -> None:
    _, _ = _accounts(make_user)
    room = make_room()
    other_room = make_room()
    other_area = make_area(other_room.id, "B 区")
    headers = _login(api_client, "A9001", "admin123")

    response = api_client.post(
        f"/api/v1/rooms/{room.id}/close",
        headers=headers,
        json={
            "start_at": "2026-11-03T13:00",
            "end_at": "2026-11-03T17:00",
            "area_id": other_area.id,
            "reason": "考试封场",
            "cancel_affected": False,
            "expected_reservation_ids": [],
        },
    )
    assert response.status_code == 404, response.text


def test_login_is_audited_and_queryable_by_admin(
    api_client, db, make_user
) -> None:
    student, _ = _accounts(make_user)
    student_headers = _login(api_client, "S9001", "student123")
    admin_headers = _login(api_client, "A9001", "admin123")

    response = api_client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={"action_type": "LOGIN_SUCCESS"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 2
    assert any(item["operator_id"] == student.id for item in body["items"])

    # 学生不能查询审计日志
    denied = api_client.get("/api/v1/audit-logs", headers=student_headers)
    assert denied.status_code == 403


def test_messages_unread_count_endpoint(api_client, db, make_user) -> None:
    student, _ = _accounts(make_user)
    notification_service.notify(
        db,
        user_id=student.id,
        message_type=notification_service.MessageType.SYSTEM,
        title="测试",
        content="内容",
    )
    db.commit()

    headers = _login(api_client, "S9001", "student123")
    response = api_client.get("/api/v1/messages/unread-count", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"count": 1}
