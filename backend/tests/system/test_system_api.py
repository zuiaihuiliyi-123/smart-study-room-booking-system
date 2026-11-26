"""系统测试：对真实运行的后端 + MySQL 做端到端 HTTP 验证。

默认跳过；启动隔离环境后显式设置 ``SYSTEM_BASE_URL`` 运行：

    SYSTEM_BASE_URL=http://127.0.0.1:8010 pytest tests/system -q

测试使用独立数据库与随机学号，不依赖、也不修改开发库数据。
"""

from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest

BASE_URL = os.getenv("SYSTEM_BASE_URL")
pytestmark = pytest.mark.skipif(
    not BASE_URL, reason="未设置 SYSTEM_BASE_URL，跳过系统测试"
)

TZ = ZoneInfo("Asia/Shanghai")


@pytest.fixture(scope="module")
def http() -> httpx.Client:
    assert BASE_URL
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        yield client


def _login(client: httpx.Client, student_no: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _available_seats(
    client: httpx.Client,
    token: str,
    room_id: int,
    reserve_date: str,
    start: str,
    end: str,
) -> list[dict]:
    response = client.get(
        "/api/v1/reservations/available-seats",
        params={
            "room_id": room_id,
            "reserve_date": reserve_date,
            "start_time": start,
            "end_time": end,
        },
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_reservation(
    client: httpx.Client,
    token: str,
    seat_id: int,
    reserve_date: str,
    start: str,
    end: str,
    key: str | None = None,
) -> dict:
    response = client.post(
        "/api/v1/reservations",
        json={
            "seat_id": seat_id,
            "reserve_date": reserve_date,
            "start_time": start,
            "end_time": end,
            "idempotency_key": key or uuid.uuid4().hex,
        },
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _reservation_status(
    client: httpx.Client, token: str, reservation_id: int
) -> str:
    response = client.get(
        "/api/v1/reservations/me",
        params={"page": 1, "page_size": 100},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    for item in response.json()["items"]:
        if item["id"] == reservation_id:
            return item["status"]
    raise AssertionError(f"预约 {reservation_id} 不在本人预约列表中")


def _next_slot(now: datetime) -> datetime:
    minutes = now.hour * 60 + now.minute
    aligned = ((minutes // 5) + 1) * 5
    if aligned >= 24 * 60:  # 已接近零点：返回当前时间，后续可行性判断会跳过
        return now
    return now.replace(
        hour=aligned // 60, minute=aligned % 60, second=0, microsecond=0
    )


def test_production_surface_and_authorization(http: httpx.Client) -> None:
    health = http.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    # 隔离后端以 APP_ENV=production 启动：接口文档必须关闭
    assert http.get("/docs").status_code == 404
    assert http.get("/openapi.json").status_code == 404

    anonymous = http.get("/api/v1/users")
    assert anonymous.status_code == 401

    student_token = _login(http, "student", "student123")
    student_me = http.get("/api/v1/auth/me", headers=_auth(student_token))
    assert student_me.status_code == 200
    assert student_me.json()["role"] == "学生用户"

    forbidden = http.get("/api/v1/users", headers=_auth(student_token))
    assert forbidden.status_code == 403

    admin_token = _login(http, "admin", "admin123")
    admin_me = http.get("/api/v1/auth/me", headers=_auth(admin_token))
    assert admin_me.status_code == 200
    assert admin_me.json()["role"] == "自习室管理员"
    assert http.get("/api/v1/users", headers=_auth(admin_token)).status_code == 200


def _register(client: httpx.Client, student_no: str) -> tuple[str, int]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "student_no": student_no,
            "name": "系统测试学生",
            "password": "SysTest123",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers=_auth(token)).json()
    return token, me["id"]


def test_concurrent_idempotent_booking_on_real_mysql(http: httpx.Client) -> None:
    """真实 MySQL 下：同键并发只落一张单，另一用户同座位同时段被 C3 拒绝。"""
    now = datetime.now(TZ)
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    suffix = uuid.uuid4().hex[:8]
    token_a, _ = _register(http, f"SYSA{suffix}")
    token_b, _ = _register(http, f"SYSB{suffix}")

    rooms = http.get("/api/v1/rooms", headers=_auth(token_a)).json()
    room_id = next(room["id"] for room in rooms if room["enabled"])
    seats = _available_seats(http, token_a, room_id, tomorrow, "16:00", "18:00")
    assert seats
    seat_id = seats[0]["id"]

    key = uuid.uuid4().hex
    payload = {
        "seat_id": seat_id,
        "reserve_date": tomorrow,
        "start_time": "16:00",
        "end_time": "18:00",
        "idempotency_key": key,
    }
    barrier = threading.Barrier(5, timeout=15)

    def attempt() -> tuple[int, dict]:
        assert BASE_URL
        with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
            barrier.wait()
            response = client.post(
                "/api/v1/reservations",
                json=payload,
                headers=_auth(token_a),
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = [future.result() for future in [pool.submit(attempt) for _ in range(5)]]

    assert all(status == 200 for status, _ in results), results
    assert len({body["id"] for _, body in results}) == 1

    mine = http.get(
        "/api/v1/reservations/me",
        params={"page": 1, "page_size": 100},
        headers=_auth(token_a),
    ).json()
    matched = [
        item
        for item in mine["items"]
        if item["seat_id"] == seat_id and item["reserve_date"] == tomorrow
    ]
    assert len(matched) == 1

    conflict = http.post(
        "/api/v1/reservations",
        json={**payload, "idempotency_key": uuid.uuid4().hex},
        headers=_auth(token_b),
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "C3_BR-006"


def test_full_business_flow(http: httpx.Client) -> None:
    now = datetime.now(TZ)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    tomorrow_text = tomorrow.isoformat()

    # ---------- 注册与登录 ----------
    suffix = f"{now:%H%M%S}{uuid.uuid4().hex[:4]}"
    student_no = f"SYS{suffix}"
    password = "SysTest123"
    register = http.post(
        "/api/v1/auth/register",
        json={"student_no": student_no, "name": "系统测试学生", "password": password},
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    me = http.get("/api/v1/auth/me", headers=_auth(token)).json()
    user_id = me["id"]
    assert me["student_no"] == student_no

    rooms = http.get("/api/v1/rooms", headers=_auth(token)).json()
    room_id = next(room["id"] for room in rooms if room["enabled"])

    # ---------- 预约、幂等、冲突 ----------
    seats = _available_seats(http, token, room_id, tomorrow_text, "14:00", "16:00")
    assert seats, "明天 14:00-16:00 应存在可约座位"
    seat_id = seats[0]["id"]

    key = uuid.uuid4().hex
    created = _create_reservation(
        http, token, seat_id, tomorrow_text, "14:00", "16:00", key
    )
    reservation_id = created["id"]
    assert created["status"] == "待使用"

    replay = _create_reservation(
        http, token, seat_id, tomorrow_text, "14:00", "16:00", key
    )
    assert replay["id"] == reservation_id, "同一幂等键必须返回同一张预约"

    reused = http.post(
        "/api/v1/reservations",
        json={
            "seat_id": seat_id,
            "reserve_date": tomorrow_text,
            "start_time": "14:00",
            "end_time": "17:00",
            "idempotency_key": key,
        },
        headers=_auth(token),
    )
    assert reused.status_code == 409, reused.text
    assert reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"

    after_booking = _available_seats(
        http, token, room_id, tomorrow_text, "14:00", "16:00"
    )
    assert seat_id not in {seat["id"] for seat in after_booking}

    mine = http.get("/api/v1/reservations/me", headers=_auth(token))
    assert mine.status_code == 200
    assert reservation_id in {item["id"] for item in mine.json()["items"]}

    cancel = http.post(
        f"/api/v1/reservations/{reservation_id}/cancel",
        json={"reason": "系统测试取消"},
        headers=_auth(token),
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["message"] == "预约已取消"
    assert _reservation_status(http, token, reservation_id) == "已取消"

    after_cancel = _available_seats(
        http, token, room_id, tomorrow_text, "14:00", "16:00"
    )
    assert seat_id in {seat["id"] for seat in after_cancel}

    # ---------- 签到 / 签退（真实时间窗口） ----------
    start_dt = _next_slot(now)
    end_dt = start_dt + timedelta(minutes=60)
    if start_dt.time() >= time(8, 0) and end_dt.time() <= time(21, 55):
        start_text = start_dt.strftime("%H:%M")
        end_text = end_dt.strftime("%H:%M")
        today_text = today.isoformat()
        live_seats = _available_seats(
            http, token, room_id, today_text, start_text, end_text
        )
        assert live_seats
        live_seat = live_seats[0]["id"]
        live = _create_reservation(
            http, token, live_seat, today_text, start_text, end_text
        )

        check_in = http.post(
            f"/api/v1/reservations/{live['id']}/check-in", headers=_auth(token)
        )
        assert check_in.status_code == 200, check_in.text
        assert check_in.json()["message"] == "签到成功"
        assert _reservation_status(http, token, live["id"]) == "使用中"

        check_out = http.post(
            f"/api/v1/reservations/{live['id']}/check-out", headers=_auth(token)
        )
        assert check_out.status_code == 200, check_out.text
        assert check_out.json()["message"] == "签退成功"
        assert _reservation_status(http, token, live["id"]) == "已完成"

    # ---------- 管理员手动违约 ----------
    admin_token = _login(http, "admin", "admin123")
    violation_target = None
    if start_dt.time() >= time(8, 0) and end_dt.time() <= time(21, 55):
        seats_now = _available_seats(
            http, token, room_id, today.isoformat(), start_text, end_text
        )
        assert seats_now
        violation_target = _create_reservation(
            http,
            token,
            seats_now[0]["id"],
            today.isoformat(),
            start_text,
            end_text,
        )
        checked = http.post(
            f"/api/v1/reservations/{violation_target['id']}/check-in",
            headers=_auth(token),
        )
        assert checked.status_code == 200, checked.text

        manual = http.post(
            "/api/v1/violations/manual",
            json={
                "reservation_id": violation_target["id"],
                "reason": "系统测试手动违约",
            },
            headers=_auth(admin_token),
        )
        assert manual.status_code == 200, manual.text
        assert manual.json()["type"] == "手动违约"

    # ---------- 黑名单限制与解除 ----------
    expire_at = datetime.combine(tomorrow, time(12, 0)).isoformat()
    blacklist = http.post(
        "/api/v1/blacklist",
        json={"user_id": user_id, "reason": "系统测试限制", "expire_at": expire_at},
        headers=_auth(admin_token),
    )
    assert blacklist.status_code == 201, blacklist.text
    entry_id = blacklist.json()["id"]

    blocked = http.post(
        "/api/v1/reservations",
        json={
            "seat_id": seat_id,
            "reserve_date": tomorrow_text,
            "start_time": "14:00",
            "end_time": "16:00",
            "idempotency_key": uuid.uuid4().hex,
        },
        headers=_auth(token),
    )
    assert blocked.status_code == 403, blocked.text
    assert blocked.json()["code"] == "ST-047"

    released = http.post(
        f"/api/v1/blacklist/{entry_id}/release",
        json={"reason": "系统测试解除"},
        headers=_auth(admin_token),
    )
    assert released.status_code == 200, released.text

    # ---------- 投诉全流程 ----------
    complaint = http.post(
        "/api/v1/complaints",
        json={
            "target_type": "座位",
            "target_id": seat_id,
            "content": "系统测试投诉：座位附近有噪音",
        },
        headers=_auth(token),
    )
    assert complaint.status_code == 201, complaint.text
    complaint_id = complaint.json()["id"]

    listed = http.get(
        "/api/v1/complaints",
        params={"status": "待处理", "keyword": "系统测试投诉"},
        headers=_auth(admin_token),
    )
    assert listed.status_code == 200
    assert complaint_id in {item["id"] for item in listed.json()["items"]}

    processing = http.patch(
        f"/api/v1/complaints/{complaint_id}",
        json={"status": "处理中", "handle_note": "已受理，正在核实"},
        headers=_auth(admin_token),
    )
    assert processing.status_code == 200, processing.text
    assert processing.json()["status"] == "处理中"

    handled = http.patch(
        f"/api/v1/complaints/{complaint_id}",
        json={"status": "已处理", "handle_note": "已协调处理"},
        headers=_auth(admin_token),
    )
    assert handled.status_code == 200, handled.text
    assert handled.json()["status"] == "已处理"

    confirmed = http.post(
        f"/api/v1/complaints/{complaint_id}/confirm", headers=_auth(token)
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "已关闭"

    # ---------- 消息、看板、审计 ----------
    messages = http.get("/api/v1/messages/me", headers=_auth(token))
    assert messages.status_code == 200
    assert messages.json()["total"] >= 1

    today_text = today.isoformat()
    for path in ("/api/v1/dashboard/overview", "/api/v1/dashboard/trend"):
        response = http.get(path, params={"start_date": today_text, "end_date": today_text}, headers=_auth(admin_token))
        assert response.status_code == 200, (path, response.text)
    usage = http.get(
        "/api/v1/dashboard/seat-usage",
        params={"start_date": today_text, "end_date": today_text, "group_by": "seat"},
        headers=_auth(admin_token),
    )
    assert usage.status_code == 200

    audit = http.get("/api/v1/audit-logs", headers=_auth(admin_token))
    assert audit.status_code == 200
    assert audit.json()["total"] > 0
