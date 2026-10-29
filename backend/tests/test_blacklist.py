from __future__ import annotations

from datetime import timedelta

from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus
from app.models.user import User
from app.tasks.blacklist_expiry import release_expired_restrictions
from tests.conftest import API, DAY, NOW, booking_payload, fresh


def test_manual_blacklist_restricts_and_release_restores(
    client, base, db, student2, admin
):
    response = client.post(
        f"{API}/blacklist",
        headers=admin,
        json={
            "user_id": base.student2.id,
            "reason": "多次扰乱秩序",
            "expire_at": (NOW + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    entry = response.json()
    assert entry["mode"] == "手动"
    assert entry["released_at"] is None

    fresh(db)
    assert db.get(User, base.student2.id).account_status == AccountStatus.RESTRICTED.value

    # 受限用户仍可登录（ST-049），但不能创建预约（ST-047）
    forbidden = client.post(
        f"{API}/reservations",
        headers=student2,
        json=booking_payload(base.seats[0].id, DAY, "14:00", "16:00"),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "ST-047"

    # 手动限制到期后不会被自动解除（BR-010）
    assert release_expired_restrictions(NOW + timedelta(days=2)) == 0
    fresh(db)
    assert db.get(User, base.student2.id).account_status == AccountStatus.RESTRICTED.value
    assert db.get(BlacklistEntry, entry["id"]).released_at is None

    released = client.post(
        f"{API}/blacklist/{entry['id']}/release",
        headers=admin,
        json={"reason": "核实后提前解除"},
    )
    assert released.status_code == 200, released.text
    assert released.json()["released_at"] is not None

    fresh(db)
    assert db.get(User, base.student2.id).account_status == AccountStatus.NORMAL.value

    allowed = client.post(
        f"{API}/reservations",
        headers=student2,
        json=booking_payload(base.seats[0].id, DAY, "14:00", "16:00"),
    )
    assert allowed.status_code == 200, allowed.text


def test_duplicate_active_blacklist_entry_is_rejected(client, base, admin):
    payload = {"user_id": base.student2.id, "reason": "测试"}
    assert client.post(f"{API}/blacklist", headers=admin, json=payload).status_code == 201

    duplicate = client.post(f"{API}/blacklist", headers=admin, json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ST-041"


def test_release_requires_reason(client, base, admin):
    created = client.post(
        f"{API}/blacklist",
        headers=admin,
        json={"user_id": base.student2.id, "reason": "测试"},
    ).json()

    missing = client.post(
        f"{API}/blacklist/{created['id']}/release", headers=admin, json={}
    )
    assert missing.status_code == 422

    blank = client.post(
        f"{API}/blacklist/{created['id']}/release",
        headers=admin,
        json={"reason": "   "},
    )
    assert blank.status_code == 422
    assert blank.json()["code"] == "REASON_REQUIRED"


def test_blacklist_list_and_permissions(client, base, student2, admin):
    assert client.get(f"{API}/blacklist", headers=student2).status_code == 403

    created = client.post(
        f"{API}/blacklist",
        headers=admin,
        json={"user_id": base.student2.id, "reason": "测试"},
    )
    assert created.status_code == 201

    listing = client.get(f"{API}/blacklist", headers=admin)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["user_id"] == base.student2.id
