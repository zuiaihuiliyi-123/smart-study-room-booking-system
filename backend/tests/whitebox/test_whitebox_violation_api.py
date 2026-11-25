"""白盒测试：违约查询 HTTP 路由与筛选参数透传。"""

from datetime import datetime

from app.core.security import create_access_token
from app.models.enums import Role, ViolationType
from app.models.violation import ViolationRecord


def _headers(user) -> dict[str, str]:
    token = create_access_token(str(user.id), user.role, user.token_version or 0)
    return {"Authorization": f"Bearer {token}"}


def test_my_violations_endpoint(db, api_client, make_user) -> None:
    student = make_user(student_no="WBVA001")
    other = make_user(student_no="WBVA002")
    for user, type_ in ((student, ViolationType.MANUAL), (other, ViolationType.AUTO)):
        db.add(
            ViolationRecord(
                user_id=user.id,
                reservation_id=1000 + user.id,
                type=type_.value,
                reason="白盒 API",
                created_at=datetime(2026, 11, 20, 9, 0),
            )
        )
    db.commit()

    response = api_client.get("/api/v1/violations/me", headers=_headers(student))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == student.id


def test_admin_violations_endpoint_filters(db, api_client, make_user) -> None:
    admin = make_user(student_no="WBVA101", role=Role.ADMIN.value)
    alice = make_user(student_no="WBVA102")
    bob = make_user(student_no="WBVA103")
    rows = [
        (alice, ViolationType.MANUAL, datetime(2026, 11, 20, 9, 0)),
        (alice, ViolationType.AUTO, datetime(2026, 11, 21, 9, 0)),
        (bob, ViolationType.MANUAL, datetime(2026, 11, 22, 9, 0)),
    ]
    for index, (user, type_, created) in enumerate(rows):
        db.add(
            ViolationRecord(
                user_id=user.id,
                reservation_id=2000 + index,
                type=type_.value,
                reason="白盒 API",
                created_at=created,
            )
        )
    db.commit()

    response = api_client.get(
        "/api/v1/violations",
        params={
            "type": ViolationType.MANUAL.value,
            "created_from": "2026-11-21",
            "created_to": "2026-11-22",
            "student_no": "WBVA103",
        },
        headers=_headers(admin),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == bob.id
