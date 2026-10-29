from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, BlacklistMode, ReservationStatus, SeatStatus
from app.models.message import StationMessage
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.seat import Seat
from app.models.user import User
from app.models.violation import ViolationRecord
from app.tasks.auto_end_reservation import finish_expired_reservations
from app.tasks.auto_violation import scan_auto_violations
from app.tasks.blacklist_expiry import release_expired_restrictions
from tests.conftest import API, DAY, at, booking_payload, fresh


def _create(client, headers, seat_id, *, day=DAY, key="violation-key-1"):
    response = client.post(
        f"{API}/reservations",
        headers=headers,
        json=booking_payload(seat_id, day, "14:00", "16:00", key),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _check_in(client, headers, reservation_id):
    response = client.post(
        f"{API}/reservations/{reservation_id}/check-in", headers=headers
    )
    assert response.status_code == 200, response.text


def _trigger_three_violations(client, base, headers, freeze):
    ids = []
    for offset in range(3):
        day = DAY + timedelta(days=offset)
        created = _create(
            client,
            headers,
            base.seats[0].id,
            day=day,
            key=f"threshold-{offset}",
        )
        ids.append(created["id"])
        freeze(at(day, "14:15"))
        assert scan_auto_violations(at(day, "14:15")) == 1
    return ids


def test_auto_violation_is_idempotent(client, base, db, student1, freeze):
    created = _create(client, student1, base.seats[0].id)

    assert scan_auto_violations(at(DAY, "14:15")) == 1
    fresh(db)

    reservation = db.get(Reservation, created["id"])
    assert reservation.status == ReservationStatus.VIOLATED.value

    records = db.scalars(select(ViolationRecord)).all()
    assert len(records) == 1
    assert records[0].type == "自动违约"
    assert records[0].operator_id is None

    user = db.get(User, base.student1.id)
    assert user.violation_count == 1
    assert user.account_status == AccountStatus.NORMAL.value

    assert db.get(Seat, base.seats[0].id).status == SeatStatus.AVAILABLE.value
    assert db.scalars(select(ReservationSlot)).all() == []

    # ST-034：重复执行不新增记录、不重复累加
    assert scan_auto_violations(at(DAY, "14:20")) == 0
    fresh(db)
    assert db.scalar(select(func.count()).select_from(ViolationRecord)) == 1
    assert db.get(User, base.student1.id).violation_count == 1


def test_threshold_restricts_account_and_keeps_existing_booking(
    client, base, db, student1, freeze
):
    future = _create(
        client, student1, base.seats[1].id, day=DAY + timedelta(days=4), key="future-1"
    )
    _trigger_three_violations(client, base, student1, freeze)

    fresh(db)
    user = db.get(User, base.student1.id)
    assert user.violation_count == 3
    assert user.account_status == AccountStatus.RESTRICTED.value

    entry = db.scalar(
        select(BlacklistEntry).where(BlacklistEntry.user_id == user.id)
    )
    assert entry is not None
    assert entry.mode == BlacklistMode.AUTO.value
    assert entry.released_at is None
    assert entry.expire_at == at(DAY + timedelta(days=2), "14:15") + timedelta(days=7)

    # ST-049：受限前已有的未来预约保持原状
    assert db.get(Reservation, future["id"]).status == ReservationStatus.PENDING.value

    # ST-047：新预约被拒绝，并返回预计解除时间
    response = client.post(
        f"{API}/reservations",
        headers=student1,
        json=booking_payload(
            base.seats[2].id, DAY + timedelta(days=3), "14:00", "16:00"
        ),
    )
    assert response.status_code == 403
    error = response.json()
    assert error["code"] == "ST-047"
    assert error["details"]["params"]["limit_until"] == "2026-11-08T14:15:00"


def test_restricted_account_can_still_check_in_existing_booking(
    client, base, db, student1, freeze
):
    future_day = DAY + timedelta(days=4)
    created = _create(
        client, student1, base.seats[1].id, day=future_day, key="future-2"
    )
    _trigger_three_violations(client, base, student1, freeze)

    fresh(db)
    assert db.get(User, base.student1.id).account_status == AccountStatus.RESTRICTED.value
    assert db.get(Reservation, created["id"]).status == ReservationStatus.PENDING.value

    freeze(at(future_day, "14:00"))
    _check_in(client, student1, created["id"])


def test_auto_restriction_expires_after_seven_days(
    client, base, db, student1, freeze
):
    _trigger_three_violations(client, base, student1, freeze)
    restricted_at = at(DAY + timedelta(days=2), "14:15")
    later = restricted_at + timedelta(days=8)

    assert release_expired_restrictions(later) == 1
    freeze(later)
    fresh(db)

    user = db.get(User, base.student1.id)
    assert user.account_status == AccountStatus.NORMAL.value
    entry = db.scalar(select(BlacklistEntry).where(BlacklistEntry.user_id == user.id))
    assert entry.released_at is not None

    day = later.date() + timedelta(days=1)
    response = client.post(
        f"{API}/reservations",
        headers=student1,
        json=booking_payload(base.seats[3].id, day, "14:00", "16:00"),
    )
    assert response.status_code == 200, response.text


def test_auto_completion_does_not_create_violation(
    client, base, db, student1, freeze
):
    created = _create(client, student1, base.seats[0].id)
    freeze(at(DAY, "14:00"))
    _check_in(client, student1, created["id"])

    freeze(at(DAY, "16:01"))
    assert finish_expired_reservations(at(DAY, "16:01")) == 1

    fresh(db)
    reservation = db.get(Reservation, created["id"])
    assert reservation.status == ReservationStatus.COMPLETED.value
    assert reservation.auto_completed is True
    assert reservation.check_out_time == at(DAY, "16:00")
    assert db.scalars(select(ViolationRecord)).all() == []
    assert db.scalars(select(ReservationSlot)).all() == []


def test_manual_violation_requires_in_use_and_reason(
    client, base, db, student1, admin, freeze
):
    created = _create(client, student1, base.seats[0].id)

    pending = client.post(
        f"{API}/violations/manual",
        headers=admin,
        json={"reservation_id": created["id"], "reason": "未到场"},
    )
    assert pending.status_code == 409
    assert pending.json()["code"] == "ST-026"
    assert "强制取消" in pending.json()["details"]["hint"]

    freeze(at(DAY, "14:00"))
    _check_in(client, student1, created["id"])

    blank = client.post(
        f"{API}/violations/manual",
        headers=admin,
        json={"reservation_id": created["id"], "reason": "   "},
    )
    assert blank.status_code == 422
    assert blank.json()["code"] == "REASON_REQUIRED"

    response = client.post(
        f"{API}/violations/manual",
        headers=admin,
        json={"reservation_id": created["id"], "reason": "已签到但未正常签退"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "手动违约"
    assert body["operator_id"] == base.admin.id
    assert body["reason"] == "已签到但未正常签退"

    fresh(db)
    assert db.get(Reservation, created["id"]).status == ReservationStatus.VIOLATED.value
    assert db.get(User, base.student1.id).violation_count == 1

    audit = db.query(AuditLog).filter_by(action_type="MANUAL_VIOLATION").all()
    assert len(audit) == 1
    assert audit[0].reason == "已签到但未正常签退"


def test_manual_violation_repeat_is_idempotent(
    client, base, db, student1, admin, freeze
):
    created = _create(client, student1, base.seats[0].id)
    freeze(at(DAY, "14:00"))
    _check_in(client, student1, created["id"])

    payload = {"reservation_id": created["id"], "reason": "未正常签退"}
    first = client.post(f"{API}/violations/manual", headers=admin, json=payload)
    assert first.status_code == 200
    second = client.post(f"{API}/violations/manual", headers=admin, json=payload)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    fresh(db)
    assert db.scalar(select(func.count()).select_from(ViolationRecord)) == 1
    assert db.get(User, base.student1.id).violation_count == 1


def test_student_cannot_register_manual_violation(
    client, base, db, student1, student2, freeze
):
    created = _create(client, student1, base.seats[0].id)

    response = client.post(
        f"{API}/violations/manual",
        headers=student2,
        json={"reservation_id": created["id"], "reason": "越权"},
    )
    assert response.status_code == 403

    fresh(db)
    logs = (
        db.query(AuditLog)
        .filter_by(
            action_type="UNAUTHORIZED_ATTEMPT", operator_id=base.student2.id
        )
        .all()
    )
    assert len(logs) == 1


def test_violation_queries_and_permissions(
    client, base, db, student1, student2, admin, freeze
):
    _create(client, student1, base.seats[0].id)
    scan_auto_violations(at(DAY, "14:15"))

    mine = client.get(f"{API}/violations/me", headers=student1)
    assert mine.status_code == 200
    assert mine.json()["total"] == 1
    assert mine.json()["items"][0]["type"] == "自动违约"

    other = client.get(f"{API}/violations/me", headers=student2)
    assert other.json()["total"] == 0

    all_records = client.get(f"{API}/violations", headers=admin)
    assert all_records.status_code == 200
    assert all_records.json()["total"] == 1

    forbidden = client.get(f"{API}/violations", headers=student1)
    assert forbidden.status_code == 403


def test_station_message_is_written_on_booking(
    client, base, db, student1
):
    _create(client, student1, base.seats[0].id)
    fresh(db)
    messages = db.scalars(select(StationMessage)).all()
    assert len(messages) == 1
    assert messages[0].title == "预约成功"
    assert messages[0].related_type == "reservation"
