"""生成 / 重置演示业务数据：python -m scripts.seed_demo_data [--reset]

分工：
- ``scripts.seed``：基础演示账户 admin / student；
- ``scripts.seed_demo``：演示自习室、分区、座位；
- 本脚本：在 ``scripts.seed_demo`` 提供的 3 间自习室 / 10 个分区 / 98 个座位上，
  按“当前时间”补齐预约、违约、黑名单、投诉、站内消息、评价和场地临时关闭，
  供 8～10 分钟课堂演示使用。

``--reset`` 只清理演示账号（student、demo_li、demo_wang、demo_zhao、demo_sun）
的业务数据，以及原因以「【演示】」开头的场地关闭记录；不会删除用户、其他用户的
数据、审计日志或数据库结构。审计日志按 NFR-009 只追加，重置时保留。
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.blacklist import BlacklistEntry
from app.models.complaint import Complaint
from app.models.enums import (
    AccountStatus,
    ComplaintStatus,
    ComplaintTargetType,
    MessageType,
    ReservationStatus,
    Role,
    ViolationType,
)
from app.models.message import StationMessage
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.review import Review
from app.models.room import Room, RoomClosure
from app.models.seat import Seat
from app.models.user import User
from app.models.violation import ViolationRecord
from app.schemas.blacklist import BlacklistCreate
from app.schemas.complaint import ComplaintCreate, ComplaintHandle
from app.schemas.review import ReviewCreate
from app.schemas.room import RoomCloseRequest
from app.schemas.violation import ManualViolationCreate
from app.services import (
    blacklist_service,
    complaint_service,
    review_service,
    room_service,
    violation_service,
)
from app.utils import time_utils
from scripts.seed_demo import ensure_demo_resources

DEMO_PASSWORD = "demo1234"
DEMO_STUDENT_NOS = ("student", "demo_li", "demo_wang", "demo_zhao", "demo_sun")
DEMO_REASON_PREFIX = "【演示】"
SEED_KEY_PREFIX = "demo-seed-"

_DEMO_USERS: tuple[tuple[str, str, str, Role], ...] = (
    ("student", "student123", "演示学生", Role.STUDENT),
    ("demo_li", DEMO_PASSWORD, "李思远", Role.STUDENT),
    ("demo_wang", DEMO_PASSWORD, "王浩", Role.STUDENT),
    ("demo_zhao", DEMO_PASSWORD, "赵敏", Role.STUDENT),
    ("demo_sun", DEMO_PASSWORD, "孙悦", Role.STUDENT),
)


# ---------------------------------------------------------------------------
# 时间与通用写入辅助
# ---------------------------------------------------------------------------


def _aligned(value: datetime, *, up: bool) -> datetime:
    """按预约粒度对齐到整 5 分钟（up=True 向上取整，否则向下取整）。"""
    gran = settings.reservation_granularity_minutes
    base = value.replace(second=0, microsecond=0)
    minutes = base.hour * 60 + base.minute
    remainder = minutes % gran
    if up and remainder:
        base += timedelta(minutes=gran - remainder)
    elif not up:
        base -= timedelta(minutes=remainder)
    return base


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute))


def _ensure_user(
    db: Session,
    student_no: str,
    password: str,
    name: str,
    role: Role,
) -> User:
    user = db.scalar(select(User).where(User.student_no == student_no))
    if user is None:
        user = User(
            name=name,
            student_no=student_no,
            password_hash=hash_password(password),
            role=role.value,
            account_status=AccountStatus.NORMAL.value,
            violation_count=0,
        )
        db.add(user)
        db.flush()
        return user
    # 演示账号的密码固定为文档中的值；student / admin 保持用户可能改过的密码。
    if student_no.startswith("demo_"):
        user.password_hash = hash_password(password)
    return user


def _seat(db: Session, room_name: str, seat_no: str) -> Seat:
    seat = db.scalar(
        select(Seat)
        .join(Room, Seat.room_id == Room.id)
        .where(Room.name == room_name, Seat.seat_no == seat_no)
    )
    if seat is None:
        raise RuntimeError(f"演示座位不存在：{room_name} / {seat_no}")
    return seat


def _add_reservation(
    db: Session,
    *,
    user: User,
    seat: Seat,
    day: date,
    start: time,
    end: time,
    status: ReservationStatus,
    label: str,
    check_in_time: datetime | None = None,
    check_out_time: datetime | None = None,
    cancel_time: datetime | None = None,
    cancel_reason: str | None = None,
    auto_completed: bool = False,
    created_at: datetime | None = None,
) -> Reservation:
    key = f"{SEED_KEY_PREFIX}{user.student_no}-{label}"
    reservation = Reservation(
        user_id=user.id,
        seat_id=seat.id,
        reserve_date=day,
        start_time=start,
        end_time=end,
        status=status.value,
        check_in_time=check_in_time,
        check_out_time=check_out_time,
        cancel_time=cancel_time,
        cancel_reason=cancel_reason,
        auto_completed=auto_completed,
        idempotency_key=key,
        created_at=created_at or time_utils.now(),
    )
    db.add(reservation)
    db.flush()

    # 只有有效预约占用时段；终态预约按业务规则不保留 slot。
    if status in (ReservationStatus.PENDING, ReservationStatus.IN_USE):
        cursor = datetime.combine(day, start)
        end_at = datetime.combine(day, end)
        while cursor < end_at:
            db.add(
                ReservationSlot(
                    reservation_id=reservation.id,
                    seat_id=seat.id,
                    user_id=user.id,
                    slot_start=cursor,
                )
            )
            cursor += timedelta(minutes=settings.reservation_granularity_minutes)
        db.flush()
    return reservation


def _add_violation(
    db: Session,
    reservation: Reservation,
    *,
    violation_type: ViolationType,
    reason: str,
    created_at: datetime,
    operator_id: int | None = None,
) -> ViolationRecord:
    record = ViolationRecord(
        user_id=reservation.user_id,
        reservation_id=reservation.id,
        type=violation_type.value,
        reason=reason,
        operator_id=operator_id,
        created_at=created_at,
    )
    reservation.status = ReservationStatus.VIOLATED.value
    db.add(record)
    db.flush()
    return record


def _add_message(
    db: Session,
    user: User,
    message_type: MessageType,
    title: str,
    content: str,
    *,
    is_read: bool = False,
    created_at: datetime | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
) -> StationMessage:
    message = StationMessage(
        user_id=user.id,
        type=message_type.value,
        title=title,
        content=content,
        is_read=is_read,
        created_at=created_at or time_utils.now(),
        related_type=related_type,
        related_id=related_id,
    )
    db.add(message)
    return message


# ---------------------------------------------------------------------------
# 清理
# ---------------------------------------------------------------------------


def _delete(db: Session, model, *conditions) -> int:
    statement = delete(model).where(*conditions).execution_options(
        synchronize_session=False
    )
    result = db.execute(statement)
    return int(result.rowcount or 0)


def reset_demo_data(db: Session) -> dict[str, int]:
    """清理演示账号的业务数据；返回各表删除行数。

    - 只处理 ``DEMO_STUDENT_NOS`` 中的账号，其他用户的数据不受影响；
    - 场地关闭只删除原因以「【演示】」开头的记录；
    - 审计日志按 NFR-009 保留（只追加，不删除）。
    """
    users = list(
        db.scalars(select(User).where(User.student_no.in_(DEMO_STUDENT_NOS))).all()
    )
    ids = [user.id for user in users]
    stats: dict[str, int] = {}

    if ids:
        # 先删引用 reservations 的子表，再删预约单。
        stats["reviews"] = _delete(db, Review, Review.user_id.in_(ids))
        stats["violations"] = _delete(
            db, ViolationRecord, ViolationRecord.user_id.in_(ids)
        )
        stats["slots"] = _delete(db, ReservationSlot, ReservationSlot.user_id.in_(ids))
        stats["reservations"] = _delete(
            db, Reservation, Reservation.user_id.in_(ids)
        )
        stats["complaints"] = _delete(db, Complaint, Complaint.user_id.in_(ids))
        stats["messages"] = _delete(
            db, StationMessage, StationMessage.user_id.in_(ids)
        )
        stats["blacklist"] = _delete(
            db, BlacklistEntry, BlacklistEntry.user_id.in_(ids)
        )
        db.execute(
            update(User)
            .where(User.id.in_(ids))
            .values(
                violation_count=0,
                account_status=AccountStatus.NORMAL.value,
            )
            .execution_options(synchronize_session=False)
        )

    stats["closures"] = _delete(
        db,
        RoomClosure,
        RoomClosure.reason.like(f"{DEMO_REASON_PREFIX}%"),
    )
    db.commit()
    return stats


def _has_seeded_data(db: Session) -> bool:
    count = db.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(Reservation.idempotency_key.like(f"{SEED_KEY_PREFIX}%"))
    )
    return bool(count)


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------


def seed_demo_data(db: Session, now: datetime | None = None) -> dict[str, int]:
    """补齐演示业务数据；调用方负责决定是否先执行 ``reset_demo_data``。"""
    now = now or time_utils.now()
    today = now.date()
    stats = {
        "users": 0,
        "reservations": 0,
        "violations": 0,
        "complaints": 0,
        "messages": 0,
        "reviews": 0,
        "closures": 0,
    }

    ensure_demo_resources(db)
    admin = _ensure_user(db, "admin", "admin123", "演示管理员", Role.ADMIN)
    users: dict[str, User] = {}
    for student_no, password, name, role in _DEMO_USERS:
        users[student_no] = _ensure_user(db, student_no, password, name, role)
    student, li = users["student"], users["demo_li"]
    wang, zhao, sun = users["demo_wang"], users["demo_zhao"], users["demo_sun"]
    stats["users"] = len(_DEMO_USERS)
    db.flush()

    room1 = db.scalar(select(Room).where(Room.name == "第一自习室"))
    room2 = db.scalar(select(Room).where(Room.name == "第二自习室"))
    room3 = db.scalar(select(Room).where(Room.name == "第三自习室"))
    if room1 is None or room2 is None or room3 is None:
        raise RuntimeError("演示自习室创建失败，请先运行 python -m scripts.seed_demo")

    # ---- 今天的“可签到”预约：开始时间在 10 分钟后，签到窗口已打开 ----
    # 夜间/闭馆后无法演示签到：顺延到明天 13:00，避开明天 09:00-11:00 的取消演示预约，
    # 否则同一用户同一时段会产生 C4 冲突，槽位唯一约束也会直接失败。
    soon_start = _aligned(now + timedelta(minutes=10), up=True)
    check_in_demo_available = (
        soon_start.date() == today
        and time(8, 0) <= soon_start.time() <= time(20, 55)
    )
    if not check_in_demo_available:
        soon_start = _at(today + timedelta(days=1), 13, 0)
    soon_end = soon_start + timedelta(hours=1)

    r_student_soon = _add_reservation(
        db,
        user=student,
        seat=_seat(db, "第一自习室", "A-01"),
        day=soon_start.date(),
        start=soon_start.time(),
        end=soon_end.time(),
        status=ReservationStatus.PENDING,
        label="soon",
        created_at=now,
    )

    # ---- 明天：用于“取消预约”演示 ----
    tomorrow = today + timedelta(days=1)
    r_student_tomorrow = _add_reservation(
        db,
        user=student,
        seat=_seat(db, "第一自习室", "A-02"),
        day=tomorrow,
        start=time(9, 0),
        end=time(11, 0),
        status=ReservationStatus.PENDING,
        label="tomorrow",
        created_at=now,
    )

    # ---- 历史记录：已完成 / 已违约 / 已取消 ----
    r_student_done = _add_reservation(
        db,
        user=student,
        seat=_seat(db, "第一自习室", "A-03"),
        day=today - timedelta(days=1),
        start=time(14, 0),
        end=time(15, 0),
        status=ReservationStatus.COMPLETED,
        label="done",
        check_in_time=_at(today - timedelta(days=1), 14, 3),
        check_out_time=_at(today - timedelta(days=1), 14, 55),
        created_at=_at(today - timedelta(days=2), 20, 0),
    )
    r_student_violated = _add_reservation(
        db,
        user=student,
        seat=_seat(db, "第一自习室", "A-04"),
        day=today - timedelta(days=3),
        start=time(10, 0),
        end=time(11, 0),
        status=ReservationStatus.VIOLATED,
        label="violated",
        created_at=_at(today - timedelta(days=4), 9, 0),
    )
    _add_reservation(
        db,
        user=student,
        seat=_seat(db, "第三自习室", "D-01"),
        day=today - timedelta(days=4),
        start=time(16, 0),
        end=time(17, 0),
        status=ReservationStatus.CANCELLED,
        label="cancelled",
        cancel_time=_at(today - timedelta(days=4), 15, 10),
        cancel_reason="临时有课，行程调整",
        created_at=_at(today - timedelta(days=4), 12, 0),
    )
    _add_violation(
        db,
        r_student_violated,
        violation_type=ViolationType.AUTO,
        reason="超过签到截止时间（开始后 15 分钟）仍未签到，系统自动判定违约",
        created_at=_at(today - timedelta(days=3), 11, 20),
    )
    blacklist_service.restrict_if_threshold(db, student.id, now=now)
    stats["violations"] += 1

    # ---- demo_li：明天被临时关闭影响的预约、第三自习室历史完成预约 ----
    r_li_tomorrow = _add_reservation(
        db,
        user=li,
        seat=_seat(db, "第二自习室", "C-01"),
        day=tomorrow,
        start=time(14, 0),
        end=time(15, 0),
        status=ReservationStatus.PENDING,
        label="closure-affected",
        created_at=now,
    )
    _add_reservation(
        db,
        user=li,
        seat=_seat(db, "第三自习室", "E-02"),
        day=today - timedelta(days=2),
        start=time(9, 0),
        end=time(10, 0),
        status=ReservationStatus.COMPLETED,
        label="done",
        check_in_time=_at(today - timedelta(days=2), 9, 2),
        check_out_time=_at(today - timedelta(days=2), 9, 55),
        created_at=_at(today - timedelta(days=3), 18, 0),
    )

    # demo_li 的“使用中”预约：用于演示管理员手动违约登记。
    li_in_use_start = _aligned(now - timedelta(minutes=20), up=False)
    if li_in_use_start.date() != today or li_in_use_start.time() < time(8, 0):
        li_in_use_start = _at(today, 8, 5)
    li_in_use_end = li_in_use_start + timedelta(minutes=90)
    r_li_in_use = _add_reservation(
        db,
        user=li,
        seat=_seat(db, "第二自习室", "C-04"),
        day=li_in_use_start.date(),
        start=li_in_use_start.time(),
        end=li_in_use_end.time(),
        status=ReservationStatus.IN_USE,
        label="in-use",
        check_in_time=li_in_use_start + timedelta(minutes=3),
        created_at=li_in_use_start - timedelta(hours=2),
    )
    violation_service.register_manual(
        db,
        admin,
        ManualViolationCreate(
            reservation_id=r_li_in_use.id,
            reason="离开超过 40 分钟且未签退，管理员现场核实后登记",
        ),
    )
    stats["violations"] += 1

    # ---- demo_wang：3 次自动违约（分布在 3 间自习室）+ 自动黑名单（受限） ----
    wang_specs = (
        (2, time(9, 0), time(10, 0), "第一自习室", "B-01"),
        (3, time(14, 0), time(15, 0), "第二自习室", "D-02"),
        (4, time(16, 0), time(17, 0), "第三自习室", "F-02"),
    )
    for offset, start, end, room_name, seat_no in wang_specs:
        day = today - timedelta(days=offset)
        reservation = _add_reservation(
            db,
            user=wang,
            seat=_seat(db, room_name, seat_no),
            day=day,
            start=start,
            end=end,
            status=ReservationStatus.VIOLATED,
            label=f"violated-{offset}",
            created_at=_at(day, 8, 0),
        )
        _add_violation(
            db,
            reservation,
            violation_type=ViolationType.AUTO,
            reason="超过签到截止时间（开始后 15 分钟）仍未签到，系统自动判定违约",
            created_at=_at(day, end.hour, end.minute) + timedelta(minutes=20),
        )
        stats["violations"] += 1
    entry = blacklist_service.restrict_if_threshold(db, wang.id, now=now)
    if entry is None:
        raise RuntimeError("demo_wang 的自动黑名单创建失败（可能已存在有效限制）")

    _add_reservation(
        db,
        user=wang,
        seat=_seat(db, "第三自习室", "D-03"),
        day=today - timedelta(days=5),
        start=time(10, 0),
        end=time(11, 0),
        status=ReservationStatus.CANCELLED,
        label="cancelled",
        cancel_time=_at(today - timedelta(days=5), 9, 20),
        cancel_reason="临时调整",
        created_at=_at(today - timedelta(days=5), 8, 30),
    )

    # ---- demo_zhao：“使用中”预约（现场演示手动违约）+ 两条已完成预约 ----
    zhao_in_use_start = _aligned(now - timedelta(minutes=10), up=False)
    if zhao_in_use_start.date() != today or zhao_in_use_start.time() < time(8, 0):
        zhao_in_use_start = _at(today, 8, 10)
    zhao_in_use_end = zhao_in_use_start + timedelta(minutes=60)
    _add_reservation(
        db,
        user=zhao,
        seat=_seat(db, "第二自习室", "D-05"),
        day=zhao_in_use_start.date(),
        start=zhao_in_use_start.time(),
        end=zhao_in_use_end.time(),
        status=ReservationStatus.IN_USE,
        label="in-use",
        check_in_time=zhao_in_use_start + timedelta(minutes=2),
        created_at=zhao_in_use_start - timedelta(hours=2),
    )
    r_zhao_done1 = _add_reservation(
        db,
        user=zhao,
        seat=_seat(db, "第二自习室", "E-03"),
        day=today - timedelta(days=1),
        start=time(15, 0),
        end=time(16, 0),
        status=ReservationStatus.COMPLETED,
        label="done-1",
        check_in_time=_at(today - timedelta(days=1), 15, 1),
        check_out_time=_at(today - timedelta(days=1), 15, 58),
        created_at=_at(today - timedelta(days=2), 19, 0),
    )
    r_zhao_done2 = _add_reservation(
        db,
        user=zhao,
        seat=_seat(db, "第三自习室", "E-01"),
        day=today - timedelta(days=5),
        start=time(10, 0),
        end=time(11, 0),
        status=ReservationStatus.COMPLETED,
        label="done-2",
        check_in_time=_at(today - timedelta(days=5), 10, 4),
        check_out_time=_at(today - timedelta(days=5), 10, 56),
        created_at=_at(today - timedelta(days=6), 20, 0),
    )

    # ---- 手动黑名单：演示“自动 / 手动”两种来源 ----
    if db.scalar(
        select(func.count())
        .select_from(BlacklistEntry)
        .where(
            BlacklistEntry.user_id == sun.id,
            BlacklistEntry.released_at.is_(None),
        )
    ) == 0:
        blacklist_service.add_entry(
            db,
            admin,
            BlacklistCreate(
                user_id=sun.id,
                reason="多次预约后未使用且拒绝沟通，管理员手动限制",
                expire_at=now + timedelta(days=5),
            ),
        )

    # ---- 投诉：待处理 / 处理中 / 已处理 / 已驳回 / 已关闭 ----
    complaint_service.create_complaint(
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.SEAT,
            target_id=_seat(db, "第一自习室", "A-04").id,
            content="A-04 座位的台灯不亮，晚上看书比较吃力，希望尽快维修。",
        ),
    )
    stats["complaints"] += 1

    li_complaint = complaint_service.create_complaint(
        db,
        li.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM,
            target_id=room2.id,
            content="第二自习室空调温度偏低，靠窗区域体感明显。",
        ),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        li_complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="已联系物业检查空调"),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        li_complaint.id,
        ComplaintHandle(
            status=ComplaintStatus.RESOLVED,
            handle_note="已将空调温度调整为 26℃，并加装挡风板",
        ),
    )
    complaint_service.confirm_close(db, li.id, li_complaint.id)
    stats["complaints"] += 1

    wang_complaint = complaint_service.create_complaint(
        db,
        wang.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.SEAT,
            target_id=_seat(db, "第二自习室", "C-02").id,
            content="我明明是按时到的，为什么记我违约？",
        ),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        wang_complaint.id,
        ComplaintHandle(
            status=ComplaintStatus.REJECTED,
            handle_note="经核验签到记录为空，违约判定无误；如有异议可现场联系管理员。",
        ),
    )
    stats["complaints"] += 1

    zhao_complaint = complaint_service.create_complaint(
        db,
        zhao.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM,
            target_id=room1.id,
            content="第一自习室有人长时间占座但未预约，希望加强巡查。",
        ),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        zhao_complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="已安排晚间巡查"),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        zhao_complaint.id,
        ComplaintHandle(
            status=ComplaintStatus.RESOLVED,
            handle_note="已清理占座物品并张贴提示，后续将每两小时巡查一次",
        ),
    )
    stats["complaints"] += 1

    # ---- 评价：仅对已完成预约 ----
    review_specs = (
        (student.id, r_student_done.id, 5, "座位安静，插座充足，签到流程很顺畅。"),
        (
            li.id,
            db.scalar(
                select(Reservation).where(
                    Reservation.user_id == li.id,
                    Reservation.idempotency_key == f"{SEED_KEY_PREFIX}demo_li-done",
                )
            ).id,
            4,
            "靠窗采光好，偶尔有人走动。",
        ),
        (zhao.id, r_zhao_done1.id, 5, "管理规范，桌面干净，体验很好。"),
        (zhao.id, r_zhao_done2.id, 3, "空调有点冷，其他方面不错。"),
    )
    for user_id, reservation_id, score, content in review_specs:
        review_service.create_review(
            db,
            user_id,
            ReviewCreate(reservation_id=reservation_id, score=score, content=content),
        )
        stats["reviews"] += 1

    # ---- 场地临时关闭：明天 14:00-16:00 关闭第二自习室，保留受影响预约 ----
    closure_start = _at(tomorrow, 14, 0)
    closure_end = _at(tomorrow, 16, 0)
    _, affected = room_service.preview_close(
        db, room2.id, closure_start, closure_end, None
    )
    room_service.close_room(
        db,
        room2.id,
        RoomCloseRequest(
            start_at=closure_start,
            end_at=closure_end,
            area_id=None,
            reason=f"{DEMO_REASON_PREFIX}设备检修",
            cancel_affected=False,
            expected_reservation_ids=sorted(item.id for item in affected),
        ),
        operator_id=admin.id,
    )
    stats["closures"] = 1

    # ---- 站内消息：补充服务未覆盖的提醒，并制造未读 ----
    _add_message(
        db,
        student,
        MessageType.SYSTEM,
        "欢迎使用智慧自习室",
        "预约、签到、签退都可在“我的预约”中完成；如需帮助请查看首页使用指引。",
        is_read=True,
        created_at=now - timedelta(days=7),
    )
    _add_message(
        db,
        student,
        MessageType.RESERVATION,
        "预约即将开始",
        (
            f"你在 {r_student_soon.reserve_date} 的预约即将开始，"
            f"请在开始前 15 分钟至开始后 15 分钟内签到。"
        ),
        created_at=now - timedelta(minutes=5),
        related_type="预约单",
        related_id=r_student_soon.id,
    )
    _add_message(
        db,
        student,
        MessageType.RESERVATION,
        "预约成功",
        f"你已预约 {r_student_tomorrow.reserve_date} 09:00-11:00 的座位。",
        created_at=now - timedelta(days=1),
        related_type="预约单",
        related_id=r_student_tomorrow.id,
    )
    _add_message(
        db,
        student,
        MessageType.VIOLATION,
        "自动违约通知",
        "你在 3 天前的预约未按时签到，已记 1 次违约；累计 3 次将自动限制账户 7 天。",
        created_at=now - timedelta(days=3, hours=1),
    )
    _add_message(
        db,
        student,
        MessageType.RESERVATION,
        "预约已取消",
        "你的历史预约已取消，该时段已重新开放。",
        is_read=True,
        created_at=now - timedelta(days=4),
    )
    _add_message(
        db,
        li,
        MessageType.SYSTEM,
        "所选座位临时关闭",
        "第二自习室明天 14:00-16:00 因设备检修临时关闭，你的预约暂时保留，请留意后续通知。",
        created_at=now - timedelta(minutes=30),
        related_type="预约单",
        related_id=r_li_tomorrow.id,
    )
    _add_message(
        db,
        zhao,
        MessageType.SYSTEM,
        "本周使用小结",
        "你本周已完成 2 次自习，累计使用 2 小时，欢迎继续预约。",
        is_read=True,
        created_at=now - timedelta(days=1),
    )
    for offset in (2, 3, 4):
        _add_message(
            db,
            wang,
            MessageType.VIOLATION,
            "自动违约通知",
            f"你在 {today - timedelta(days=offset)} 的预约未按时签到，已记录违约。",
            created_at=_at(today - timedelta(days=offset), 18, 0),
        )

    db.commit()
    demo_ids = [user.id for user in users.values()]
    stats["messages"] = db.scalar(
        select(func.count())
        .select_from(StationMessage)
        .where(StationMessage.user_id.in_(demo_ids))
    ) or 0
    stats["complaints"] = db.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.user_id.in_(demo_ids))
    ) or 0
    stats["reservations"] = db.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(Reservation.idempotency_key.like(f"{SEED_KEY_PREFIX}%"))
    ) or 0
    stats["violations"] = db.scalar(
        select(func.count())
        .select_from(ViolationRecord)
        .where(ViolationRecord.user_id.in_(demo_ids))
    ) or 0
    stats["check_in_ready"] = int(check_in_demo_available)
    return stats


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or reset the demo bookings/violations/complaints/messages."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear demo users' business data first, then recreate it.",
    )
    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="Only clear demo data; do not recreate.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    with SessionLocal() as db:
        if args.reset or args.reset_only:
            stats = reset_demo_data(db)
            print(
                "已清理演示数据："
                f"预约 {stats.get('reservations', 0)}、违约 {stats.get('violations', 0)}、"
                f"投诉 {stats.get('complaints', 0)}、消息 {stats.get('messages', 0)}、"
                f"评价 {stats.get('reviews', 0)}、黑名单 {stats.get('blacklist', 0)}、"
                f"场地关闭 {stats.get('closures', 0)}。"
            )
            if args.reset_only:
                return 0

        if not args.reset and _has_seeded_data(db):
            print("检测到已存在的演示业务数据，已跳过。需要重建请运行：")
            print("  python -m scripts.seed_demo_data --reset")
            return 0

        stats = seed_demo_data(db)

    print(
        "演示数据已就绪："
        f"预约 {stats['reservations']} 条、违约 {stats['violations']} 条、"
        f"投诉 {stats['complaints']} 条、评价 {stats['reviews']} 条、"
        f"消息 {stats['messages']} 条、场地关闭 {stats['closures']} 条。"
    )
    if not stats.get("check_in_ready"):
        print(
            "提示：当前不在 08:00-20:55 之间，签到演示的预约已顺延到明天 13:00；"
            "如需现场演示签到，请在白天重新运行 --reset。"
        )
    print("演示账号：")
    print("  student   / student123  （主演示学生，1 次违约）")
    print("  demo_li   / demo1234    （有投诉与场地关闭影响）")
    print("  demo_wang / demo1234    （3 次违约，账户已受限）")
    print("  demo_zhao / demo1234    （有“使用中”预约，用于手动违约演示）")
    print("  demo_sun  / demo1234    （手动黑名单）")
    print("重置命令：python -m scripts.seed_demo_data --reset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
