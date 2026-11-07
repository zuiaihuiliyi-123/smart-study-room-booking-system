"""HTTP 层：看板用户违约次数 Top N 聚合（D1）。"""

from datetime import date, datetime

from app.core.security import hash_password
from app.models.enums import ReservationStatus, Role
from app.models.violation import ViolationRecord


def _login(api_client, student_no: str, password: str) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _add_violations(
    db,
    make_reservation,
    user,
    seat_id: int,
    days: list[int],
    start_id: int,
) -> None:
    for offset, day in enumerate(days):
        reservation = make_reservation(
            user.id,
            seat_id,
            reserve_date=date(2099, 1, start_id + offset),
            status=ReservationStatus.COMPLETED.value,
        )
        db.add(
            ViolationRecord(
                user_id=user.id,
                reservation_id=reservation.id,
                type="自动违约",
                reason="测试聚合",
                created_at=datetime(2026, 11, day, 10, 0),
            )
        )


def test_violation_top_aggregates_users_and_limits(
    api_client, db, make_user, make_room, make_seat, make_reservation
) -> None:
    make_user(
        student_no="A8501",
        name="看板管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    alice = make_user(
        student_no="S8501", name="甲同学", password_hash=hash_password("student123")
    )
    bob = make_user(
        student_no="S8502", name="乙同学", password_hash=hash_password("student123")
    )
    carol = make_user(
        student_no="S8503", name="丙同学", password_hash=hash_password("student123")
    )
    room = make_room()
    seat = make_seat(room.id)

    _add_violations(db, make_reservation, alice, seat.id, [1, 2, 3], 1)
    _add_violations(db, make_reservation, bob, seat.id, [2, 3], 10)
    _add_violations(db, make_reservation, carol, seat.id, [30], 20)  # 11-30，区间外
    db.commit()

    headers = _login(api_client, "A8501", "admin123")

    top = api_client.get(
        "/api/v1/dashboard/violation-top",
        params={
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "limit": 2,
        },
        headers=headers,
    )
    assert top.status_code == 200, top.text
    body = top.json()
    assert body["total_records"] == 5
    assert [item["user_id"] for item in body["items"]] == [alice.id, bob.id]
    assert [item["count"] for item in body["items"]] == [3, 2]
    assert body["items"][0]["name"] == "甲同学"
    assert body["items"][0]["student_no"] == "S8501"

    # 缩小日期区间：11-02 当天甲、乙各 1 条
    one_day = api_client.get(
        "/api/v1/dashboard/violation-top",
        params={
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "limit": 10,
        },
        headers=headers,
    )
    assert one_day.status_code == 200, one_day.text
    assert one_day.json()["total_records"] == 2
    assert [item["count"] for item in one_day.json()["items"]] == [1, 1]

    # limit 越界由 Query 校验拒绝
    invalid = api_client.get(
        "/api/v1/dashboard/violation-top",
        params={
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "limit": 0,
        },
        headers=headers,
    )
    assert invalid.status_code == 422, invalid.text


def test_violation_top_requires_admin(api_client, make_user) -> None:
    make_user(
        student_no="S8504",
        name="普通学生",
        password_hash=hash_password("student123"),
    )
    headers = _login(api_client, "S8504", "student123")

    response = api_client.get(
        "/api/v1/dashboard/violation-top",
        params={"start_date": "2026-11-01", "end_date": "2026-11-05"},
        headers=headers,
    )

    assert response.status_code == 403, response.text
