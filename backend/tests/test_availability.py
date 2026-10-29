from __future__ import annotations

from app.models.enums import SeatStatus
from app.models.room import Room
from app.models.seat import Seat
from tests.conftest import API, DAY, booking_payload


def _create(client, headers, seat_id, key="availability-1"):
    response = client.post(
        f"{API}/reservations",
        headers=headers,
        json=booking_payload(seat_id, DAY, "14:00", "16:00", key),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _available(client, headers, base, start="14:00", end="16:00"):
    return client.get(
        f"{API}/reservations/available-seats",
        headers=headers,
        params={
            "room_id": base.room.id,
            "reserve_date": DAY.isoformat(),
            "start_time": start,
            "end_time": end,
        },
    )


def test_available_seats_exclude_occupied_and_maintenance(
    client, base, db, student1, student2
):
    _create(client, student1, base.seats[0].id)

    seat = db.get(Seat, base.seats[1].id)
    seat.status = SeatStatus.MAINTENANCE.value
    db.commit()

    response = _available(client, student2, base)
    assert response.status_code == 200, response.text
    seat_ids = {item["id"] for item in response.json()}
    assert base.seats[0].id not in seat_ids  # C3
    assert base.seats[1].id not in seat_ids  # C1
    assert base.seats[2].id in seat_ids


def test_adjacent_slot_makes_seat_available_again(
    client, base, student1, student2
):
    _create(client, student1, base.seats[0].id)

    response = _available(client, student2, base, start="16:00", end="18:00")
    assert response.status_code == 200, response.text
    assert base.seats[0].id in {item["id"] for item in response.json()}


def test_user_own_conflict_returns_empty_list(client, base, student1):
    _create(client, student1, base.seats[0].id)

    response = _available(client, student1, base, start="15:00", end="17:00")
    assert response.status_code == 200
    assert response.json() == []


def test_disabled_room_is_rejected(client, base, db, student1):
    room = db.get(Room, base.room.id)
    room.enabled = False
    db.commit()

    response = _available(client, student1, base)
    assert response.status_code == 409
    assert response.json()["code"] == "C2"


def test_outside_open_hours_is_rejected(client, base, student1):
    response = _available(client, student1, base, start="07:00", end="08:00")
    assert response.status_code == 409
    assert response.json()["code"] == "C2"


def test_unknown_room_returns_404(client, base, student1):
    response = client.get(
        f"{API}/reservations/available-seats",
        headers=student1,
        params={
            "room_id": 9999,
            "reserve_date": DAY.isoformat(),
            "start_time": "14:00",
            "end_time": "16:00",
        },
    )
    assert response.status_code == 404
