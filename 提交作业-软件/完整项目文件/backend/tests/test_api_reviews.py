"""HTTP 层：管理员评价列表的评分 / 提交日期筛选与权限。"""

from datetime import date, datetime

from app.core.security import hash_password
from app.models.enums import ReservationStatus, Role
from app.models.review import Review


def _login(api_client, student_no: str, password: str) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_review_list_filters_by_score_and_date(
    api_client, db, make_user, make_room, make_seat, make_reservation
) -> None:
    """评分与日期区间均为服务端筛选，且按提交时间倒序。"""
    make_user(
        student_no="A8101",
        name="评价管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    student = make_user(
        student_no="S8101", name="评价学生", password_hash=hash_password("student123")
    )
    room = make_room()
    seat = make_seat(room.id)
    first = make_reservation(
        student.id,
        seat.id,
        reserve_date=date(2099, 1, 1),
        status=ReservationStatus.COMPLETED.value,
    )
    second = make_reservation(
        student.id,
        seat.id,
        reserve_date=date(2099, 1, 2),
        status=ReservationStatus.COMPLETED.value,
    )
    db.add_all(
        [
            Review(
                user_id=student.id,
                reservation_id=first.id,
                score=5,
                content="环境很好",
                created_at=datetime(2026, 11, 1, 9, 30),
            ),
            Review(
                user_id=student.id,
                reservation_id=second.id,
                score=3,
                content=None,
                created_at=datetime(2026, 11, 5, 18, 0),
            ),
        ]
    )
    db.commit()

    headers = _login(api_client, "A8101", "admin123")

    all_page = api_client.get(
        "/api/v1/reviews", params={"page": 1, "page_size": 10}, headers=headers
    )
    assert all_page.status_code == 200, all_page.text
    body = all_page.json()
    assert body["total"] == 2
    assert [item["score"] for item in body["items"]] == [3, 5]

    # 分页：page_size=1 时 total 仍是 2
    paged = api_client.get(
        "/api/v1/reviews", params={"page": 1, "page_size": 1}, headers=headers
    )
    assert paged.status_code == 200, paged.text
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1

    # 评分筛选
    score_five = api_client.get(
        "/api/v1/reviews", params={"score": 5}, headers=headers
    )
    assert score_five.status_code == 200, score_five.text
    assert score_five.json()["total"] == 1
    assert score_five.json()["items"][0]["score"] == 5

    # 提交日期区间（含端点）
    by_date = api_client.get(
        "/api/v1/reviews",
        params={"created_from": "2026-11-04", "created_to": "2026-11-05"},
        headers=headers,
    )
    assert by_date.status_code == 200, by_date.text
    assert by_date.json()["total"] == 1
    assert by_date.json()["items"][0]["score"] == 3

    # 评分越界由 Query 校验拒绝
    invalid = api_client.get(
        "/api/v1/reviews", params={"score": 6}, headers=headers
    )
    assert invalid.status_code == 422, invalid.text


def test_student_cannot_list_all_reviews(api_client, make_user) -> None:
    """评价列表（管理员）仅业务管理员可访问。"""
    make_user(
        student_no="S8102",
        name="普通学生",
        password_hash=hash_password("student123"),
    )
    headers = _login(api_client, "S8102", "student123")

    response = api_client.get("/api/v1/reviews", headers=headers)

    assert response.status_code == 403, response.text
