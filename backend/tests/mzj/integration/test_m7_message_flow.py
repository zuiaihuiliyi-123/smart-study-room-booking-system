"""集成：M7 站内消息读取闭环、类型筛选与通知失败隔离。"""

from sqlalchemy import func, select

from app.models.enums import ComplaintStatus, MessageType
from app.models.message import StationMessage


def test_message_read_flow_and_boundaries(
    api_client,
    make_student,
    make_admin,
    make_complaint,
    auth_headers,
    captured_notifications,
) -> None:
    owner = make_student(student_no="S99601")
    other = make_student(student_no="S99602")
    admin = make_admin()
    complaint = make_complaint(owner.id)

    handled = api_client.patch(
        f"/api/v1/complaints/{complaint.id}",
        headers=auth_headers(admin),
        json={"status": "处理中", "handle_note": "已受理"},
    )
    assert handled.status_code == 200, handled.text
    assert len(captured_notifications) == 1

    owner_headers = auth_headers(owner)
    listing = api_client.get("/api/v1/messages/me", headers=owner_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    item = listing.json()["items"][0]
    assert item["type"] == MessageType.COMPLAINT.value
    assert item["is_read"] is False
    message_id = item["id"]

    assert (
        api_client.get("/api/v1/messages/unread-count", headers=owner_headers)
        .json()["count"]
        == 1
    )

    read = api_client.post(f"/api/v1/messages/{message_id}/read", headers=owner_headers)
    assert read.status_code == 200
    assert read.json()["is_read"] is True
    assert (
        api_client.get("/api/v1/messages/unread-count", headers=owner_headers)
        .json()["count"]
        == 0
    )

    # 重复标记已读是幂等的
    assert (
        api_client.post(
            f"/api/v1/messages/{message_id}/read", headers=owner_headers
        ).status_code
        == 200
    )

    forbidden = api_client.post(
        f"/api/v1/messages/{message_id}/read", headers=auth_headers(other)
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "FORBIDDEN"

    missing = api_client.post("/api/v1/messages/999999/read", headers=owner_headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "MESSAGE_NOT_FOUND"


def test_message_type_filter_pagination_and_isolation(
    api_client, make_student, make_message, auth_headers
) -> None:
    owner = make_student(student_no="S99610")
    other = make_student(student_no="S99611")
    for _ in range(3):
        make_message(owner.id, type=MessageType.SYSTEM.value)
    make_message(owner.id, type=MessageType.COMPLAINT.value)
    make_message(other.id)

    page = api_client.get(
        "/api/v1/messages/me",
        headers=auth_headers(owner),
        params={"type": MessageType.SYSTEM.value, "page": 2, "page_size": 2},
    )
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 1
    assert page.json()["items"][0]["type"] == MessageType.SYSTEM.value

    other_list = api_client.get(
        "/api/v1/messages/me", headers=auth_headers(other)
    )
    assert other_list.json()["total"] == 1


def test_notification_failure_does_not_rollback_complaint(
    api_client, db, make_student, make_admin, make_complaint, auth_headers
) -> None:
    """通知走独立会话；本组 autouse 夹具已让该会话不可用。"""
    owner = make_student(student_no="S99620")
    admin = make_admin()
    complaint = make_complaint(owner.id)

    response = api_client.patch(
        f"/api/v1/complaints/{complaint.id}",
        headers=auth_headers(admin),
        json={"status": "处理中", "handle_note": "已受理"},
    )

    assert response.status_code == 200, response.text
    db.refresh(complaint)
    assert complaint.status == ComplaintStatus.PROCESSING.value
    assert (
        db.scalar(select(func.count()).select_from(StationMessage)) == 0
    )
