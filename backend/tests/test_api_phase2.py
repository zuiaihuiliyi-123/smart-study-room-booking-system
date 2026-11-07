"""第二阶段新增能力的回归：消息分页/类型筛选、投诉提交人与关键词筛选、停用账户 403。

这些用例覆盖本轮新增的后端查询参数与鉴权口径，避免后续改动回退。
"""

from __future__ import annotations

from datetime import date

from app.core.security import create_access_token, hash_password
from app.models.complaint import Complaint
from app.models.enums import AccountStatus, Role
from app.models.message import StationMessage


def _login(api_client, student_no: str, password: str) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------------------------------------------------------------- 消息


def test_messages_type_filter_and_pagination(api_client, db, make_user) -> None:
    """消息列表按类型筛选，且分页由服务端完成（不再全量拉取）。"""
    user = make_user(
        student_no="S9001", name="消息用户", password_hash=hash_password("student123")
    )
    db.add_all(
        [
            StationMessage(user_id=user.id, type="预约通知", title="t1", content="预约成功"),
            StationMessage(user_id=user.id, type="违约通知", title="t2", content="违约 1"),
            StationMessage(user_id=user.id, type="违约通知", title="t3", content="违约 2"),
        ]
    )
    db.commit()
    headers = _login(api_client, "S9001", "student123")

    # 全部：3 条
    all_page = api_client.get(
        "/api/v1/messages/me",
        params={"page": 1, "page_size": 10},
        headers=headers,
    )
    assert all_page.status_code == 200, all_page.text
    assert all_page.json()["total"] == 3

    # 按类型筛选：2 条，且返回项类型一致
    filtered = api_client.get(
        "/api/v1/messages/me",
        params={"type": "违约通知", "page": 1, "page_size": 10},
        headers=headers,
    )
    assert filtered.status_code == 200, filtered.text
    body = filtered.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert {item["type"] for item in body["items"]} == {"违约通知"}

    # 分页：page_size=2 时第 1 页只返回 2 条，但 total 仍是 2（筛选后）
    paged = api_client.get(
        "/api/v1/messages/me",
        params={"type": "违约通知", "page": 1, "page_size": 1},
        headers=headers,
    )
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1


def test_messages_isolated_between_users(api_client, db, make_user) -> None:
    """消息按用户隔离：A 看不到 B 的消息。"""
    alice = make_user(
        student_no="S9002", name="甲", password_hash=hash_password("student123")
    )
    bob = make_user(
        student_no="S9003", name="乙", password_hash=hash_password("student123")
    )
    db.add_all(
        [
            StationMessage(user_id=alice.id, type="系统通知", title="a", content="甲的"),
            StationMessage(user_id=bob.id, type="系统通知", title="b", content="乙的"),
        ]
    )
    db.commit()
    headers = _login(api_client, "S9002", "student123")
    body = api_client.get(
        "/api/v1/messages/me", params={"page": 1, "page_size": 10}, headers=headers
    ).json()
    assert body["total"] == 1
    assert body["items"][0]["content"] == "甲的"


# ---------------------------------------------------------------- 投诉


def test_complaints_filter_by_submitter_and_keyword(api_client, db, make_user) -> None:
    """管理员可按提交人（user_id）与内容关键词筛选投诉。"""
    make_user(
        student_no="A9001",
        name="管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    alice = make_user(
        student_no="S9004", name="甲", password_hash=hash_password("student123")
    )
    bob = make_user(
        student_no="S9005", name="乙", password_hash=hash_password("student123")
    )
    db.add_all(
        [
            Complaint(
                user_id=alice.id, target_type="座位", target_id=1, content="夜间噪音很大"
            ),
            Complaint(
                user_id=alice.id, target_type="座位", target_id=2, content="座位损坏"
            ),
            Complaint(
                user_id=bob.id, target_type="自习室", target_id=1, content="空调太冷"
            ),
        ]
    )
    db.commit()
    headers = _login(api_client, "A9001", "admin123")

    # 按提交人：甲有 2 条
    by_user = api_client.get(
        "/api/v1/complaints", params={"user_id": alice.id}, headers=headers
    )
    assert by_user.status_code == 200, by_user.text
    assert by_user.json()["total"] == 2

    # 按关键词：只有 1 条命中「噪音」
    by_keyword = api_client.get(
        "/api/v1/complaints", params={"keyword": "噪音"}, headers=headers
    )
    assert by_keyword.status_code == 200, by_keyword.text
    assert by_keyword.json()["total"] == 1
    assert "噪音" in by_keyword.json()["items"][0]["content"]

    # 组合条件：甲 + 「座位」关键词
    combined = api_client.get(
        "/api/v1/complaints",
        params={"user_id": alice.id, "keyword": "座位"},
        headers=headers,
    )
    assert combined.json()["total"] == 1


# ---------------------------------------------------------------- 我的预约计数


def test_my_reservations_status_counts_grouped_and_filtered(
    api_client, db, make_user, make_room, make_seat, make_reservation
) -> None:
    """状态计数一次返回 5 个状态，且与列表共用用户范围与筛选条件。"""
    alice = make_user(
        student_no="S9010", name="计数用户", password_hash=hash_password("student123")
    )
    bob = make_user(
        student_no="S9011", name="其他用户", password_hash=hash_password("student123")
    )
    room = make_room()
    other_room = make_room()
    seat = make_seat(room.id)
    other_seat = make_seat(other_room.id)

    make_reservation(alice.id, seat.id, reserve_date=date(2099, 1, 1), status="待使用")
    make_reservation(alice.id, seat.id, reserve_date=date(2099, 1, 2), status="已完成")
    make_reservation(alice.id, seat.id, reserve_date=date(2099, 1, 3), status="已取消")
    make_reservation(alice.id, other_seat.id, reserve_date=date(2099, 1, 4), status="已违约")
    # 其他用户的记录不得计入
    make_reservation(bob.id, seat.id, reserve_date=date(2099, 1, 1), status="待使用")

    headers = _login(api_client, "S9010", "student123")

    all_counts = api_client.get(
        "/api/v1/reservations/me/status-counts", headers=headers
    )
    assert all_counts.status_code == 200, all_counts.text
    body = all_counts.json()
    assert body["counts"] == {
        "待使用": 1,
        "使用中": 0,
        "已完成": 1,
        "已取消": 1,
        "已违约": 1,
    }
    assert body["total"] == 4

    # 日期区间筛选：只统计当天
    by_date = api_client.get(
        "/api/v1/reservations/me/status-counts",
        params={"reserve_date_from": "2099-01-02", "reserve_date_to": "2099-01-02"},
        headers=headers,
    )
    assert by_date.status_code == 200, by_date.text
    assert by_date.json()["counts"]["已完成"] == 1
    assert by_date.json()["total"] == 1

    # 自习室筛选：只统计另一间馆的违约记录
    by_room = api_client.get(
        "/api/v1/reservations/me/status-counts",
        params={"room_id": other_room.id},
        headers=headers,
    )
    assert by_room.status_code == 200, by_room.text
    assert by_room.json()["counts"]["已违约"] == 1
    assert by_room.json()["total"] == 1


# ---------------------------------------------------------------- 停用账户


def test_disabled_account_returns_403_not_401(api_client, db, make_user) -> None:
    """停用账户访问受保护接口应返回 403（而非 401「登录过期」）。"""
    user = make_user(
        student_no="S9006", name="停用用户", password_hash=hash_password("student123")
    )
    token = create_access_token(str(user.id), user.role)

    user.account_status = AccountStatus.DISABLED.value
    db.commit()

    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403, response.text
    # 统一异常处理器把 HTTPException 包装为 {code, message}
    assert "停用" in response.json()["message"]


def test_normal_account_can_read_me(api_client, db, make_user) -> None:
    """对照用例：正常账户仍可访问（避免上面的改动误伤）。"""
    make_user(
        student_no="S9007", name="正常用户", password_hash=hash_password("student123")
    )
    headers = _login(api_client, "S9007", "student123")
    response = api_client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["student_no"] == "S9007"
