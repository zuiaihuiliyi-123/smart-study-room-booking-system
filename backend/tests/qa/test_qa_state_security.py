"""阶段 3 · 状态机、权限与安全用例（只读业务代码，仅新增测试）。"""

from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.enums import (
    AccountStatus,
    BlacklistMode,
    ComplaintStatus,
    ReservationStatus,
    Role,
    SeatStatus,
    ViolationType,
)
from app.models.blacklist import BlacklistEntry
from app.models.complaint import Complaint
from app.models.reservation_slot import ReservationSlot
from app.models.violation import ViolationRecord
from app.services import (
    blacklist_service,
    complaint_service,
    notification_service,
    violation_service,
)
from app.utils import time_utils

FIXED_NOW = datetime(2026, 11, 24, 10, 0)
D1 = FIXED_NOW.date() + timedelta(days=1)


@pytest.fixture(autouse=True)
def _silence(monkeypatch):
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


def _admin(make_user, student_no: str = "A0001"):
    return make_user(
        student_no=student_no,
        name="管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("Aa123456"),
    )


def _slot(db, reservation) -> None:
    db.add(
        ReservationSlot(
            reservation_id=reservation.id,
            seat_id=reservation.seat_id,
            user_id=reservation.user_id,
            slot_start=datetime.combine(reservation.reserve_date, reservation.start_time),
        )
    )
    db.commit()


def test_cancel_deadline_is_strict(api_client, db, monkeypatch, make_user, make_room, make_seat):
    _student(make_user, "S0001")
    _student(make_user, "S0002")
    room = make_room()
    seat1 = make_seat(room.id)
    seat2 = make_seat(room.id)
    headers = _headers(api_client, "S0001")
    other_headers = _headers(api_client, "S0002")

    def book(seat_id: int, key: str, auth: dict[str, str]):
        return api_client.post(
            "/api/v1/reservations",
            headers=auth,
            json={
                "seat_id": seat_id,
                "reserve_date": D1.isoformat(),
                "start_time": "14:00",
                "end_time": "15:00",
                "idempotency_key": key,
            },
        )

    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    first = book(seat1.id, "qa-cancel-0001", headers)
    second = book(seat2.id, "qa-cancel-0002", other_headers)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    monkeypatch.setattr(
        time_utils, "now", lambda: datetime(2026, 11, 25, 13, 29)
    )
    allowed = api_client.post(
        f"/api/v1/reservations/{first.json()['id']}/cancel",
        headers=headers,
        json={"reason": "行程变化"},
    )
    assert allowed.status_code == 200, allowed.text

    monkeypatch.setattr(
        time_utils, "now", lambda: datetime(2026, 11, 25, 13, 30)
    )
    blocked = api_client.post(
        f"/api/v1/reservations/{second.json()['id']}/cancel",
        headers=other_headers,
        json={"reason": "行程变化"},
    )
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["code"] == "ST-029"


def test_checkin_window_left_and_right_edges(
    api_client, db, monkeypatch, make_user, make_room, make_seat, make_reservation
):
    user = _student(make_user)
    seat = make_seat(make_room().id)
    first = make_reservation(user.id, seat.id, reserve_date=D1, start_time=time(14, 0), end_time=time(16, 0))
    second = make_reservation(user.id, seat.id, reserve_date=D1, start_time=time(14, 0), end_time=time(16, 0))
    headers = _headers(api_client, "S0001")

    monkeypatch.setattr(time_utils, "now", lambda: datetime(2026, 11, 25, 13, 44))
    too_early = api_client.post(
        f"/api/v1/reservations/{first.id}/check-in", headers=headers
    )
    assert too_early.status_code == 422, too_early.text
    assert too_early.json()["code"] == "ST-027"

    monkeypatch.setattr(time_utils, "now", lambda: datetime(2026, 11, 25, 13, 45))
    at_left = api_client.post(
        f"/api/v1/reservations/{first.id}/check-in", headers=headers
    )
    assert at_left.status_code == 200, at_left.text

    monkeypatch.setattr(time_utils, "now", lambda: datetime(2026, 11, 25, 14, 14))
    late_ok = api_client.post(
        f"/api/v1/reservations/{second.id}/check-in", headers=headers
    )
    assert late_ok.status_code == 200, late_ok.text

    third = make_reservation(user.id, seat.id, reserve_date=D1, start_time=time(14, 0), end_time=time(16, 0))
    monkeypatch.setattr(time_utils, "now", lambda: datetime(2026, 11, 25, 14, 15))
    too_late = api_client.post(
        f"/api/v1/reservations/{third.id}/check-in", headers=headers
    )
    assert too_late.status_code == 422, too_late.text
    assert too_late.json()["code"] == "ST-027"


def test_checkout_completes_and_releases_slots(
    api_client, db, monkeypatch, make_user, make_room, make_seat, make_reservation
):
    user = _student(make_user)
    seat = make_seat(make_room().id)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=D1,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.IN_USE.value,
    )
    _slot(db, reservation)
    headers = _headers(api_client, "S0001")

    monkeypatch.setattr(time_utils, "now", lambda: datetime(2026, 11, 25, 15, 0))
    response = api_client.post(
        f"/api/v1/reservations/{reservation.id}/check-out", headers=headers
    )

    assert response.status_code == 200, response.text
    db.refresh(reservation)
    assert reservation.status == ReservationStatus.COMPLETED.value
    assert reservation.check_out_time == datetime(2026, 11, 25, 15, 0)
    assert db.query(ReservationSlot).filter_by(reservation_id=reservation.id).count() == 0


def test_auto_violation_boundary_and_idempotency(
    db, monkeypatch, make_user, make_room, make_seat, make_reservation
):
    user = _student(make_user)
    seat = make_seat(make_room().id)
    reservation = make_reservation(
        user.id, seat.id, reserve_date=D1, start_time=time(14, 0), end_time=time(16, 0)
    )
    _slot(db, reservation)

    before = violation_service.apply_auto_violation(
        db, reservation.id, now=datetime(2026, 11, 25, 14, 14)
    )
    assert before is None
    db.refresh(reservation)
    assert reservation.status == ReservationStatus.PENDING.value

    first = violation_service.apply_auto_violation(
        db, reservation.id, now=datetime(2026, 11, 25, 14, 15)
    )
    second = violation_service.apply_auto_violation(
        db, reservation.id, now=datetime(2026, 11, 25, 14, 16)
    )

    assert first is not None
    assert second is not None and second.id == first.id
    db.refresh(user)
    db.refresh(reservation)
    assert reservation.status == ReservationStatus.VIOLATED.value
    assert user.violation_count == 1
    assert db.query(ViolationRecord).filter_by(reservation_id=reservation.id).count() == 1
    assert db.query(ReservationSlot).filter_by(reservation_id=reservation.id).count() == 0


def test_manual_violation_requires_in_use_and_reason(
    api_client, db, make_user, make_room, make_seat, make_reservation
):
    user = _student(make_user)
    _admin(make_user)
    seat = make_seat(make_room().id)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=D1,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.IN_USE.value,
    )
    headers = _headers(api_client, "A0001", "Aa123456")

    no_reason = api_client.post(
        "/api/v1/violations/manual",
        headers=headers,
        json={"reservation_id": reservation.id, "reason": ""},
    )
    assert no_reason.status_code == 422, no_reason.text

    response = api_client.post(
        "/api/v1/violations/manual",
        headers=headers,
        json={"reservation_id": reservation.id, "reason": "长时间占座"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["operator_id"] is not None
    db.refresh(reservation)
    db.refresh(user)
    assert reservation.status == ReservationStatus.VIOLATED.value
    assert user.violation_count == 1


def test_third_violation_restricts_account(
    api_client, db, make_user, make_room, make_seat, make_reservation
):
    user = _student(make_user, violation_count=2)
    _admin(make_user)
    seat = make_seat(make_room().id)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=D1,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.IN_USE.value,
    )
    for index in range(2):
        history = make_reservation(
            user.id,
            seat.id,
            reserve_date=D1 - timedelta(days=index + 1),
            start_time=time(8, 0),
            end_time=time(9, 0),
            status=ReservationStatus.VIOLATED.value,
            idempotency_key=f"history-{index}",
        )
        db.add(
            ViolationRecord(
                user_id=user.id,
                reservation_id=history.id,
                type=ViolationType.AUTO.value,
                reason="历史违约",
                created_at=FIXED_NOW,
            )
        )
    db.commit()
    headers = _headers(api_client, "A0001", "Aa123456")

    response = api_client.post(
        "/api/v1/violations/manual",
        headers=headers,
        json={"reservation_id": reservation.id, "reason": "第三次违约"},
    )

    assert response.status_code == 200, response.text
    db.refresh(user)
    assert user.violation_count == 3
    assert user.account_status == AccountStatus.RESTRICTED.value
    entry = db.query(BlacklistEntry).filter_by(user_id=user.id, mode=BlacklistMode.AUTO.value).one()
    assert entry.released_at is None


def test_auto_restriction_expiry_resets_violation_count(
    db, make_user, make_room, make_seat, make_reservation
):
    """本轮裁决：自动限制到期解除后，累计违约次数清零。"""
    user = _student(make_user, violation_count=3, account_status=AccountStatus.RESTRICTED.value)
    seat = make_seat(make_room().id)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=D1,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.VIOLATED.value,
    )
    for index in range(3):
        history = make_reservation(
            user.id,
            seat.id,
            reserve_date=D1 - timedelta(days=index + 1),
            start_time=time(8, 0),
            end_time=time(9, 0),
            status=ReservationStatus.VIOLATED.value,
            idempotency_key=f"reset-history-{index}",
        )
        db.add(
            ViolationRecord(
                user_id=user.id,
                reservation_id=history.id,
                type=ViolationType.AUTO.value,
                reason="历史违约",
                created_at=FIXED_NOW,
            )
        )
    db.add(
        BlacklistEntry(
            user_id=user.id,
            reason="累计违约达到 3 次",
            mode=BlacklistMode.AUTO.value,
            start_at=FIXED_NOW - timedelta(days=7),
            expire_at=FIXED_NOW - timedelta(minutes=1),
            operator_id=None,
        )
    )
    db.commit()

    released = blacklist_service.release_expired(db, now=FIXED_NOW)

    db.refresh(user)
    assert released == 1
    assert user.account_status == AccountStatus.NORMAL.value
    assert user.violation_count == 0


def test_student_cross_user_and_vertical_permissions(
    api_client, db, make_user, make_room, make_seat, make_reservation
):
    owner = _student(make_user, "S0001")
    other = _student(make_user, "S0002")
    seat = make_seat(make_room().id)
    reservation = make_reservation(owner.id, seat.id, reserve_date=D1)
    headers_other = _headers(api_client, "S0002")

    cross_cancel = api_client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        headers=headers_other,
        json={"reason": "越权"},
    )
    assert cross_cancel.status_code == 403, cross_cancel.text

    for path in (
        "/api/v1/users",
        "/api/v1/audit-logs",
        "/api/v1/dashboard/overview",
        "/api/v1/blacklist",
    ):
        response = api_client.get(path, headers=headers_other)
        assert response.status_code == 403, f"{path}: {response.text}"


def test_admin_cannot_book_and_contacts_are_masked(
    api_client, db, monkeypatch, make_user, make_room, make_seat
):
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    student = _student(make_user, "S0001")
    student.contact = "13800138000"
    db.commit()
    _admin(make_user)
    seat = make_seat(make_room().id)

    admin_headers = _headers(api_client, "A0001", "Aa123456")
    booking = api_client.post(
        "/api/v1/reservations",
        headers=admin_headers,
        json={
            "seat_id": seat.id,
            "reserve_date": D1.isoformat(),
            "start_time": "14:00",
            "end_time": "15:00",
            "idempotency_key": "qa-admin-book-1",
        },
    )
    assert booking.status_code == 403, booking.text

    listing = api_client.get("/api/v1/users", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    row = next(item for item in listing.json()["items"] if item["student_no"] == "S0001")
    assert row["contact"] != "13800138000"
    assert "****" in row["contact"]


def test_password_change_invalidates_old_token(
    api_client, make_user
):
    _student(make_user)
    old_headers = _headers(api_client, "S0001")

    changed = api_client.patch(
        "/api/v1/users/me/password",
        headers=old_headers,
        json={"old_password": "Ss123456", "new_password": "Ss654321"},
    )
    assert changed.status_code == 200, changed.text

    old_token = api_client.get("/api/v1/auth/me", headers=old_headers)
    assert old_token.status_code == 401, old_token.text

    new_headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    new_token = api_client.get("/api/v1/auth/me", headers=new_headers)
    assert new_token.status_code == 200, new_token.text


def test_tampered_token_rejected(api_client, make_user):
    _student(make_user)
    headers = _headers(api_client, "S0001")
    token = headers["Authorization"].split(" ", 1)[1]
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")

    response = api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert response.status_code == 401, response.text


def test_logout_must_invalidate_token(api_client, make_user):
    """本轮裁决：登出后旧令牌立即失效。"""
    _student(make_user)
    headers = _headers(api_client, "S0001")

    logout = api_client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200, f"登出接口未实现或失败: {logout.status_code}"

    after = api_client.get("/api/v1/auth/me", headers=headers)
    assert after.status_code == 401, after.text


def test_login_rate_limit(api_client, make_user):
    """本轮裁决：登录接口按 IP 限流，超限 429。"""
    _student(make_user)
    statuses = []
    for _ in range(11):
        response = api_client.post(
            "/api/v1/auth/login",
            json={"student_no": "S0001", "password": "Ss123456"},
        )
        statuses.append(response.status_code)

    assert statuses[-1] == 429, f"连续 11 次登录的状态码: {statuses}"
    assert api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S0001", "password": "Ss123456"},
    ).headers.get("Retry-After") is not None


def test_student_message_isolation(
    api_client, db, make_user, make_room, make_seat, make_reservation
):
    from app.models.enums import MessageType
    from app.models.message import StationMessage

    _student(make_user, "S0001")
    other = _student(make_user, "S0002")
    message = StationMessage(
        user_id=other.id,
        type=MessageType.SYSTEM.value,
        title="他人消息",
        content="不应被读取",
        is_read=False,
    )
    db.add(message)
    db.commit()

    headers = _headers(api_client, "S0001")
    response = api_client.post(f"/api/v1/messages/{message.id}/read", headers=headers)
    assert response.status_code in (403, 404), response.text
    db.refresh(message)
    assert message.is_read is False


def test_complaint_state_machine_and_owner_confirm(
    api_client, db, make_user, make_room, make_seat
):
    _student(make_user, "S0001")
    _student(make_user, "S0002")
    _admin(make_user)
    room = make_room()
    seat = make_seat(room.id)
    student_headers = _headers(api_client, "S0001")
    admin_headers = _headers(api_client, "A0001", "Aa123456")

    created = api_client.post(
        "/api/v1/complaints",
        headers=student_headers,
        json={"target_type": "座位", "target_id": seat.id, "content": "座位有异味"},
    )
    assert created.status_code == 201, created.text
    complaint_id = created.json()["id"]

    illegal = api_client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers=admin_headers,
        json={"status": ComplaintStatus.RESOLVED.value, "handle_note": "直接完成"},
    )
    assert illegal.status_code == 409, illegal.text

    processing = api_client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers=admin_headers,
        json={"status": ComplaintStatus.PROCESSING.value, "handle_note": "已受理"},
    )
    assert processing.status_code == 200, processing.text

    resolved = api_client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers=admin_headers,
        json={"status": ComplaintStatus.RESOLVED.value, "handle_note": "已清洁"},
    )
    assert resolved.status_code == 200, resolved.text

    other_headers = _headers(api_client, "S0002")
    not_owner = api_client.post(
        f"/api/v1/complaints/{complaint_id}/confirm", headers=other_headers
    )
    assert not_owner.status_code == 403, not_owner.text

    closed = api_client.post(
        f"/api/v1/complaints/{complaint_id}/confirm", headers=student_headers
    )
    assert closed.status_code == 200, closed.text
    db.refresh(db.get(Complaint, complaint_id))
    assert db.get(Complaint, complaint_id).status == ComplaintStatus.CLOSED.value


def _available_seats_setup(api_client, make_user, make_room, make_seat, monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    _student(make_user)
    room = make_room()
    make_seat(room.id)
    return room, _headers(api_client, "S0001")


def test_available_seats_rejects_out_of_window_date(
    api_client, make_user, make_room, make_seat, monkeypatch
):
    """用户裁决 D2：available-seats 仅接受今日..今日+7。"""
    room, headers = _available_seats_setup(
        api_client, make_user, make_room, make_seat, monkeypatch
    )
    d8 = api_client.get(
        "/api/v1/reservations/available-seats",
        headers=headers,
        params={
            "room_id": room.id,
            "reserve_date": (
                FIXED_NOW.date() + timedelta(days=8)
            ).isoformat(),
            "start_time": "14:00",
            "end_time": "15:00",
        },
    )

    assert d8.status_code == 422, f"D+8 未被拒绝：{d8.status_code} {d8.text}"


def test_available_seats_rejects_misaligned_time(
    api_client, make_user, make_room, make_seat, monkeypatch
):
    """用户裁决 D2：available-seats 起止时间必须 5 分钟对齐。"""
    room, headers = _available_seats_setup(
        api_client, make_user, make_room, make_seat, monkeypatch
    )
    misaligned = api_client.get(
        "/api/v1/reservations/available-seats",
        headers=headers,
        params={
            "room_id": room.id,
            "reserve_date": D1.isoformat(),
            "start_time": "14:02",
            "end_time": "15:00",
        },
    )

    assert misaligned.status_code == 422, (
        f"非 5 分钟对齐未被拒绝：{misaligned.status_code} {misaligned.text}"
    )


def test_docs_disabled_in_production(monkeypatch):
    """裁决 D3：生产环境识别为 APP_ENV=production，接口文档关闭。"""
    from app.main import create_app

    monkeypatch.setattr(settings, "app_env", "production")
    production_app = create_app()
    assert production_app.docs_url is None
    assert production_app.openapi_url is None
    assert production_app.redoc_url is None

    monkeypatch.setattr(settings, "app_env", "development")
    development_app = create_app()
    assert development_app.docs_url == "/docs"
