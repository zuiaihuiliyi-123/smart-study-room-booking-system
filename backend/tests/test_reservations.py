from __future__ import annotations

import threading
from datetime import datetime, time, timedelta

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, BlacklistMode, ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.user import User
from app.models.violation import ViolationRecord
from app.schemas.reservation import ReservationCreate
from app.services import reservation_service
from tests.conftest import API, DAY, NOW, at, booking_payload, fresh


def _create(client, headers, seat_id, *, day=DAY, start="14:00", end="16:00", key="idem-key-0001"):
    return client.post(
        f"{API}/reservations",
        headers=headers,
        json=booking_payload(seat_id, day, start, end, key),
    )


def test_create_success_keeps_seat_status(client, base, db, student1):
    response = _create(client, student1, base.seats[0].id)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["status"] == "待使用"
    assert body["seat_id"] == base.seats[0].id
    assert body["start_time"] == "14:00:00"
    assert body["end_time"] == "16:00:00"
    assert body["check_in_time"] is None
    assert body["auto_completed"] is False

    fresh(db)
    seat = db.get(Seat, base.seats[0].id)
    assert seat.status == SeatStatus.AVAILABLE.value  # 预约不改变座位资源状态


def test_adjacent_slots_are_allowed(client, base, student1, student2, auth):
    assert _create(client, student1, base.seats[0].id, key="adjacent-1").status_code == 200

    # TB-01：[14,16) 与 [16,18) 不冲突
    assert (
        _create(
            client, student2, base.seats[0].id, start="16:00", end="18:00", key="adjacent-2"
        ).status_code
        == 200
    )
    # TB-03：[13,14) 也不冲突
    assert (
        _create(
            client,
            auth("student3"),
            base.seats[0].id,
            start="13:00",
            end="14:00",
            key="adjacent-3",
        ).status_code
        == 200
    )


def test_seat_conflict_returns_c3(client, base, student1, student2):
    assert _create(client, student1, base.seats[0].id, key="c3-1").status_code == 200

    response = _create(
        client, student2, base.seats[0].id, start="15:00", end="17:00", key="c3-2"
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "C3_BR-006"
    assert error["details"]["condition"] == "C3"
    assert error["details"]["rule"] == "BR-006"
    assert len(error["details"]["params"]["conflicts"]) == 1


def test_user_overlap_returns_c4(client, base, student1):
    assert _create(client, student1, base.seats[0].id, key="c4-1").status_code == 200

    response = _create(
        client, student1, base.seats[1].id, start="15:00", end="17:00", key="c4-2"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "C4_BR-005"


def test_maintenance_seat_returns_c1(client, base, db, student1):
    seat = db.get(Seat, base.seats[0].id)
    seat.status = SeatStatus.MAINTENANCE.value
    db.commit()

    response = _create(client, student1, seat.id, key="c1-1")
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "C1_BR-017"
    assert error["details"]["params"]["seat_status"] == "维修中"


def test_outside_open_hours_returns_c2(client, base, student1):
    response = _create(
        client, student1, base.seats[0].id, start="07:00", end="08:00", key="c2-1"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "C2"


def test_time_rules_return_specific_codes(client, base, student1):
    response = _create(
        client, student1, base.seats[0].id, start="14:10", end="16:00", key="rule-1"
    )
    assert response.status_code == 422
    assert response.json()["code"] == "C6_BR-001"

    response = _create(
        client, student1, base.seats[0].id, start="08:00", end="13:00", key="rule-2"
    )
    assert response.status_code == 422
    assert response.json()["code"] == "C6_BR-003"

    response = _create(
        client, student1, base.seats[0].id, start="22:00", end="01:00", key="rule-3"
    )
    assert response.status_code == 422
    assert response.json()["code"] == "C6_BR-020"

    response = _create(
        client,
        student1,
        base.seats[0].id,
        day=DAY + timedelta(days=8),
        key="rule-4",
    )
    assert response.status_code == 422
    assert response.json()["code"] == "C6_BR-002"

    response = _create(
        client,
        student1,
        base.seats[0].id,
        day=NOW.date(),
        start="09:00",
        end="10:00",
        key="rule-5",
    )
    assert response.status_code == 422
    assert response.json()["code"] == "C6_BR-002"


def test_exact_four_hours_is_allowed(client, base, student1):
    response = _create(
        client, student1, base.seats[0].id, start="08:00", end="12:00", key="four-hours"
    )
    assert response.status_code == 200, response.text


def test_daily_limit_returns_c6(client, base, student1):
    assert (
        _create(client, student1, base.seats[0].id, start="08:00", end="10:00", key="daily-1").status_code
        == 200
    )
    assert (
        _create(client, student1, base.seats[0].id, start="10:00", end="12:00", key="daily-2").status_code
        == 200
    )

    response = _create(
        client, student1, base.seats[0].id, start="12:00", end="14:00", key="daily-3"
    )
    assert response.status_code == 422
    error = response.json()
    assert error["code"] == "C6_BR-004"
    assert error["details"]["params"]["max_per_day"] == 2


def test_restricted_account_returns_st047(client, base, db, student1):
    user = db.get(User, base.student1.id)
    user.account_status = AccountStatus.RESTRICTED.value
    db.add(
        BlacklistEntry(
            user_id=user.id,
            reason="测试限制",
            mode=BlacklistMode.AUTO.value,
            start_at=NOW,
            expire_at=NOW + timedelta(days=3),
        )
    )
    db.commit()

    response = _create(client, student1, base.seats[0].id, key="restricted-1")
    assert response.status_code == 403
    error = response.json()
    assert error["code"] == "ST-047"
    assert error["details"]["params"]["account_status"] == "受限"
    assert error["details"]["params"]["limit_until"] == "2026-11-01T10:00:00"


def test_idempotency_returns_same_reservation(client, base, db, student1):
    first = _create(client, student1, base.seats[0].id, key="idem-0001")
    assert first.status_code == 200
    first_id = first.json()["id"]

    for _ in range(2):
        replay = _create(client, student1, base.seats[0].id, key="idem-0001")
        assert replay.status_code == 200
        assert replay.json()["id"] == first_id

    fresh(db)
    assert db.scalar(select(func.count()).select_from(Reservation)) == 1


def test_idempotency_key_reuse_for_other_payload_is_rejected(
    client, base, student1
):
    assert _create(client, student1, base.seats[0].id, key="idem-0002").status_code == 200

    response = _create(client, student1, base.seats[1].id, key="idem-0002")
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_replay_after_cancel_returns_cancelled_reservation(
    client, base, student1, freeze
):
    first = _create(client, student1, base.seats[0].id, key="idem-0003").json()

    freeze(at(DAY, "13:00"))
    assert (
        client.post(
            f"{API}/reservations/{first['id']}/cancel",
            headers=student1,
            json={"reason": "临时有事"},
        ).status_code
        == 200
    )

    replay = _create(client, student1, base.seats[0].id, key="idem-0003")
    assert replay.status_code == 200
    assert replay.json()["id"] == first["id"]
    assert replay.json()["status"] == "已取消"


def test_concurrent_requests_create_exactly_one(base, db):
    """VS-01 / NFR-011：并发争用同一座位同一时段，恰好一条成功。"""
    user_ids = [user.id for user in base.students[:4]]
    seat_id = base.seats[0].id
    barrier = threading.Barrier(len(user_ids))
    results: list[str] = []
    lock = threading.Lock()

    def attempt(user_id: int) -> None:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                payload = ReservationCreate(
                    seat_id=seat_id,
                    reserve_date=DAY,
                    start_time=time(14, 0),
                    end_time=time(16, 0),
                    idempotency_key=f"concurrent-{user_id}",
                )
                reservation = reservation_service.create_reservation(
                    session, user, payload
                )
                result = f"ok:{reservation.id}"
            except BusinessError as exc:
                result = f"error:{exc.code}"
            except Exception as exc:  # pragma: no cover - 便于定位并发问题
                result = f"exception:{type(exc).__name__}:{exc}"
            with lock:
                results.append(result)

    threads = [
        threading.Thread(target=attempt, args=(user_id,)) for user_id in user_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    successes = [item for item in results if item.startswith("ok:")]
    assert len(successes) == 1, results
    assert all(
        item.startswith("ok:") or item in ("error:C3_BR-006", "error:ST-035")
        for item in results
    ), results

    fresh(db)
    assert db.scalar(select(func.count()).select_from(Reservation)) == 1


def test_user_cancel_boundary(client, base, db, student1, freeze):
    created = _create(client, student1, base.seats[0].id, key="cancel-1").json()

    freeze(datetime(2026, 10, 30, 13, 29, 59))
    response = client.post(
        f"{API}/reservations/{created['id']}/cancel",
        headers=student1,
        json={"reason": "临时有事"},
    )
    assert response.status_code == 200, response.text

    fresh(db)
    reservation = db.get(Reservation, created["id"])
    assert reservation.status == ReservationStatus.CANCELLED.value
    assert reservation.cancel_reason == "临时有事"


def test_user_cancel_at_deadline_is_rejected(client, base, student1, freeze):
    created = _create(client, student1, base.seats[0].id, key="cancel-2").json()

    freeze(datetime(2026, 10, 30, 13, 30, 0))
    response = client.post(
        f"{API}/reservations/{created['id']}/cancel",
        headers=student1,
        json={},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "ST-029"


def test_cannot_cancel_after_check_in(client, base, student1, freeze):
    created = _create(client, student1, base.seats[0].id, key="cancel-3").json()
    freeze(at(DAY, "14:00"))
    assert (
        client.post(
            f"{API}/reservations/{created['id']}/check-in", headers=student1
        ).status_code
        == 200
    )

    response = client.post(
        f"{API}/reservations/{created['id']}/cancel", headers=student1, json={}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ST-031"


def test_admin_force_cancel_requires_reason(client, base, student1, admin):
    created = _create(client, student1, base.seats[0].id, key="force-1").json()

    missing = client.post(
        f"{API}/reservations/{created['id']}/force-cancel",
        headers=admin,
        json={},
    )
    assert missing.status_code == 422

    blank = client.post(
        f"{API}/reservations/{created['id']}/force-cancel",
        headers=admin,
        json={"reason": "   "},
    )
    assert blank.status_code == 422
    assert blank.json()["code"] == "REASON_REQUIRED"


def test_admin_force_cancel_does_not_create_violation(
    client, base, db, student1, admin
):
    created = _create(client, student1, base.seats[0].id, key="force-2").json()

    response = client.post(
        f"{API}/reservations/{created['id']}/force-cancel",
        headers=admin,
        json={"reason": "场地临时征用"},
    )
    assert response.status_code == 200, response.text

    fresh(db)
    reservation = db.get(Reservation, created["id"])
    assert reservation.status == ReservationStatus.CANCELLED.value
    assert reservation.cancel_reason == "场地临时征用"
    assert reservation.cancelled_by_id == base.admin.id
    assert db.scalar(select(func.count()).select_from(ViolationRecord)) == 0
    assert db.get(User, base.student1.id).violation_count == 0

    logs = db.query(AuditLog).filter_by(action_type="RESERVATION_FORCE_CANCEL").all()
    assert len(logs) == 1


def test_force_cancel_in_use_is_rejected(client, base, student1, admin, freeze):
    created = _create(client, student1, base.seats[0].id, key="force-3").json()
    freeze(at(DAY, "14:00"))
    assert (
        client.post(
            f"{API}/reservations/{created['id']}/check-in", headers=student1
        ).status_code
        == 200
    )

    response = client.post(
        f"{API}/reservations/{created['id']}/force-cancel",
        headers=admin,
        json={"reason": "测试"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ST-022"
    assert "手动违约" in response.json()["details"]["hint"]


def test_check_in_window_and_duplicate(client, base, db, student1, freeze):
    created = _create(client, student1, base.seats[0].id, key="checkin-1").json()

    freeze(at(DAY, "13:44"))
    early = client.post(
        f"{API}/reservations/{created['id']}/check-in", headers=student1
    )
    assert early.status_code == 422
    assert early.json()["code"] == "ST-027"

    # TB-08：13:45 整可签到（左闭）
    freeze(at(DAY, "13:45"))
    ok = client.post(
        f"{API}/reservations/{created['id']}/check-in", headers=student1
    )
    assert ok.status_code == 200, ok.text

    fresh(db)
    reservation = db.get(Reservation, created["id"])
    assert reservation.status == ReservationStatus.IN_USE.value
    assert reservation.check_in_time == at(DAY, "13:45")

    freeze(at(DAY, "13:50"))
    duplicate = client.post(
        f"{API}/reservations/{created['id']}/check-in", headers=student1
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ST-030"

    fresh(db)
    assert db.get(Reservation, created["id"]).check_in_time == at(DAY, "13:45")


def test_check_in_after_deadline_and_other_user(
    client, base, student1, student2, freeze
):
    created = _create(client, student1, base.seats[0].id, key="checkin-2").json()

    freeze(at(DAY, "14:00"))
    other = client.post(
        f"{API}/reservations/{created['id']}/check-in", headers=student2
    )
    assert other.status_code == 403

    freeze(at(DAY, "14:15"))
    late = client.post(
        f"{API}/reservations/{created['id']}/check-in", headers=student1
    )
    assert late.status_code == 422
    assert late.json()["code"] == "ST-027"


def test_check_out_flow(client, base, db, student1, freeze):
    created = _create(client, student1, base.seats[0].id, key="checkout-1").json()

    freeze(at(DAY, "14:00"))
    early = client.post(
        f"{API}/reservations/{created['id']}/check-out", headers=student1
    )
    assert early.status_code == 409
    assert early.json()["code"] == "ST-031"

    assert (
        client.post(
            f"{API}/reservations/{created['id']}/check-in", headers=student1
        ).status_code
        == 200
    )

    freeze(at(DAY, "15:30"))
    done = client.post(
        f"{API}/reservations/{created['id']}/check-out", headers=student1
    )
    assert done.status_code == 200, done.text

    fresh(db)
    reservation = db.get(Reservation, created["id"])
    assert reservation.status == ReservationStatus.COMPLETED.value
    assert reservation.check_out_time == at(DAY, "15:30")
    assert reservation.auto_completed is False

    again = client.post(
        f"{API}/reservations/{created['id']}/check-out", headers=student1
    )
    assert again.status_code == 409


def test_admin_cannot_create_reservation_and_attempt_is_audited(
    client, base, db, admin
):
    response = _create(client, admin, base.seats[0].id, key="admin-create")
    assert response.status_code == 403

    fresh(db)
    logs = db.query(AuditLog).filter_by(action_type="UNAUTHORIZED_ATTEMPT").all()
    assert len(logs) == 1
    assert logs[0].operator_id == base.admin.id
