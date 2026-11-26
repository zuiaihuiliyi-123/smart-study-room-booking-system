"""M5 评价单元测试：并发唯一约束、日期边界、schema 校验与分页隔离。"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus
from app.schemas.review import ReviewCreate
from app.services import review_service


def test_create_review_maps_unique_conflict_to_409(
    db, make_student, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    """并发窗口：两个请求同时通过“是否已评价”预检，只能由唯一约束兜底。"""
    room = make_room()
    seat = make_seat(room.id)
    student = make_student(student_no="S93001")
    reservation = make_reservation(
        student.id, seat.id, status=ReservationStatus.COMPLETED.value
    )
    review_service.create_review(
        db, student.id, ReviewCreate(reservation_id=reservation.id, score=5)
    )

    # 让预检返回“未评价”，模拟并发下两个请求都通过检查
    monkeypatch.setattr(db, "scalar", lambda *args, **kwargs: None)
    rollback_calls: list[bool] = []
    original_rollback = db.rollback
    monkeypatch.setattr(
        db, "rollback", lambda: rollback_calls.append(True) or original_rollback()
    )

    with pytest.raises(BusinessError) as conflict:
        review_service.create_review(
            db, student.id, ReviewCreate(reservation_id=reservation.id, score=4)
        )

    assert conflict.value.code == "REVIEW_ALREADY_EXISTS"
    assert conflict.value.status_code == 409
    assert rollback_calls == [True]


def test_review_schema_rejects_out_of_range_values() -> None:
    ReviewCreate(reservation_id=1, score=1)
    ReviewCreate(reservation_id=1, score=5, content="x" * 500)

    with pytest.raises(ValidationError):
        ReviewCreate(reservation_id=1, score=0)
    with pytest.raises(ValidationError):
        ReviewCreate(reservation_id=1, score=6)
    with pytest.raises(ValidationError):
        ReviewCreate(reservation_id=1, score=5, content="x" * 501)


def test_list_all_reviews_created_to_includes_whole_day(
    db, make_student, make_room, make_seat, make_reservation, make_review
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_student(student_no="S93010")
    first = make_reservation(
        student.id, seat.id, status=ReservationStatus.COMPLETED.value
    )
    second = make_reservation(
        student.id,
        seat.id,
        reserve_date=date(2099, 1, 2),
        status=ReservationStatus.COMPLETED.value,
    )
    early = make_review(
        student.id, first.id, created_at=datetime(2026, 11, 25, 23, 59, 59)
    )
    make_review(student.id, second.id, created_at=datetime(2026, 11, 26, 0, 0, 0))

    page = review_service.list_all_reviews(db, 1, 20, created_to=date(2026, 11, 25))

    assert [item.id for item in page.items] == [early.id]
    assert page.total == 1


def test_list_my_reviews_paginates_and_isolates_users(
    db, make_student, make_room, make_seat, make_reservation, make_review
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    owner = make_student(student_no="S93020")
    other = make_student(student_no="S93021")

    for index, reserve_date in enumerate(
        [date(2099, 1, 1), date(2099, 1, 2), date(2099, 1, 3)]
    ):
        reservation = make_reservation(
            owner.id,
            seat.id,
            reserve_date=reserve_date,
            status=ReservationStatus.COMPLETED.value,
        )
        make_review(owner.id, reservation.id, score=index + 3)

    other_reservation = make_reservation(
        other.id,
        seat.id,
        reserve_date=date(2099, 1, 4),
        status=ReservationStatus.COMPLETED.value,
    )
    make_review(other.id, other_reservation.id, score=5)

    first_page = review_service.list_my_reviews(db, owner.id, 1, 2)
    second_page = review_service.list_my_reviews(db, owner.id, 2, 2)
    other_page = review_service.list_my_reviews(db, other.id, 1, 20)

    assert first_page.total == 3
    assert len(first_page.items) == 2
    assert len(second_page.items) == 1
    assert other_page.total == 1
    assert {item.user_id for item in first_page.items} == {owner.id}
