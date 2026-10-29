from __future__ import annotations

from app.models.audit_log import AuditLog
from app.models.enums import AccountStatus
from app.models.user import User
from tests.conftest import API, fresh


def test_login_success_and_me(client, base):
    response = client.post(
        f"{API}/auth/login",
        json={"student_no": "student1", "password": "student123"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    me = client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["student_no"] == "student1"
    assert me.json()["role"] == "学生用户"
    assert me.json()["account_status"] == "正常"
    assert me.json()["violation_count"] == 0


def test_login_wrong_password(client, base):
    response = client.post(
        f"{API}/auth/login",
        json={"student_no": "student1", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_login_disabled_account(client, base, db):
    user = db.get(User, base.student1.id)
    user.account_status = AccountStatus.DISABLED.value
    db.commit()

    response = client.post(
        f"{API}/auth/login",
        json={"student_no": "student1", "password": "student123"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_DISABLED"


def test_missing_token_is_rejected(client):
    response = client.get(f"{API}/reservations/me")
    assert response.status_code == 401


def test_restricted_account_can_login(client, base, db):
    user = db.get(User, base.student1.id)
    user.account_status = AccountStatus.RESTRICTED.value
    db.commit()

    response = client.post(
        f"{API}/auth/login",
        json={"student_no": "student1", "password": "student123"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_student_cannot_call_admin_api_and_attempt_is_audited(
    client, base, db, student1
):
    response = client.get(f"{API}/reservations", headers=student1)
    assert response.status_code == 403

    fresh(db)
    logs = db.query(AuditLog).filter_by(action_type="UNAUTHORIZED_ATTEMPT").all()
    assert len(logs) == 1
    assert logs[0].operator_id == base.student1.id
