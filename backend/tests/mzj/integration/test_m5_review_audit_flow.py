"""集成：M5 评价全链路与审计日志（HTTP + 数据库）。"""

from datetime import date

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.enums import ReservationStatus


def test_review_flow_and_admin_filters(
    api_client,
    make_student,
    make_admin,
    make_room,
    make_seat,
    make_reservation,
    auth_headers,
) -> None:
    owner = make_student(student_no="S99001")
    other = make_student(student_no="S99002")
    admin = make_admin()
    room = make_room()
    seat = make_seat(room.id)
    completed = make_reservation(
        owner.id, seat.id, status=ReservationStatus.COMPLETED.value
    )
    pending = make_reservation(
        other.id,
        seat.id,
        reserve_date=date(2099, 1, 2),
        status=ReservationStatus.PENDING.value,
    )
    owner_headers = auth_headers(owner)
    other_headers = auth_headers(other)
    admin_headers = auth_headers(admin)

    created = api_client.post(
        "/api/v1/reviews",
        headers=owner_headers,
        json={"reservation_id": completed.id, "score": 5, "content": "很安静"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["score"] == 5

    duplicate = api_client.post(
        "/api/v1/reviews",
        headers=owner_headers,
        json={"reservation_id": completed.id, "score": 4},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "REVIEW_ALREADY_EXISTS"

    not_owner = api_client.post(
        "/api/v1/reviews",
        headers=other_headers,
        json={"reservation_id": completed.id, "score": 5},
    )
    assert not_owner.status_code == 403
    assert not_owner.json()["code"] == "REVIEW_NOT_OWNER"

    not_completed = api_client.post(
        "/api/v1/reviews",
        headers=other_headers,
        json={"reservation_id": pending.id, "score": 5},
    )
    assert not_completed.status_code == 409
    assert not_completed.json()["code"] == "REVIEW_NOT_ALLOWED"

    invalid_score = api_client.post(
        "/api/v1/reviews",
        headers=owner_headers,
        json={"reservation_id": completed.id, "score": 6},
    )
    assert invalid_score.status_code == 422
    assert invalid_score.json()["code"] == "VALIDATION_ERROR"

    listed = api_client.get(
        "/api/v1/reviews", headers=admin_headers, params={"score": 5}
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    mine = api_client.get("/api/v1/reviews/me", headers=owner_headers)
    assert mine.json()["total"] == 1
    others = api_client.get("/api/v1/reviews/me", headers=other_headers)
    assert others.json()["total"] == 0


def test_audit_log_records_core_actions_and_supports_filters(
    api_client, db, make_student, make_admin, make_complaint, auth_headers
) -> None:
    subject = make_student(student_no="S99010")
    actor = make_admin()
    viewer = make_admin()
    complaint = make_complaint(subject.id)
    subject_headers = auth_headers(subject)
    actor_headers = auth_headers(actor)
    viewer_headers = auth_headers(viewer)

    # 1) 登录失败
    api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S99010", "password": "wrong-password"},
    )
    # 2) 越权尝试
    assert api_client.get("/api/v1/users", headers=subject_headers).status_code == 403
    # 3) 投诉处理
    assert (
        api_client.patch(
            f"/api/v1/complaints/{complaint.id}",
            headers=actor_headers,
            json={"status": "处理中", "handle_note": "已受理"},
        ).status_code
        == 200
    )
    # 4) 账户状态变更
    assert (
        api_client.patch(
            f"/api/v1/users/{subject.id}/account-status",
            headers=actor_headers,
            json={"account_status": "停用", "reason": "测试停用"},
        ).status_code
        == 200
    )
    # 5) 主动登出
    assert api_client.post("/api/v1/auth/logout", headers=actor_headers).status_code == 200

    actions = set(db.scalars(select(AuditLog.action_type)).all())
    assert {
        "LOGIN_FAILED",
        "UNAUTHORIZED_ATTEMPT",
        "COMPLAINT_HANDLE",
        "ACCOUNT_STATUS_UPDATE",
        "LOGOUT",
    } <= actions

    by_action = api_client.get(
        "/api/v1/audit-logs",
        headers=viewer_headers,
        params={"action_type": "COMPLAINT_HANDLE"},
    )
    assert by_action.status_code == 200
    assert by_action.json()["total"] == 1

    by_operator = api_client.get(
        "/api/v1/audit-logs",
        headers=viewer_headers,
        params={"operator_id": actor.id},
    )
    assert by_operator.json()["total"] >= 3

    today = date.today().isoformat()
    by_date = api_client.get(
        "/api/v1/audit-logs",
        headers=viewer_headers,
        params={"created_from": today, "created_to": today},
    )
    assert by_date.status_code == 200
    assert by_date.json()["total"] >= 5

    page = api_client.get(
        "/api/v1/audit-logs",
        headers=viewer_headers,
        params={"page": 1, "page_size": 1},
    )
    assert page.json()["total"] >= 5
    assert len(page.json()["items"]) == 1


def test_audit_response_never_contains_credentials(
    api_client, make_student, make_admin, login, auth_headers
) -> None:
    student = make_student(student_no="S99020")
    viewer = make_admin()
    headers = login(student.student_no)

    changed = api_client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"old_password": "Ss123456", "new_password": "Ss654321"},
    )
    assert changed.status_code == 200, changed.text

    response = api_client.get(
        "/api/v1/audit-logs",
        headers=auth_headers(viewer),
        params={"page_size": 100},
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    text = response.text
    for secret in ("Ss123456", "Ss654321", "$2b$", "access_token"):
        assert secret not in text
