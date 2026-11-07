"""HTTP 层：学生自助注册（POST /auth/register）。"""

from sqlalchemy import select

from app.core.config import settings
from app.core.security import verify_password
from app.models.audit_log import AuditLog
from app.models.enums import AccountStatus, Role
from app.models.user import User


def _payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "name": "李四",
        "student_no": "S20260001",
        "password": "passw0rd123",
        "contact": "13800001111",
    }
    data.update(overrides)
    return data


def test_register_creates_student_and_returns_usable_token(api_client, db):
    response = api_client.post("/api/v1/auth/register", json=_payload())

    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    assert token

    user = db.scalar(select(User).where(User.student_no == "S20260001"))
    assert user is not None
    assert user.name == "李四"
    assert user.role == Role.STUDENT.value
    assert user.account_status == AccountStatus.NORMAL.value
    assert user.violation_count == 0
    assert user.contact == "13800001111"
    assert user.password_hash != "passw0rd123"
    assert verify_password("passw0rd123", user.password_hash)

    me = api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200, me.text
    assert me.json()["student_no"] == "S20260001"
    assert me.json()["role"] == Role.STUDENT.value

    audit = db.scalar(
        select(AuditLog).where(AuditLog.action_type == "REGISTER_SUCCESS")
    )
    assert audit is not None
    assert audit.operator_id == user.id


def test_register_rejects_duplicate_student_no(api_client, db):
    first = api_client.post("/api/v1/auth/register", json=_payload())
    assert first.status_code == 201, first.text

    second = api_client.post("/api/v1/auth/register", json=_payload())

    assert second.status_code == 409, second.text
    assert second.json()["code"] == "STUDENT_NO_TAKEN"
    count = len(db.scalars(select(User).where(User.student_no == "S20260001")).all())
    assert count == 1


def test_register_trims_identity_fields_and_blank_contact(api_client, db):
    response = api_client.post(
        "/api/v1/auth/register",
        json=_payload(student_no="  S20260002  ", contact="   "),
    )

    assert response.status_code == 201, response.text
    user = db.scalar(select(User).where(User.student_no == "S20260002"))
    assert user is not None
    assert user.contact is None


def test_register_rejects_invalid_payload(api_client, db):
    cases = [
        _payload(password="short"),
        _payload(password="        "),
        _payload(student_no="S1"),
        _payload(student_no="学号2026"),
        _payload(name="李"),
    ]
    for payload in cases:
        response = api_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422, (payload, response.text)
        assert response.json()["code"] == "VALIDATION_ERROR"

    assert db.scalar(select(User).where(User.student_no == "S20260001")) is None


def test_register_can_be_closed(api_client, db, monkeypatch):
    """A2：关闭自助注册后，任何学号都不能创建账号。"""
    monkeypatch.setattr(settings, "registration_enabled", False)

    response = api_client.post("/api/v1/auth/register", json=_payload())

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "REGISTRATION_CLOSED"
    assert db.scalar(select(User).where(User.student_no == "S20260001")) is None


def test_register_whitelist_blocks_unlisted_and_allows_listed(
    api_client, db, monkeypatch
):
    """A2：配置学籍白名单后，仅名单内学号可注册。"""
    monkeypatch.setattr(
        settings, "registration_whitelist", "S20260010, S20260011"
    )

    denied = api_client.post(
        "/api/v1/auth/register", json=_payload(student_no="S20260012")
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == "STUDENT_NO_NOT_ALLOWED"
    assert db.scalar(select(User).where(User.student_no == "S20260012")) is None

    allowed = api_client.post(
        "/api/v1/auth/register", json=_payload(student_no="S20260011")
    )
    assert allowed.status_code == 201, allowed.text
    assert db.scalar(select(User).where(User.student_no == "S20260011")) is not None


def test_register_defaults_contact_to_null(api_client, db):
    response = api_client.post(
        "/api/v1/auth/register",
        json={
            "name": "王五",
            "student_no": "S20260003",
            "password": "passw0rd123",
        },
    )

    assert response.status_code == 201, response.text
    user = db.scalar(select(User).where(User.student_no == "S20260003"))
    assert user is not None
    assert user.contact is None
