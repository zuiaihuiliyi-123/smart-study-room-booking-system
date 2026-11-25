"""白盒测试：手动/自动违约的状态门槛、幂等与列表筛选分支。"""

from datetime import date, datetime, time

import pytest
from sqlalchemy import select

from app.core.exceptions import BusinessError
from app.models.enums import AccountStatus, ReservationStatus, Role, ViolationType
from app.models.violation import ViolationRecord
from app.schemas.violation import ManualViolationCreate
from app.services import notification_service, violation_service
from app.utils import time_utils

NOW = datetime(2026, 11, 24, 10, 0)
TODAY = date(2026, 11, 24)


@pytest.fixture(autouse=True)
def _silence_notifications(monkeypatch):
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def _reservation(
    make_reservation,
    user,
    seat,
    *,
    status: str = ReservationStatus.IN_USE.value,
    start: time = time(10, 0),
    end: time = time(12, 0),
):
    return make_reservation(
        user.id,
        seat.id,
        status=status,
        reserve_date=TODAY,
        start_time=start,
        end_time=end,
    )


def _manual(db, reservation, *, type_: ViolationType = ViolationType.MANUAL, when=NOW):
    record = ViolationRecord(
        user_id=reservation.user_id,
        reservation_id=reservation.id,
        type=type_.value,
        reason="已有记录",
        created_at=when,
    )
    db.add(record)
    reservation.status = ReservationStatus.VIOLATED.value
    db.commit()
    db.refresh(record)
    return record


def test_register_manual_validates_reason_and_reservation(
    db, make_user
) -> None:
    admin = make_user(student_no="WBV000", role=Role.ADMIN.value)

    with pytest.raises(BusinessError) as exc:
        violation_service.register_manual(
            db, admin, ManualViolationCreate(reservation_id=1, reason="   ")
        )
    _assert_code(exc, "REASON_REQUIRED")

    with pytest.raises(BusinessError) as exc:
        violation_service.register_manual(
            db, admin, ManualViolationCreate(reservation_id=9999, reason="迟到")
        )
    _assert_code(exc, "RESERVATION_NOT_FOUND")


def test_register_manual_idempotent_and_conflicts(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    admin = make_user(student_no="WBV001", role=Role.ADMIN.value)
    user = make_user(student_no="WBV002")
    room = make_room()
    seat = make_seat(room.id)

    manual_reservation = _reservation(make_reservation, user, seat)
    existing = _manual(db, manual_reservation, type_=ViolationType.MANUAL)
    again = violation_service.register_manual(
        db,
        admin,
        ManualViolationCreate(reservation_id=manual_reservation.id, reason="重复登记"),
    )
    assert again.id == existing.id

    auto_reservation = _reservation(
        make_reservation, user, seat, start=time(13, 0), end=time(14, 0)
    )
    _manual(db, auto_reservation, type_=ViolationType.AUTO)
    with pytest.raises(BusinessError) as exc:
        violation_service.register_manual(
            db,
            admin,
            ManualViolationCreate(reservation_id=auto_reservation.id, reason="迟到"),
        )
    _assert_code(exc, "ST-026")

    pending = _reservation(
        make_reservation,
        user,
        seat,
        status=ReservationStatus.PENDING.value,
        start=time(14, 0),
        end=time(15, 0),
    )
    with pytest.raises(BusinessError) as exc:
        violation_service.register_manual(
            db,
            admin,
            ManualViolationCreate(reservation_id=pending.id, reason="提前违约"),
        )
    _assert_code(exc, "ST-026")
    assert exc.value.details["hint"]


def test_register_manual_rejects_admin_target(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    admin = make_user(student_no="WBV003", role=Role.ADMIN.value)
    target = make_user(
        student_no="WBV004",
        role=Role.ADMIN.value,
        name="被登记的管理员",
    )
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(make_reservation, target, seat)

    with pytest.raises(BusinessError) as exc:
        violation_service.register_manual(
            db,
            admin,
            ManualViolationCreate(reservation_id=reservation.id, reason="测试"),
        )
    _assert_code(exc, "VIOLATION_TARGET_NOT_STUDENT")


def test_register_manual_success_updates_status_and_count(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    admin = make_user(student_no="WBV005", role=Role.ADMIN.value)
    user = make_user(student_no="WBV006")
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(make_reservation, user, seat)

    record = violation_service.register_manual(
        db,
        admin,
        ManualViolationCreate(reservation_id=reservation.id, reason="长时间离座"),
    )

    assert record.type == ViolationType.MANUAL.value
    assert db.get(type(reservation), reservation.id).status == ReservationStatus.VIOLATED.value
    db.refresh(user)
    assert user.violation_count == 1
    # 阈值为 3，尚未进入受限
    assert user.account_status == AccountStatus.NORMAL.value


def test_apply_auto_violation_guards_and_success(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    monkeypatch.setattr(time_utils, "now", lambda: NOW)
    user = make_user(student_no="WBV101")
    admin = make_user(student_no="WBV102", role=Role.ADMIN.value)
    room = make_room()
    seat = make_seat(room.id)

    assert violation_service.apply_auto_violation(db, 9999, now=NOW) is None

    admin_reservation = _reservation(
        make_reservation, admin, seat, status=ReservationStatus.PENDING.value
    )
    assert violation_service.apply_auto_violation(db, admin_reservation.id, now=NOW) is None

    cancelled = _reservation(
        make_reservation, user, seat, status=ReservationStatus.CANCELLED.value
    )
    assert violation_service.apply_auto_violation(db, cancelled.id, now=NOW) is None

    not_due = _reservation(
        make_reservation,
        user,
        seat,
        status=ReservationStatus.PENDING.value,
        start=time(11, 30),
    )
    assert violation_service.apply_auto_violation(db, not_due.id, now=NOW) is None

    due = _reservation(
        make_reservation,
        user,
        seat,
        status=ReservationStatus.PENDING.value,
        start=time(9, 0),
    )
    first = violation_service.apply_auto_violation(db, due.id, now=NOW)
    assert first is not None
    assert first.type == ViolationType.AUTO.value
    second = violation_service.apply_auto_violation(db, due.id, now=NOW)
    assert second is not None and second.id == first.id
    assert len(db.scalars(select(ViolationRecord)).all()) == 1


def test_list_violations_filters_and_empty(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user(student_no="WBV201")
    other = make_user(student_no="WBV202")
    room = make_room()
    seat = make_seat(room.id)

    first = _reservation(make_reservation, user, seat, status=ReservationStatus.VIOLATED.value)
    second = _reservation(
        make_reservation,
        user,
        seat,
        status=ReservationStatus.VIOLATED.value,
        start=time(13, 0),
        end=time(14, 0),
    )
    third = _reservation(
        make_reservation,
        other,
        seat,
        status=ReservationStatus.VIOLATED.value,
        start=time(15, 0),
        end=time(16, 0),
    )
    _manual(db, first, type_=ViolationType.MANUAL, when=datetime(2026, 11, 20, 9, 0))
    _manual(db, second, type_=ViolationType.AUTO, when=datetime(2026, 11, 21, 9, 0))
    _manual(db, third, type_=ViolationType.MANUAL, when=datetime(2026, 11, 22, 9, 0))

    mine = violation_service.list_my_violations(db, user.id, 1, 10)
    assert mine.total == 2

    manual = violation_service.list_all_violations(
        db, 1, 10, violation_type=ViolationType.MANUAL.value
    )
    assert manual.total == 2

    ranged = violation_service.list_all_violations(
        db,
        1,
        10,
        created_from=date(2026, 11, 21),
        created_to=date(2026, 11, 22),
    )
    assert ranged.total == 2

    by_student = violation_service.list_all_violations(
        db, 1, 10, student_no="WBV202"
    )
    assert by_student.total == 1

    empty = violation_service.list_my_violations(db, 9999, 1, 10)
    assert empty.total == 0
    assert empty.items == []


def test_violation_page_pagination(db, make_user, make_room, make_seat, make_reservation) -> None:
    user = make_user(student_no="WBV301")
    room = make_room()
    seat = make_seat(room.id)
    for index in range(3):
        reservation = _reservation(
            make_reservation,
            user,
            seat,
            status=ReservationStatus.VIOLATED.value,
            start=time(9 + index, 0),
        )
        _manual(
            db,
            reservation,
            when=datetime(2026, 11, 20 + index, 9, 0),
        )

    page = violation_service.list_my_violations(db, user.id, 2, 1)
    assert page.total == 3
    assert len(page.items) == 1
    # 按 created_at 倒序：第二页是 11-21 的记录
    assert page.items[0].created_at == datetime(2026, 11, 21, 9, 0)
