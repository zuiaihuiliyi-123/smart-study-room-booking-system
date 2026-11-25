"""白盒测试：投诉列表筛选与用户管理（筛选 / 账户状态变更）分支。"""

from datetime import date, datetime, timedelta

import pytest

from app.core.exceptions import BusinessError
from app.models.blacklist import BlacklistEntry
from app.models.enums import (
    AccountStatus,
    BlacklistMode,
    ComplaintStatus,
    ComplaintTargetType,
    Role,
)
from app.schemas.complaint import ComplaintCreate
from app.schemas.user import AccountStatusUpdate
from app.services import complaint_service, user_service

NOW = datetime(2026, 11, 24, 10, 0)


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def test_complaint_create_validations(db, make_user, make_room, make_seat) -> None:
    user = make_user(student_no="WBU001")
    room = make_room()
    seat = make_seat(room.id)

    with pytest.raises(BusinessError) as exc:
        complaint_service.create_complaint(
            db,
            user.id,
            ComplaintCreate.model_construct(
                target_type="不存在的类型", target_id=seat.id, content="内容"
            ),
        )
    _assert_code(exc, "COMPLAINT_TARGET_TYPE_INVALID")

    with pytest.raises(BusinessError) as exc:
        complaint_service.create_complaint(
            db,
            user.id,
            ComplaintCreate.model_construct(
                target_type=ComplaintTargetType.SEAT.value,
                target_id=seat.id,
                content="   ",
            ),
        )
    _assert_code(exc, "COMPLAINT_CONTENT_REQUIRED")

    created = complaint_service.create_complaint(
        db,
        user.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.SEAT,
            target_id=seat.id,
            content="座位有噪音",
        ),
    )
    assert created.status == ComplaintStatus.PENDING.value


def test_complaint_lists_and_filters(db, make_user, make_room, make_seat) -> None:
    alice = make_user(student_no="WBU101")
    bob = make_user(student_no="WBU102")
    room = make_room()
    seat = make_seat(room.id)

    first = complaint_service.create_complaint(
        db,
        alice.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.SEAT,
            target_id=seat.id,
            content="座位有噪音",
        ),
    )
    second = complaint_service.create_complaint(
        db,
        alice.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM,
            target_id=room.id,
            content="空调太冷",
        ),
    )
    third = complaint_service.create_complaint(
        db,
        bob.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM,
            target_id=room.id,
            content="灯光太暗",
        ),
    )
    first.created_at = datetime(2026, 11, 20, 9, 0)
    second.created_at = datetime(2026, 11, 21, 9, 0)
    third.created_at = datetime(2026, 11, 22, 9, 0)
    second.status = ComplaintStatus.PROCESSING.value
    db.commit()

    mine = complaint_service.list_my_complaints(db, alice.id, 1, 10)
    assert mine.total == 2

    empty = complaint_service.list_my_complaints(db, 9999, 1, 10)
    assert empty.total == 0 and empty.items == []

    processing = complaint_service.list_all_complaints(
        db, 1, 10, status=ComplaintStatus.PROCESSING.value
    )
    assert processing.total == 1

    by_type = complaint_service.list_all_complaints(
        db, 1, 10, target_type=ComplaintTargetType.ROOM.value
    )
    assert by_type.total == 2

    by_keyword = complaint_service.list_all_complaints(db, 1, 10, keyword="空调")
    assert by_keyword.total == 1

    by_user = complaint_service.list_all_complaints(db, 1, 10, user_id=bob.id)
    assert by_user.total == 1

    by_date = complaint_service.list_all_complaints(
        db, 1, 10, created_from=date(2026, 11, 21), created_to=date(2026, 11, 21)
    )
    assert by_date.total == 1


def test_list_users_filters(db, make_user) -> None:
    alice = make_user(
        student_no="WBU201", name="白盒甲", violation_count=3
    )
    bob = make_user(
        student_no="WBU202",
        name="白盒乙",
        role=Role.ADMIN.value,
        account_status=AccountStatus.DISABLED.value,
    )

    by_keyword = user_service.list_users(db, 1, 10, keyword="白盒")
    assert by_keyword.total == 2

    by_student_no = user_service.list_users(db, 1, 10, keyword="WBU202")
    assert by_student_no.total == 1
    assert by_student_no.items[0].student_no == "WBU202"
    # 管理员列表中的联系方式必须脱敏
    assert "13800001234" not in (by_student_no.items[0].contact or "")

    by_role = user_service.list_users(db, 1, 10, role=Role.ADMIN.value)
    assert {item.id for item in by_role.items} == {bob.id}

    by_status = user_service.list_users(
        db, 1, 10, account_status=AccountStatus.DISABLED.value
    )
    assert {item.id for item in by_status.items} == {bob.id}

    by_violation = user_service.list_users(db, 1, 10, violation_min=3)
    assert {item.id for item in by_violation.items} == {alice.id}

    empty = user_service.list_users(db, 1, 10, keyword="不存在")
    assert empty.total == 0 and empty.items == []


def test_set_account_status_guards(db, make_user) -> None:
    admin = make_user(student_no="WBU301", role=Role.ADMIN.value)
    student = make_user(student_no="WBU302")
    another_admin = make_user(student_no="WBU303", role=Role.ADMIN.value)

    with pytest.raises(BusinessError) as exc:
        user_service.set_account_status(
            db, 9999, AccountStatusUpdate(account_status="停用", reason="测试"), admin.id
        )
    _assert_code(exc, "USER_NOT_FOUND")

    with pytest.raises(BusinessError) as exc:
        user_service.set_account_status(
            db,
            admin.id,
            AccountStatusUpdate(account_status="停用", reason="测试"),
            admin.id,
        )
    _assert_code(exc, "SELF_OPERATION_FORBIDDEN")

    with pytest.raises(BusinessError) as exc:
        user_service.set_account_status(
            db,
            another_admin.id,
            AccountStatusUpdate(account_status="停用", reason="测试"),
            admin.id,
        )
    _assert_code(exc, "TARGET_ROLE_NOT_ALLOWED")

    student.account_status = AccountStatus.RESTRICTED.value
    db.commit()
    with pytest.raises(BusinessError) as exc:
        user_service.set_account_status(
            db,
            student.id,
            AccountStatusUpdate(account_status="停用", reason="测试"),
            admin.id,
        )
    _assert_code(exc, "ACCOUNT_STILL_RESTRICTED")


def test_set_account_status_no_change_and_restore_with_active_entry(
    db, make_user
) -> None:
    admin = make_user(student_no="WBU401", role=Role.ADMIN.value)
    student = make_user(student_no="WBU402")

    with pytest.raises(BusinessError) as exc:
        user_service.set_account_status(
            db,
            student.id,
            AccountStatusUpdate(account_status="正常", reason="测试"),
            admin.id,
        )
    _assert_code(exc, "ACCOUNT_STATUS_NO_CHANGE")

    student.account_status = AccountStatus.DISABLED.value
    entry = BlacklistEntry(
        user_id=student.id,
        reason="仍有有效限制",
        mode=BlacklistMode.MANUAL.value,
        start_at=NOW - timedelta(days=1),
        active_user_id=student.id,
    )
    db.add(entry)
    db.commit()

    with pytest.raises(BusinessError) as exc:
        user_service.set_account_status(
            db,
            student.id,
            AccountStatusUpdate(account_status="正常", reason="恢复"),
            admin.id,
        )
    _assert_code(exc, "ACCOUNT_STILL_RESTRICTED")
    assert exc.value.details["blacklist_entry_id"] == entry.id


def test_set_account_status_success(db, make_user) -> None:
    admin = make_user(student_no="WBU501", role=Role.ADMIN.value)
    student = make_user(student_no="WBU502")

    updated = user_service.set_account_status(
        db,
        student.id,
        AccountStatusUpdate(account_status="停用", reason="违规使用他人物品"),
        admin.id,
    )

    assert updated.account_status == AccountStatus.DISABLED.value
