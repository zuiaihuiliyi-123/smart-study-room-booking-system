"""M7 站内消息与通知写入的单元测试。"""

import logging

import pytest
from sqlalchemy import select

from app.core.exceptions import BusinessError
from app.models.enums import MessageType
from app.models.message import StationMessage
from app.services import message_service, notification_service


def test_notify_persists_message_fields(db, make_student) -> None:
    student = make_student(student_no="S95001")

    notification_service.notify(
        db,
        user_id=student.id,
        message_type=MessageType.COMPLAINT,
        title="投诉状态更新",
        content="已受理",
        related_type="投诉",
        related_id=12,
    )
    db.commit()

    row = db.scalars(select(StationMessage)).one()
    assert row.type == MessageType.COMPLAINT.value
    assert row.title == "投诉状态更新"
    assert row.content == "已受理"
    assert (row.related_type, row.related_id) == ("投诉", 12)
    assert row.is_read is False


def test_notify_safe_swallows_session_failure(monkeypatch, caplog) -> None:
    """通知属非关键路径：独立会话不可用时只记日志，不能中断业务。"""

    class _BoomSession:
        def __enter__(self) -> None:
            raise RuntimeError("notification db down")

        def __exit__(self, *exc_info: object) -> bool:
            return False

    monkeypatch.setattr(notification_service, "SessionLocal", _BoomSession)

    with caplog.at_level(logging.ERROR):
        notification_service.notify_safe(
            user_id=1,
            message_type=MessageType.SYSTEM,
            title="系统通知",
            content="内容",
        )

    assert "站内通知写入失败" in caplog.text


def test_mark_read_is_idempotent_and_checks_owner(
    db, make_student, make_message, monkeypatch
) -> None:
    student = make_student(student_no="S95002")
    other = make_student(student_no="S95003")
    message = make_message(student.id, is_read=False)

    read = message_service.mark_read(db, student.id, message.id)
    assert read.is_read is True

    commit_calls: list[bool] = []
    monkeypatch.setattr(db, "commit", lambda: commit_calls.append(True))
    again = message_service.mark_read(db, student.id, message.id)
    assert again.is_read is True
    assert commit_calls == []  # 已读时不再写库

    with pytest.raises(BusinessError) as forbidden:
        message_service.mark_read(db, other.id, message.id)
    assert forbidden.value.code == "FORBIDDEN"
    assert forbidden.value.status_code == 403

    with pytest.raises(BusinessError) as missing:
        message_service.mark_read(db, student.id, 999999)
    assert missing.value.code == "MESSAGE_NOT_FOUND"
    assert missing.value.status_code == 404


def test_unread_count_and_type_filtered_pagination(db, make_student, make_message) -> None:
    owner = make_student(student_no="S95004")
    other = make_student(student_no="S95005")
    make_message(owner.id, is_read=False, type=MessageType.SYSTEM.value)
    make_message(owner.id, is_read=False, type=MessageType.COMPLAINT.value)
    make_message(owner.id, is_read=True, type=MessageType.SYSTEM.value)
    make_message(other.id, is_read=False)

    assert message_service.unread_count(db, owner.id) == 2

    page = message_service.list_my_messages(
        db, owner.id, 2, 1, message_type=MessageType.SYSTEM.value
    )
    assert page.total == 2
    assert len(page.items) == 1
    assert page.items[0].type == MessageType.SYSTEM.value
