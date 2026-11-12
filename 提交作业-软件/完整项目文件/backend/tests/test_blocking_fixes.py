"""本轮阻塞级修复回归：BR-018 权限拆分、联系方式脱敏、FR-051 口径、JWT 校验。"""

from datetime import date, datetime, time, timedelta

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.enums import Role
from app.services import (
    attendance_service,
    dashboard_service,
    notification_service,
    user_service,
)
from app.utils import masking, time_utils


@pytest.fixture(autouse=True)
def _fixed_now_and_silent_notifications(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: datetime(2026, 11, 2, 10, 0))
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _login(api_client, student_no: str, password: str) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---- #2 联系方式服务端脱敏（§5.6 / NFR-006）----


def test_mask_contact_phone_and_email():
    assert masking.mask_contact("13800001234") == "138****1234"
    assert masking.mask_contact("student@zju.edu.cn") == "s******@zju.edu.cn"
    assert masking.mask_contact(None) == "—"
    assert masking.mask_contact("") == "—"


def test_list_users_masks_contact_for_admin(
    api_client, db, make_user
) -> None:
    student = make_user(
        student_no="S7001",
        name="学生甲",
        contact="13800001234",
        password_hash=hash_password("student123"),
    )
    admin = make_user(
        student_no="A7001",
        name="管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    headers = _login(api_client, "A7001", "admin123")

    response = api_client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    target = next(item for item in items if item["id"] == student.id)
    # 管理员列表中联系方式须脱敏，不得返回明文
    assert target["contact"] == "138****1234"
    assert "13800001234" not in response.text


def test_my_profile_keeps_raw_contact(api_client, db, make_user) -> None:
    make_user(
        student_no="S7002",
        name="学生乙",
        contact="me@example.com",
        password_hash=hash_password("student123"),
    )
    headers = _login(api_client, "S7002", "student123")

    # 本人读取本人资料须返回原文（用户可自行修改联系方式）
    me = api_client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["contact"] == "me@example.com"

    auth_me = api_client.get("/api/v1/auth/me", headers=headers)
    assert auth_me.status_code == 200, auth_me.text
    assert auth_me.json()["contact"] == "me@example.com"


# ---- #1 BR-018 权限拆分（§4.1.1 定稿矩阵）----


def test_system_admin_rejected_from_business_endpoints(
    api_client, db, make_user
) -> None:
    make_user(
        student_no="R04001",
        name="系统管理员",
        role=Role.SYSTEM_ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    headers = _login(api_client, "R04001", "admin123")

    # R-04 系统管理员本版无业务操作权限：看板、用户列表等业务接口一律 403
    overview = api_client.get("/api/v1/dashboard/overview", headers=headers)
    assert overview.status_code == 403, overview.text

    users = api_client.get("/api/v1/users", headers=headers)
    assert users.status_code == 403, users.text


def test_teacher_role_removed(db) -> None:
    """V2.1（2026-11-05）：教师角色已取消，Role 枚举与数据库约束都不再接受「教师用户」。"""
    from sqlalchemy.exc import IntegrityError

    from app.models.user import User

    # 枚举层：不再提供 TEACHER
    assert "教师用户" not in {item.value for item in Role}
    assert not hasattr(Role, "TEACHER")

    # 数据层：直接写入非法角色应被 ck_user_role 拒绝
    db.add(
        User(
            name="教师",
            student_no="T8001",
            password_hash="hash",
            role="教师用户",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_business_admin_still_has_access(api_client, db, make_user) -> None:
    """R-02 业务管理员权限不受拆分影响（回归保障）。"""
    make_user(
        student_no="A7002",
        name="业务管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    headers = _login(api_client, "A7002", "admin123")

    overview = api_client.get("/api/v1/dashboard/overview", headers=headers)
    assert overview.status_code == 200, overview.text


# ---- #3 FR-051 折线图按状态流转统计 ----


def test_trend_counts_transitions_not_created_at(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    """FR-051：每日有效预约数 = 当日由待使用进入使用中/已完成的预约单张数。"""
    check_in_at = datetime(2026, 11, 2, 14, 0)
    monkeypatch.setattr(time_utils, "now", lambda: check_in_at)
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    day = check_in_at.date()

    # 直接构造一张「待使用」预约（绕过创建校验，专注验证 trend 口径）
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=day,
        start_time=time(14, 0),
        end_time=time(16, 0),
    )

    # 未签到未签退 → 当日有效预约数应为 0（旧口径按 created_at 会错误地计 1）
    points = dashboard_service.get_trend(db, day, day)
    assert len(points) == 1
    assert points[0].reservations == 0

    # 签到后 → 进入使用中的流转 → 计 1
    attendance_service.check_in(db, user.id, reservation.id)
    points = dashboard_service.get_trend(db, day, day)
    assert points[0].reservations == 1


def test_trend_dedupes_same_day_checkin_and_checkout(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    """同一预约单当日签到又签退仍计 1 张（FR-051 计的是预约单张数，去重）。"""
    fixed = datetime(2026, 11, 2, 14, 0)
    monkeypatch.setattr(time_utils, "now", lambda: fixed)
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    day = fixed.date()

    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=day,
        start_time=time(14, 0),
        end_time=time(16, 0),
    )
    attendance_service.check_in(db, user.id, reservation.id)
    attendance_service.check_out(db, user.id, reservation.id)

    points = dashboard_service.get_trend(db, day, day)
    assert points[0].reservations == 1


def test_trend_zero_day_has_no_breakpoint(db) -> None:
    """FR-051 验收：某日无流转则取值为 0 而非断点。"""
    points = dashboard_service.get_trend(db, date(2026, 11, 1), date(2026, 11, 3))
    assert len(points) == 3
    assert all(p.reservations == 0 and p.violations == 0 for p in points)


# ---- #5 JWT 密钥启动校验 ----


def test_validate_security_rejects_placeholder():
    original = settings.jwt_secret_key
    try:
        settings.jwt_secret_key = settings.JWT_SECRET_PLACEHOLDER
        with pytest.raises(RuntimeError, match="未配置"):
            settings.validate_security()
    finally:
        settings.jwt_secret_key = original


def test_validate_security_rejects_short_key():
    original = settings.jwt_secret_key
    try:
        settings.jwt_secret_key = "short"
        with pytest.raises(RuntimeError, match="长度不足"):
            settings.validate_security()
    finally:
        settings.jwt_secret_key = original


def test_validate_security_accepts_valid_key():
    original = settings.jwt_secret_key
    try:
        settings.jwt_secret_key = "a" * 40
        settings.validate_security()  # 不抛异常即通过
    finally:
        settings.jwt_secret_key = original


# ---- #5 资源只读接口须登录（需求 §3.3「已登录用户可读」）----


def test_resource_read_endpoints_require_auth(api_client) -> None:
    # 未登录访问资源只读接口应返回 401，而非开放枚举
    rooms = api_client.get("/api/v1/rooms")
    assert rooms.status_code == 401, rooms.text

    seats = api_client.get("/api/v1/rooms/1/seats")
    assert seats.status_code == 401, seats.text


def test_resource_read_endpoints_accessible_after_login(
    api_client, db, make_user, make_room
) -> None:
    make_user(
        student_no="S7100",
        name="学生",
        password_hash=hash_password("student123"),
    )
    make_room()
    headers = _login(api_client, "S7100", "student123")

    rooms = api_client.get("/api/v1/rooms", headers=headers)
    assert rooms.status_code == 200, rooms.text
    assert len(rooms.json()) >= 1


# ---- #6 账户停用 / 恢复端点 + 登录失败审计 ----


def test_login_failed_audited_for_wrong_password(
    api_client, db, make_user
) -> None:
    from app.models.audit_log import AuditLog

    make_user(
        student_no="S7201",
        name="学生",
        password_hash=hash_password("student123"),
    )
    # 错误密码登录应返回 401
    response = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S7201", "password": "wrong-password"},
    )
    assert response.status_code == 401, response.text

    # 应写一条 LOGIN_FAILED 审计日志
    log = db.query(AuditLog).filter(AuditLog.action_type == "LOGIN_FAILED").first()
    assert log is not None
    assert "S7201" in (log.reason or "")


def test_disable_and_restore_account(api_client, db, make_user) -> None:
    from app.models.enums import AccountStatus

    student = make_user(
        student_no="S7202",
        name="学生",
        password_hash=hash_password("student123"),
    )
    admin = make_user(
        student_no="A7202",
        name="管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    headers = _login(api_client, "A7202", "admin123")

    # ST-044：停用账户
    disabled = api_client.patch(
        f"/api/v1/users/{student.id}/account-status",
        headers=headers,
        json={"account_status": "停用", "reason": "违规操作暂停使用"},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["account_status"] == "停用"

    # 停用账户登录应被拒绝（403）
    denied = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S7202", "password": "student123"},
    )
    assert denied.status_code == 403, denied.text

    # ST-046：恢复账户
    restored = api_client.patch(
        f"/api/v1/users/{student.id}/account-status",
        headers=headers,
        json={"account_status": "正常", "reason": "核实完毕，恢复使用"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["account_status"] == "正常"

    # 恢复后可正常登录
    ok = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "S7202", "password": "student123"},
    )
    assert ok.status_code == 200, ok.text


def test_disable_account_rejects_same_status(api_client, db, make_user) -> None:
    student = make_user(
        student_no="S7203",
        name="学生",
        password_hash=hash_password("student123"),
    )
    make_user(
        student_no="A7203",
        name="管理员",
        role=Role.ADMIN.value,
        password_hash=hash_password("admin123"),
    )
    headers = _login(api_client, "A7203", "admin123")

    # 账户已为「正常」，再次设为「正常」应 409
    response = api_client.patch(
        f"/api/v1/users/{student.id}/account-status",
        headers=headers,
        json={"account_status": "正常", "reason": "重复操作"},
    )
    assert response.status_code == 409, response.text


# ---- 场地关闭：改为「关闭时间窗」实体，不再永久停用座位 ----


def test_room_close_creates_window_without_disabling_seats(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    """场地临时关闭生成关闭时间窗记录，座位资源状态保持不变。

    旧实现会把座位永久置为「停用」并需要对窗口外预约做孤儿提示；
    现行实现改用 `RoomClosure` 时间窗（可自动失效、可提前解除），
    因此座位仍为「可用」，窗口内由可预约性计算判定不可约。
    """
    from datetime import date, datetime, time

    from sqlalchemy import select

    from app.models.enums import ReservationStatus, SeatStatus
    from app.models.room import RoomClosure
    from app.schemas.room import RoomCloseRequest
    from app.services import room_service

    notified: list[int] = []
    monkeypatch.setattr(
        notification_service,
        "notify_safe",
        lambda **kwargs: notified.append(kwargs.get("user_id")),
    )

    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    # 窗口内冲突预约（11/3 14-16，关闭窗口 11/3 13-17）
    inside = make_reservation(
        user.id, seat.id,
        reserve_date=date(2026, 11, 3),
        start_time=time(14, 0), end_time=time(16, 0),
    )
    # 窗口外未来预约（11/5 14-16，与关闭窗口不重叠）
    outside = make_reservation(
        user.id, seat.id,
        reserve_date=date(2026, 11, 5),
        start_time=time(14, 0), end_time=time(16, 0),
    )

    result = room_service.close_room(
        db,
        room.id,
        RoomCloseRequest(
            start_at=datetime(2026, 11, 3, 13, 0),
            end_at=datetime(2026, 11, 3, 17, 0),
            reason="考试封场",
            cancel_affected=False,
            expected_reservation_ids=[inside.id],
        ),
        operator_id=user.id,
    )

    # 窗口内预约被保留（默认不取消）；窗口外预约同样不受影响
    assert result.kept == 1
    assert result.notified_outside_window == 0
    db.refresh(inside)
    db.refresh(outside)
    assert inside.status == ReservationStatus.PENDING.value
    assert outside.status == ReservationStatus.PENDING.value

    # 座位资源状态保持不变（不再永久停用）
    db.refresh(seat)
    assert seat.status == SeatStatus.AVAILABLE.value

    # 生成关闭时间窗记录
    closure = db.scalar(select(RoomClosure).where(RoomClosure.room_id == room.id))
    assert closure is not None
    assert closure.start_at == datetime(2026, 11, 3, 13, 0)
    assert closure.end_at == datetime(2026, 11, 3, 17, 0)

    # 仅窗口内被保留的预约收到提示（窗口外无需孤儿提示）
    assert notified.count(user.id) == 1
