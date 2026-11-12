"""HTTP 层：管理员审计日志查询（D2）。"""

from datetime import datetime

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.enums import Role


def _login(api_client, student_no: str, password: str) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_logs(db, admin, student) -> None:
    db.add_all(
        [
            AuditLog(
                operator_id=admin.id,
                action_type="ROOM_UPDATE",
                target_type="ROOM",
                target_id=1,
                reason="调整闭馆时间",
                before_value="close_time=22:00",
                after_value="close_time=21:30",
                created_at=datetime(2026, 11, 1, 9, 0),
            ),
            AuditLog(
                operator_id=admin.id,
                action_type="SEAT_STATUS_BATCH",
                target_type="SEAT",
                target_id=10,
                reason="批量转维修",
                created_at=datetime(2026, 11, 2, 10, 0),
            ),
            AuditLog(
                operator_id=student.id,
                action_type="UNAUTHORIZED_ATTEMPT",
                target_type="api",
                target_id=None,
                reason="尝试执行管理员操作",
                created_at=datetime(2026, 11, 3, 11, 0),
            ),
            AuditLog(
                operator_id=None,
                action_type="LOGIN_FAILED",
                target_type="USER",
                target_id=None,
                reason="学号「S8600」凭证错误",
                created_at=datetime(2026, 11, 4, 12, 0),
            ),
        ]
    )
    db.commit()


def test_audit_logs_filters_and_pagination(
    api_client, db, make_user
) -> None:
    admin = make_user(
        student_no="A8601",
        name="审计管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    student = make_user(
        student_no="S8601",
        name="审计学生",
        password_hash=hash_password("student123"),
    )
    _seed_logs(db, admin, student)
    headers = _login(api_client, "A8601", "admin123")

    all_logs = api_client.get(
        "/api/v1/audit-logs", params={"page": 1, "page_size": 20}, headers=headers
    )
    assert all_logs.status_code == 200, all_logs.text
    # 4 条种子 + 本次管理员登录产生的 LOGIN_SUCCESS
    assert all_logs.json()["total"] == 5
    # 按 id 倒序：最后写入的本次登录 LOGIN_SUCCESS 在最前
    assert all_logs.json()["items"][0]["action_type"] == "LOGIN_SUCCESS"

    by_action = api_client.get(
        "/api/v1/audit-logs", params={"action_type": "ROOM_UPDATE"}, headers=headers
    )
    assert by_action.status_code == 200, by_action.text
    assert by_action.json()["total"] == 1
    assert by_action.json()["items"][0]["target_type"] == "ROOM"

    by_operator = api_client.get(
        "/api/v1/audit-logs", params={"operator_id": admin.id}, headers=headers
    )
    assert by_operator.status_code == 200, by_operator.text
    # 2 条种子 + 本次登录
    assert by_operator.json()["total"] == 3

    by_target = api_client.get(
        "/api/v1/audit-logs", params={"target_type": "SEAT"}, headers=headers
    )
    assert by_target.status_code == 200, by_target.text
    assert by_target.json()["total"] == 1
    assert by_target.json()["items"][0]["target_id"] == 10

    by_date = api_client.get(
        "/api/v1/audit-logs",
        params={"created_from": "2026-11-02", "created_to": "2026-11-03"},
        headers=headers,
    )
    assert by_date.status_code == 200, by_date.text
    assert by_date.json()["total"] == 2

    paged = api_client.get(
        "/api/v1/audit-logs", params={"page": 1, "page_size": 1}, headers=headers
    )
    assert paged.status_code == 200, paged.text
    assert paged.json()["total"] == 5
    assert len(paged.json()["items"]) == 1


def test_audit_logs_require_admin(api_client, make_user) -> None:
    make_user(
        student_no="S8602",
        name="普通学生",
        password_hash=hash_password("student123"),
    )
    headers = _login(api_client, "S8602", "student123")

    response = api_client.get("/api/v1/audit-logs", headers=headers)

    assert response.status_code == 403, response.text
