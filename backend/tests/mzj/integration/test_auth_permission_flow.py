"""集成：认证与权限矩阵（HTTP + 数据库，含审计副作用）。"""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.enums import AccountStatus, Role
from app.models.login_attempt import LoginAttempt


def test_student_is_denied_admin_endpoints_and_audited(
    api_client, db, make_student, auth_headers
) -> None:
    student = make_student(student_no="S96001")
    headers = auth_headers(student)

    for path in (
        "/api/v1/users",
        "/api/v1/audit-logs",
        "/api/v1/dashboard/overview",
        "/api/v1/complaints",
        "/api/v1/reviews",
    ):
        response = api_client.get(path, headers=headers)
        assert response.status_code == 403, (path, response.text)

    logs = db.scalars(
        select(AuditLog).where(
            AuditLog.operator_id == student.id,
            AuditLog.action_type == "UNAUTHORIZED_ATTEMPT",
        )
    ).all()
    assert len(logs) == 5
    assert all(log.target_type == "api" for log in logs)


def test_admin_cannot_use_student_only_endpoints(
    api_client, make_student, make_admin, auth_headers
) -> None:
    admin = make_admin()
    headers = auth_headers(admin)
    make_student(student_no="S96002")

    assert (
        api_client.post(
            "/api/v1/complaints",
            headers=headers,
            json={"target_type": "自习室", "target_id": 1, "content": "空调太冷"},
        ).status_code
        == 403
    )
    assert (
        api_client.post(
            "/api/v1/reviews",
            headers=headers,
            json={"reservation_id": 1, "score": 5},
        ).status_code
        == 403
    )
    # 管理端自身接口保持可用
    assert api_client.get("/api/v1/users/me", headers=headers).status_code == 200
    assert api_client.get("/api/v1/users", headers=headers).status_code == 200
    assert api_client.get("/api/v1/audit-logs", headers=headers).status_code == 200
    assert api_client.get("/api/v1/dashboard/overview", headers=headers).status_code == 200


def test_system_admin_has_no_business_permissions(
    api_client, make_user, auth_headers
) -> None:
    sysadmin = make_user(
        student_no="R049601",
        name="系统管理员",
        role=Role.SYSTEM_ADMIN.value,
    )
    headers = auth_headers(sysadmin)

    for path in (
        "/api/v1/users",
        "/api/v1/audit-logs",
        "/api/v1/complaints",
        "/api/v1/dashboard/overview",
    ):
        assert api_client.get(path, headers=headers).status_code == 403, path


def test_logout_invalidates_old_token(api_client, make_student, login) -> None:
    student = make_student(student_no="S96003")
    headers = login(student.student_no)
    assert api_client.get("/api/v1/auth/me", headers=headers).status_code == 200

    assert api_client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert api_client.get("/api/v1/auth/me", headers=headers).status_code == 401

    new_headers = login(student.student_no)
    # 已失效的旧令牌不能再登出
    assert api_client.post("/api/v1/auth/logout", headers=headers).status_code == 401
    assert api_client.get("/api/v1/auth/me", headers=new_headers).status_code == 200


def test_change_password_rotates_token_without_leaking_secret(
    api_client, db, make_student, login
) -> None:
    student = make_student(student_no="S96004")
    headers = login(student.student_no)

    response = api_client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"old_password": "Ss123456", "new_password": "Ss654321"},
    )
    assert response.status_code == 200, response.text
    new_token = response.json()["access_token"]

    assert api_client.get("/api/v1/auth/me", headers=headers).status_code == 401
    new_headers = {"Authorization": f"Bearer {new_token}"}
    assert api_client.get("/api/v1/auth/me", headers=new_headers).status_code == 200

    log = db.scalars(
        select(AuditLog).where(AuditLog.action_type == "PASSWORD_CHANGED")
    ).one()
    text = " ".join(
        filter(None, [log.reason, log.before_value, log.after_value])
    )
    assert "Ss123456" not in text
    assert "Ss654321" not in text
    assert "$2b$" not in text


def test_disabled_account_is_rejected_and_attempts_cleared(
    api_client, db, make_student, make_login_attempt
) -> None:
    student = make_student(
        student_no="S96005", account_status=AccountStatus.DISABLED.value
    )
    make_login_attempt(
        student.student_no,
        failed_count=3,
        first_failed_at=datetime(2026, 11, 26, 9, 0),
        updated_at=datetime(2026, 11, 26, 9, 0) + timedelta(minutes=1),
    )

    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S96005", "password": "Ss123456"},
    )
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "ACCOUNT_DISABLED"
    assert db.get(LoginAttempt, ("S96005", "unknown")) is None

    token = create_access_token(str(student.id), student.role, 0)
    me = api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 403
