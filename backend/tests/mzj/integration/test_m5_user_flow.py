"""集成：M5 用户资料、脱敏与账户状态（HTTP + 数据库）。"""

from datetime import timedelta

from sqlalchemy import select

from app.models.audit_log import AuditLog


def test_user_list_masks_contacts_and_exposes_restrict_until(
    api_client,
    make_student,
    make_admin,
    make_blacklist,
    auth_headers,
    freeze_now,
) -> None:
    admin = make_admin()
    phone = make_student(student_no="S97001", contact="13800001234")
    email = make_student(student_no="S97002", contact="student@zju.edu.cn")
    auto = make_student(student_no="S97003")
    manual = make_student(student_no="S97004")
    now = freeze_now
    make_blacklist(
        auto.id,
        mode="自动",
        start_at=now - timedelta(days=1),
        expire_at=now + timedelta(days=6),
    )
    make_blacklist(
        manual.id,
        mode="手动",
        start_at=now - timedelta(days=1),
        expire_at=now + timedelta(days=6),
    )

    response = api_client.get(
        "/api/v1/users", headers=auth_headers(admin), params={"page_size": 100}
    )
    assert response.status_code == 200, response.text
    items = {item["id"]: item for item in response.json()["items"]}

    assert items[phone.id]["contact"] == "138****1234"
    assert items[email.id]["contact"] == "s******@zju.edu.cn"
    # 自动限制有预计解除时间；手动限制只能人工解除
    assert items[auto.id]["restrict_until"] is not None
    assert items[auto.id]["restrict_until"].startswith("2026-12-02T10:00:00")
    assert items[manual.id]["restrict_until"] is None

    # 本人读取本人资料保持明文
    me = api_client.get("/api/v1/users/me", headers=auth_headers(phone))
    assert me.status_code == 200
    assert me.json()["contact"] == "13800001234"


def test_account_status_disable_blocks_login_then_restore(
    api_client, db, make_student, make_admin, auth_headers
) -> None:
    student = make_student(student_no="S97005")
    admin = make_admin()
    headers = auth_headers(admin)
    path = f"/api/v1/users/{student.id}/account-status"

    disabled = api_client.patch(
        path,
        headers=headers,
        json={"account_status": "停用", "reason": "违规占座"},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["account_status"] == "停用"

    blocked = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S97005", "password": "Ss123456"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "ACCOUNT_DISABLED"

    restored = api_client.patch(
        path,
        headers=headers,
        json={"account_status": "正常", "reason": "核实后恢复"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["account_status"] == "正常"
    assert (
        api_client.post(
            "/api/v1/auth/login",
            json={"student_no": "S97005", "password": "Ss123456"},
        ).status_code
        == 200
    )

    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.action_type == "ACCOUNT_STATUS_UPDATE")
        .order_by(AuditLog.id)
    ).all()
    assert [(log.before_value, log.after_value) for log in logs] == [
        ("正常", "停用"),
        ("停用", "正常"),
    ]
    assert all(log.reason for log in logs)


def test_user_list_filters_and_pagination(
    api_client, make_student, make_admin, auth_headers
) -> None:
    admin = make_admin()
    make_student(student_no="S97010", name="张一")
    make_student(student_no="S97011", name="张二")
    make_student(student_no="S97012", name="李三")
    headers = auth_headers(admin)

    keyword = api_client.get(
        "/api/v1/users", headers=headers, params={"keyword": "S9701"}
    )
    assert keyword.status_code == 200
    assert keyword.json()["total"] == 3

    second_page = api_client.get(
        "/api/v1/users",
        headers=headers,
        params={"keyword": "S9701", "page": 2, "page_size": 2},
    )
    body = second_page.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1

    admins = api_client.get(
        "/api/v1/users", headers=headers, params={"role": "自习室管理员"}
    )
    assert admins.json()["total"] == 1
