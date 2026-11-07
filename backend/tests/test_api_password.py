"""HTTP 层：本人自助修改密码（B1）与旧令牌失效。"""

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.models.audit_log import AuditLog


def _login(api_client, student_no: str, password: str) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_change_password_rotates_token_and_invalidates_old(
    api_client, db, make_user
) -> None:
    user = make_user(
        student_no="S8201",
        name="改密学生",
        password_hash=hash_password("student123"),
    )
    headers = _login(api_client, "S8201", "student123")
    old_token = headers["Authorization"].split(" ", 1)[1]

    changed = api_client.patch(
        "/api/v1/users/me/password",
        json={"old_password": "student123", "new_password": "newpass123"},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    new_token = changed.json()["access_token"]
    assert new_token != old_token

    db.refresh(user)
    assert user.token_version == 1
    assert verify_password("newpass123", user.password_hash)
    assert not verify_password("student123", user.password_hash)

    # 旧令牌立即失效
    old_me = api_client.get("/api/v1/auth/me", headers=headers)
    assert old_me.status_code == 401, old_me.text

    # 新令牌仍可用
    new_headers = {"Authorization": f"Bearer {new_token}"}
    new_me = api_client.get("/api/v1/auth/me", headers=new_headers)
    assert new_me.status_code == 200, new_me.text

    # 旧密码不能再登录，新密码可以
    old_login = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S8201", "password": "student123"},
    )
    assert old_login.status_code == 401, old_login.text
    new_login = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S8201", "password": "newpass123"},
    )
    assert new_login.status_code == 200, new_login.text

    audit = db.scalar(
        select(AuditLog).where(AuditLog.action_type == "PASSWORD_CHANGED")
    )
    assert audit is not None
    assert audit.target_id == user.id


def test_change_password_rejects_wrong_old_and_same(
    api_client, db, make_user
) -> None:
    user = make_user(
        student_no="S8202",
        name="改密学生",
        password_hash=hash_password("student123"),
    )
    headers = _login(api_client, "S8202", "student123")

    wrong = api_client.patch(
        "/api/v1/users/me/password",
        json={"old_password": "wrongpass", "new_password": "newpass123"},
        headers=headers,
    )
    assert wrong.status_code == 400, wrong.text
    assert wrong.json()["code"] == "INVALID_OLD_PASSWORD"

    same = api_client.patch(
        "/api/v1/users/me/password",
        json={"old_password": "student123", "new_password": "student123"},
        headers=headers,
    )
    assert same.status_code == 400, same.text
    assert same.json()["code"] == "PASSWORD_UNCHANGED"

    db.refresh(user)
    assert verify_password("student123", user.password_hash)
    assert user.token_version == 0


def test_change_password_validates_lengths(api_client, make_user) -> None:
    make_user(
        student_no="S8203",
        name="改密学生",
        password_hash=hash_password("student123"),
    )
    headers = _login(api_client, "S8203", "student123")

    short_new = api_client.patch(
        "/api/v1/users/me/password",
        json={"old_password": "student123", "new_password": "short"},
        headers=headers,
    )
    assert short_new.status_code == 422, short_new.text

    short_old = api_client.patch(
        "/api/v1/users/me/password",
        json={"old_password": "short", "new_password": "newpass123"},
        headers=headers,
    )
    assert short_old.status_code == 422, short_old.text

    blank_new = api_client.patch(
        "/api/v1/users/me/password",
        json={"old_password": "student123", "new_password": "        "},
        headers=headers,
    )
    assert blank_new.status_code == 422, blank_new.text
