"""集成：M5 投诉全链路（提交 → 受理 → 处理 → 消息 → 确认关闭）与权限。"""

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus, ComplaintTargetType, MessageType


def test_create_complaint_for_four_target_types(
    api_client,
    make_student,
    make_room,
    make_seat,
    make_reservation,
    auth_headers,
) -> None:
    student = make_student(student_no="S98001")
    other = make_student(student_no="S98002")
    room = make_room()
    seat = make_seat(room.id)
    reservation = make_reservation(student.id, seat.id)
    headers = auth_headers(student)

    targets = [
        (ComplaintTargetType.SEAT.value, seat.id),
        (ComplaintTargetType.ROOM.value, room.id),
        (ComplaintTargetType.RESERVATION.value, reservation.id),
        (ComplaintTargetType.USER.value, other.id),
    ]
    for target_type, target_id in targets:
        response = api_client.post(
            "/api/v1/complaints",
            headers=headers,
            json={
                "target_type": target_type,
                "target_id": target_id,
                "content": f"{target_type}有问题，请处理",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["status"] == ComplaintStatus.PENDING.value


def test_complaint_full_flow_creates_message_and_audit(
    api_client,
    db,
    make_student,
    make_admin,
    make_room,
    auth_headers,
    captured_notifications,
) -> None:
    student = make_student(student_no="S98010")
    admin = make_admin()
    room = make_room()
    student_headers = auth_headers(student)
    admin_headers = auth_headers(admin)

    created = api_client.post(
        "/api/v1/complaints",
        headers=student_headers,
        json={"target_type": "自习室", "target_id": room.id, "content": "空调太冷"},
    )
    assert created.status_code == 201, created.text
    complaint_id = created.json()["id"]

    accepted = api_client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers=admin_headers,
        json={"status": "处理中", "handle_note": "已受理"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == ComplaintStatus.PROCESSING.value
    assert accepted.json()["handler_id"] == admin.id

    resolved = api_client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers=admin_headers,
        json={"status": "已处理", "handle_note": "已联系物业维修"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == ComplaintStatus.RESOLVED.value
    assert len(captured_notifications) == 2
    assert {item["message_type"] for item in captured_notifications} == {
        MessageType.COMPLAINT
    }

    unread = api_client.get("/api/v1/messages/unread-count", headers=student_headers)
    assert unread.json()["count"] == 2
    messages = api_client.get("/api/v1/messages/me", headers=student_headers)
    assert messages.json()["total"] == 2
    assert {item["type"] for item in messages.json()["items"]} == {
        MessageType.COMPLAINT.value
    }

    closed = api_client.post(
        f"/api/v1/complaints/{complaint_id}/confirm", headers=student_headers
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == ComplaintStatus.CLOSED.value

    rows = db.scalars(
        select(AuditLog).where(
            AuditLog.action_type.in_(["COMPLAINT_HANDLE", "COMPLAINT_CONFIRM"])
        )
    ).all()
    actions = [row.action_type for row in rows]
    assert actions.count("COMPLAINT_HANDLE") == 2
    assert actions.count("COMPLAINT_CONFIRM") == 1
    stored = db.get(Complaint, complaint_id)
    assert stored is not None
    assert stored.status == ComplaintStatus.CLOSED.value


def test_complaint_permissions_and_closed_state_conflict(
    api_client, make_student, make_admin, make_complaint, auth_headers
) -> None:
    owner = make_student(student_no="S98020")
    other = make_student(student_no="S98021")
    admin = make_admin()
    owner_headers = auth_headers(owner)
    other_headers = auth_headers(other)
    admin_headers = auth_headers(admin)
    complaint = make_complaint(owner.id, status=ComplaintStatus.RESOLVED.value)

    # 学生不能查看全量投诉，也不能处理投诉
    assert api_client.get("/api/v1/complaints", headers=owner_headers).status_code == 403
    assert (
        api_client.patch(
            f"/api/v1/complaints/{complaint.id}",
            headers=owner_headers,
            json={"status": "处理中", "handle_note": "自助处理"},
        ).status_code
        == 403
    )
    # 他人不能确认关闭；管理员不能走“投诉人确认”接口
    forbidden = api_client.post(
        f"/api/v1/complaints/{complaint.id}/confirm", headers=other_headers
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "COMPLAINT_NOT_OWNER"
    assert (
        api_client.post(
            f"/api/v1/complaints/{complaint.id}/confirm", headers=admin_headers
        ).status_code
        == 403
    )

    assert (
        api_client.post(
            f"/api/v1/complaints/{complaint.id}/confirm", headers=owner_headers
        ).status_code
        == 200
    )
    conflict = api_client.patch(
        f"/api/v1/complaints/{complaint.id}",
        headers=admin_headers,
        json={"status": "处理中", "handle_note": "再次受理"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "COMPLAINT_STATE_INVALID"


def test_complaint_filters_and_pagination(
    api_client, make_student, make_admin, make_complaint, auth_headers
) -> None:
    first = make_student(student_no="S98030")
    second = make_student(student_no="S98031")
    admin = make_admin()
    headers = auth_headers(admin)

    make_complaint(first.id, target_type="自习室", content="空调太冷")
    make_complaint(
        first.id,
        target_type="座位",
        content="灯光太暗",
        status=ComplaintStatus.PROCESSING.value,
    )
    make_complaint(second.id, target_type="自习室", content="插座松动")

    pending = api_client.get(
        "/api/v1/complaints", headers=headers, params={"status": "待处理"}
    )
    assert pending.json()["total"] == 2

    rooms = api_client.get(
        "/api/v1/complaints", headers=headers, params={"target_type": "自习室"}
    )
    assert rooms.json()["total"] == 2

    by_user = api_client.get(
        "/api/v1/complaints", headers=headers, params={"user_id": second.id}
    )
    assert by_user.json()["total"] == 1

    by_keyword = api_client.get(
        "/api/v1/complaints", headers=headers, params={"keyword": "灯光"}
    )
    assert by_keyword.json()["total"] == 1

    page = api_client.get(
        "/api/v1/complaints",
        headers=headers,
        params={"page": 2, "page_size": 2},
    )
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 1


def test_admin_can_reject_pending_complaint(
    api_client, make_student, make_admin, make_complaint, auth_headers
) -> None:
    student = make_student(student_no="S98040")
    admin = make_admin()
    complaint = make_complaint(student.id)

    response = api_client.patch(
        f"/api/v1/complaints/{complaint.id}",
        headers=auth_headers(admin),
        json={"status": "已驳回", "handle_note": "不属于受理范围"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == ComplaintStatus.REJECTED.value

    mine = api_client.get("/api/v1/complaints/me", headers=auth_headers(student))
    assert mine.status_code == 200
    assert mine.json()["items"][0]["status"] == ComplaintStatus.REJECTED.value
