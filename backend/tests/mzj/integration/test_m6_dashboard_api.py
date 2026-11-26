"""集成：M6 看板接口口径、区间校验与缓存键。"""

from datetime import date, time

from app.core.cache import clear_dashboard_cache
from app.models.enums import AccountStatus, ReservationStatus, SeatStatus, ViolationType
from app.services import dashboard_service


def _seed_overview(
    make_room,
    make_seat,
    make_student,
    make_admin,
    make_reservation,
    make_violation,
    now,
):
    today = now.date()
    room1 = make_room()
    room2 = make_room()
    seat1 = make_seat(room1.id)
    seat2 = make_seat(room1.id)
    make_seat(room1.id, status=SeatStatus.MAINTENANCE.value)
    seat3 = make_seat(room2.id)

    student = make_student(student_no="S99501")
    make_student(student_no="S99502", account_status=AccountStatus.RESTRICTED.value)
    admin = make_admin()

    in_use = make_reservation(
        student.id,
        seat1.id,
        reserve_date=today,
        start_time=time(9, 0),
        end_time=time(11, 0),
        status=ReservationStatus.IN_USE.value,
    )
    make_reservation(
        student.id,
        seat3.id,
        reserve_date=today,
        start_time=time(9, 0),
        end_time=time(11, 0),
        status=ReservationStatus.IN_USE.value,
    )
    make_reservation(
        student.id,
        seat2.id,
        reserve_date=today,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.PENDING.value,
    )
    make_reservation(
        student.id,
        seat2.id,
        reserve_date=today,
        start_time=time(16, 0),
        end_time=time(18, 0),
        status=ReservationStatus.CANCELLED.value,
    )
    make_violation(student.id, in_use.id, created_at=now)
    make_violation(
        admin.id,
        in_use.id,
        type=ViolationType.MANUAL.value,
        created_at=now,
    )
    return room1


def test_dashboard_overview_matches_seed_and_room_scope(
    api_client,
    freeze_now,
    make_room,
    make_seat,
    make_student,
    make_admin,
    make_reservation,
    make_violation,
    auth_headers,
) -> None:
    room1 = _seed_overview(
        make_room,
        make_seat,
        make_student,
        make_admin,
        make_reservation,
        make_violation,
        freeze_now,
    )
    admin = make_admin()
    headers = auth_headers(admin)

    scoped = api_client.get(
        "/api/v1/dashboard/overview", headers=headers, params={"room_id": room1.id}
    )
    assert scoped.status_code == 200, scoped.text
    assert scoped.json() == {
        "seat_total": 2,
        "in_use": 1,
        "today_reservations": 2,
        "today_violations": 1,
        "restricted_accounts": 1,
    }

    overall = api_client.get("/api/v1/dashboard/overview", headers=headers)
    assert overall.status_code == 200
    assert overall.json() == {
        "seat_total": 3,
        "in_use": 2,
        "today_reservations": 3,
        "today_violations": 1,
        "restricted_accounts": 1,
    }


def test_dashboard_chart_endpoints_and_range_validation(
    api_client, make_admin, make_student, make_room, auth_headers
) -> None:
    admin = make_admin()
    make_room()
    headers = auth_headers(admin)

    seat_usage = api_client.get(
        "/api/v1/dashboard/seat-usage",
        headers=headers,
        params={"start_date": "2026-11-01", "end_date": "2026-11-07"},
    )
    assert seat_usage.status_code == 200
    by_slot = api_client.get(
        "/api/v1/dashboard/seat-usage",
        headers=headers,
        params={
            "start_date": "2026-11-01",
            "end_date": "2026-11-07",
            "group_by": "slot",
        },
    )
    assert by_slot.status_code == 200

    trend = api_client.get(
        "/api/v1/dashboard/trend",
        headers=headers,
        params={"start_date": "2026-11-20", "end_date": "2026-11-26"},
    )
    assert trend.status_code == 200
    assert len(trend.json()) == 7

    too_long = api_client.get(
        "/api/v1/dashboard/trend",
        headers=headers,
        params={"start_date": "2026-11-01", "end_date": "2026-12-03"},
    )
    assert too_long.status_code == 422
    assert too_long.json()["code"] == "INVALID_ARGUMENT"

    reversed_range = api_client.get(
        "/api/v1/dashboard/trend",
        headers=headers,
        params={"start_date": "2026-11-07", "end_date": "2026-11-01"},
    )
    assert reversed_range.status_code == 422

    bad_group = api_client.get(
        "/api/v1/dashboard/seat-usage",
        headers=headers,
        params={
            "start_date": "2026-11-01",
            "end_date": "2026-11-02",
            "group_by": "hour",
        },
    )
    assert bad_group.status_code == 422

    for limit in (0, 51):
        response = api_client.get(
            "/api/v1/dashboard/violation-top",
            headers=headers,
            params={
                "start_date": "2026-11-01",
                "end_date": "2026-11-02",
                "limit": limit,
            },
        )
        assert response.status_code == 422

    assert (
        api_client.get(
            "/api/v1/dashboard/overview", headers=auth_headers(make_student())
        ).status_code
        == 403
    )


def test_dashboard_overview_cache_is_scoped_by_room(
    api_client, monkeypatch, make_admin, make_room, auth_headers
) -> None:
    admin = make_admin()
    room = make_room()
    headers = auth_headers(admin)
    calls = {"n": 0}
    original = dashboard_service.get_overview

    def _counting(db, room_id=None):
        calls["n"] += 1
        return original(db, room_id)

    monkeypatch.setattr(dashboard_service, "get_overview", _counting)

    # 10 秒轮询窗口内重复请求命中缓存
    api_client.get("/api/v1/dashboard/overview", headers=headers)
    api_client.get("/api/v1/dashboard/overview", headers=headers)
    assert calls["n"] == 1

    # room_id 是缓存 key 的一部分，不能串用其他自习室的结果
    api_client.get(
        "/api/v1/dashboard/overview", headers=headers, params={"room_id": room.id}
    )
    assert calls["n"] == 2

    clear_dashboard_cache()
    api_client.get("/api/v1/dashboard/overview", headers=headers)
    assert calls["n"] == 3


def test_violation_top_limit_and_student_scope(
    api_client,
    freeze_now,
    make_student,
    make_admin,
    make_room,
    make_seat,
    make_reservation,
    make_violation,
    auth_headers,
) -> None:
    now = freeze_now
    today = now.date()
    room = make_room()
    seat = make_seat(room.id)
    first = make_student(student_no="S99510")
    second = make_student(student_no="S99511")
    third = make_student(student_no="S99512")
    admin = make_admin()

    def add_violation(user, hour: int) -> None:
        reservation = make_reservation(
            user.id,
            seat.id,
            reserve_date=today,
            start_time=time(hour, 0),
            end_time=time(hour + 1, 0),
        )
        make_violation(user.id, reservation.id, created_at=now)

    add_violation(first, 8)
    add_violation(first, 9)
    add_violation(second, 10)
    add_violation(second, 11)
    add_violation(third, 12)
    add_violation(admin, 13)

    params = {
        "start_date": today.isoformat(),
        "end_date": today.isoformat(),
        "limit": 1,
    }
    response = api_client.get(
        "/api/v1/dashboard/violation-top",
        headers=auth_headers(admin),
        params=params,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_records"] == 5
    assert len(body["items"]) == 1
    assert body["items"][0]["user_id"] == first.id
    assert body["items"][0]["count"] == 2

    assert (
        api_client.get(
            "/api/v1/dashboard/violation-top",
            headers=auth_headers(third),
            params=params,
        ).status_code
        == 403
    )
