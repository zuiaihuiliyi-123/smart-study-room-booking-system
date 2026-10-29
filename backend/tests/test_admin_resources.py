from __future__ import annotations

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.enums import ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.user import User
from app.models.violation import ViolationRecord
from tests.conftest import API, DAY, booking_payload, fresh


def test_room_list_and_create(client, base, admin, student1):
    listing = client.get(f"{API}/rooms", headers=student1)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    created = client.post(
        f"{API}/rooms",
        headers=admin,
        json={
            "name": "新建自习室",
            "location": "二号楼",
            "open_time": "09:00",
            "close_time": "20:00",
            "capacity": 5,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "新建自习室"

    duplicate = client.post(
        f"{API}/rooms",
        headers=admin,
        json={"name": "新建自习室", "location": "二号楼"},
    )
    assert duplicate.status_code == 409

    invalid = client.post(
        f"{API}/rooms",
        headers=admin,
        json={
            "name": "时间错误",
            "location": "二号楼",
            "open_time": "21:00",
            "close_time": "20:00",
        },
    )
    assert invalid.status_code == 422

    forbidden = client.post(
        f"{API}/rooms",
        headers=student1,
        json={"name": "学生创建", "location": "二号楼"},
    )
    assert forbidden.status_code == 403


def test_seat_create_and_list(client, base, admin, student1):
    created = client.post(
        f"{API}/seats",
        headers=admin,
        json={
            "room_id": base.room.id,
            "seat_no": "B-01",
            "seat_type": "靠窗位",
            "has_power": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "可用"  # FR-002

    duplicate = client.post(
        f"{API}/seats",
        headers=admin,
        json={"room_id": base.room.id, "seat_no": "B-01"},
    )
    assert duplicate.status_code == 409

    listing = client.get(f"{API}/rooms/{base.room.id}/seats", headers=student1)
    assert listing.status_code == 200
    assert any(item["seat_no"] == "B-01" for item in listing.json())

    missing_room = client.get(f"{API}/rooms/9999/seats", headers=student1)
    assert missing_room.status_code == 404


def test_seat_status_change_keeps_conflicting_reservation(
    client, base, db, admin, student1
):
    created = client.post(
        f"{API}/reservations",
        headers=student1,
        json=booking_payload(base.seats[0].id, DAY, "14:00", "16:00"),
    )
    assert created.status_code == 200

    missing_reason = client.patch(
        f"{API}/seats/{base.seats[0].id}/status",
        headers=admin,
        json={"status": "维修中"},
    )
    assert missing_reason.status_code == 422

    response = client.patch(
        f"{API}/seats/{base.seats[0].id}/status",
        headers=admin,
        json={"status": "维修中", "reason": "灯管损坏"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "维修中"

    fresh(db)
    # BR-019 默认口径：只提示冲突，不自动取消
    assert (
        db.get(Reservation, created.json()["id"]).status
        == ReservationStatus.PENDING.value
    )
    logs = db.query(AuditLog).filter_by(action_type="SEAT_STATUS_CHANGE").all()
    assert len(logs) == 1
    assert logs[0].reason == "灯管损坏"
    assert str(created.json()["id"]) in (logs[0].after_value or "")


def test_invalid_seat_status_transition(client, base, admin):
    assert (
        client.patch(
            f"{API}/seats/{base.seats[0].id}/status",
            headers=admin,
            json={"status": "停用", "reason": "测试"},
        ).status_code
        == 200
    )

    response = client.patch(
        f"{API}/seats/{base.seats[0].id}/status",
        headers=admin,
        json={"status": "维修中", "reason": "测试"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ST-001"


def test_student_cannot_change_seat_status(client, base, db, student1):
    response = client.patch(
        f"{API}/seats/{base.seats[0].id}/status",
        headers=student1,
        json={"status": "维修中", "reason": "越权"},
    )
    assert response.status_code == 403

    fresh(db)
    assert db.get(Seat, base.seats[0].id).status == SeatStatus.AVAILABLE.value
    assert (
        db.query(AuditLog)
        .filter_by(action_type="UNAUTHORIZED_ATTEMPT", operator_id=base.student1.id)
        .count()
        == 1
    )


def test_booking_after_seat_maintenance_returns_c1(client, base, admin, student1):
    assert (
        client.patch(
            f"{API}/seats/{base.seats[0].id}/status",
            headers=admin,
            json={"status": "维修中", "reason": "检修"},
        ).status_code
        == 200
    )

    response = client.post(
        f"{API}/reservations",
        headers=student1,
        json=booking_payload(base.seats[0].id, DAY, "14:00", "16:00"),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "C1_BR-017"


def test_admin_reservation_list_and_pagination(client, base, admin, student1):
    for index in range(2):
        assert (
            client.post(
                f"{API}/reservations",
                headers=student1,
                json=booking_payload(
                    base.seats[index].id,
                    DAY,
                    "08:00" if index == 0 else "10:00",
                    "10:00" if index == 0 else "12:00",
                    f"pagination-{index}",
                ),
            ).status_code
            == 200
        )

    response = client.get(
        f"{API}/reservations", headers=admin, params={"page": 1, "page_size": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1

    mine = client.get(f"{API}/reservations/me", headers=student1)
    assert mine.status_code == 200
    assert mine.json()["total"] == 2

    filtered = client.get(
        f"{API}/reservations", headers=admin, params={"status": "待使用"}
    )
    assert filtered.json()["total"] == 2

    invalid = client.get(
        f"{API}/reservations", headers=admin, params={"status": "不存在的状态"}
    )
    assert invalid.status_code == 422


def test_batch_cancel_requires_confirmation_and_does_not_create_violation(
    client, base, db, admin, student1, student2
):
    first = client.post(
        f"{API}/reservations",
        headers=student1,
        json=booking_payload(base.seats[0].id, DAY, "14:00", "16:00", "batch-0001"),
    ).json()
    second = client.post(
        f"{API}/reservations",
        headers=student2,
        json=booking_payload(base.seats[0].id, DAY, "16:00", "18:00", "batch-0002"),
    ).json()

    unconfirmed = client.patch(
        f"{API}/seats/{base.seats[0].id}/status",
        headers=admin,
        json={
            "status": "停用",
            "reason": "场地临时关闭",
            "cancel_conflicts": True,
            "confirm": False,
        },
    )
    assert unconfirmed.status_code == 422
    assert unconfirmed.json()["code"] == "BR-022"
    assert len(unconfirmed.json()["details"]["conflicts"]) == 2

    confirmed = client.patch(
        f"{API}/seats/{base.seats[0].id}/status",
        headers=admin,
        json={
            "status": "停用",
            "reason": "场地临时关闭",
            "cancel_conflicts": True,
            "confirm": True,
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "停用"

    fresh(db)
    for reservation_id in (first["id"], second["id"]):
        reservation = db.get(Reservation, reservation_id)
        assert reservation.status == ReservationStatus.CANCELLED.value
        assert reservation.cancelled_by_id == base.admin.id
        assert "场地关闭批量取消" in reservation.cancel_reason

    assert db.scalars(select(ViolationRecord)).all() == []
    assert db.get(User, base.student1.id).violation_count == 0
    assert db.query(AuditLog).filter_by(action_type="BATCH_CANCEL").count() == 1


def test_audit_log_query(client, base, db, admin, student1):
    created = client.post(
        f"{API}/reservations",
        headers=student1,
        json=booking_payload(base.seats[0].id, DAY, "14:00", "16:00", "audit-0001"),
    ).json()
    assert (
        client.post(
            f"{API}/reservations/{created['id']}/force-cancel",
            headers=admin,
            json={"reason": "审计测试"},
        ).status_code
        == 200
    )

    response = client.get(f"{API}/audit-logs", headers=admin)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["action_type"] == "RESERVATION_FORCE_CANCEL"

    assert client.get(f"{API}/audit-logs", headers=student1).status_code == 403
