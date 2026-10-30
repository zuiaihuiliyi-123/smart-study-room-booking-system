from datetime import date, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.room import Room
from app.models.seat import Seat
from app.models.user import User
from app.utils import time_utils

#: 「有效预约」= 待使用 / 使用中；已取消、已完成、已违约不占用时段（TM-18）
ACTIVE_STATUSES = (
    ReservationStatus.PENDING.value,
    ReservationStatus.IN_USE.value,
)


def _active_overlaps(
    db: Session,
    *,
    user_id: int | None = None,
    seat_id: int | None = None,
    reserve_date: date,
    start_time: time,
    end_time: time,
) -> list[Reservation]:
    """左闭右开重叠判定：s1 < e2 且 s2 < e1（BR-020）。"""
    stmt = select(Reservation).where(
        Reservation.status.in_(ACTIVE_STATUSES),
        Reservation.reserve_date == reserve_date,
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )
    if user_id is not None:
        stmt = stmt.where(Reservation.user_id == user_id)
    if seat_id is not None:
        stmt = stmt.where(Reservation.seat_id == seat_id)
    return list(db.scalars(stmt.order_by(Reservation.start_time)).all())


def _parse_room_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:  # 防御：脏数据不应导致 500
        raise BusinessError(
            f"自习室开放时间配置不合法：{value}",
            code="ROOM_TIME_INVALID",
            status_code=500,
        ) from exc


def _details(
    condition: str, rule: str, params: dict | None = None
) -> dict:
    detail: dict = {"condition": condition, "rule": rule}
    if params:
        detail["params"] = params
    return detail


def _validate_interval(
    reserve_date: date,
    start_time: time,
    end_time: time,
    now,
) -> tuple[bool, dict | None]:
    """C6 的参数类校验；返回 (是否通过, 未通过明细)。

    顺序：区间合法性 → 粒度 → 时长 → 提前天数 → 是否已过开始时间。
    """
    granularity = settings.reservation_granularity_minutes

    if end_time <= start_time:
        return False, _details(
            "C6",
            "BR-020",
            {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
        )

    if not (
        time_utils.is_aligned(start_time, granularity)
        and time_utils.is_aligned(end_time, granularity)
    ):
        return False, _details(
            "C6", "BR-001", {"granularity_minutes": granularity}
        )

    length = time_utils.duration(reserve_date, start_time, end_time)
    if length > timedelta(hours=settings.max_reservation_hours):
        return False, _details(
            "C6",
            "BR-003",
            {
                "max_hours": settings.max_reservation_hours,
                "requested_hours": length.total_seconds() / 3600,
            },
        )

    today = now.date()
    latest = today + timedelta(days=settings.advance_booking_days)
    if reserve_date < today or reserve_date > latest:
        return False, _details(
            "C6",
            "BR-002",
            {
                "advance_days": settings.advance_booking_days,
                "allowed_from": today.isoformat(),
                "allowed_to": latest.isoformat(),
                "requested_date": reserve_date.isoformat(),
            },
        )

    if time_utils.start_at(reserve_date, start_time) <= now:
        return False, _details(
            "C6", "BR-002", {"reason": "开始时间必须晚于当前时间"}
        )

    return True, None


_RULE_MESSAGES = {
    "BR-020": "结束时间必须晚于开始时间，且一次预约不得跨日（TB-11）",
    "BR-001": f"预约时间须按 {settings.reservation_granularity_minutes} 分钟粒度对齐，"
    "系统不做自动取整",
    "BR-003": f"单次预约时长不得超过 {settings.max_reservation_hours} 小时",
    "BR-002": f"只能预约今天起未来 {settings.advance_booking_days} 天内的时段",
}


def check_reservation_rules(
    db: Session,
    *,
    user_id: int,
    seat_id: int,
    reserve_date: date,
    start_time: time,
    end_time: time,
    now=None,
) -> None:
    """M2 / FR-012：按 C1～C6 校验；失败时抛出带具体判定项的业务异常。

    拒绝顺序遵循 AD-01：C5 账户 → C1/C2 资源 → C6 规则 → C3/C4 冲突。
    """
    now = now or time_utils.now()

    valid, detail = _validate_interval(reserve_date, start_time, end_time, now)
    if not valid:
        rule = (detail or {}).get("rule", "BR-020")
        raise BusinessError(
            _RULE_MESSAGES.get(rule, "预约时段不合法"),
            code=f"C6_{rule}",
            status_code=422,
            details=detail,
        )

    # C5 用户资格
    user = db.get(User, user_id)
    if user is None:
        raise BusinessError("用户不存在", code="USER_NOT_FOUND", status_code=404)
    if user.account_status != AccountStatus.NORMAL.value:
        entry = db.scalar(
            select(BlacklistEntry)
            .where(
                BlacklistEntry.user_id == user_id,
                BlacklistEntry.released_at.is_(None),
            )
            .order_by(BlacklistEntry.id.desc())
        )
        params = {
            "account_status": user.account_status,
            "violation_count": user.violation_count,
        }
        if entry is not None:
            params["reason"] = entry.reason
            params["limit_until"] = (
                entry.expire_at.isoformat() if entry.expire_at else None
            )
        message = (
            "账户当前为「受限」，暂不能创建预约"
            if user.account_status == AccountStatus.RESTRICTED.value
            else "账户已停用，不能创建预约"
        )
        raise BusinessError(
            message,
            code="ST-047",
            status_code=403,
            details=_details("C5", "ST-047", params),
        )

    # C1 座位资源状态
    seat = db.get(Seat, seat_id)
    if seat is None:
        raise BusinessError("座位不存在", code="SEAT_NOT_FOUND", status_code=404)
    if seat.status != SeatStatus.AVAILABLE.value:
        raise BusinessError(
            f"座位当前为「{seat.status}」，不可预约",
            code="C1_BR-017",
            status_code=409,
            details=_details(
                "C1", "BR-017", {"seat_id": seat.id, "seat_status": seat.status}
            ),
        )

    # C2 自习室启用 + 开放时间
    room = db.get(Room, seat.room_id)
    if room is None or not room.enabled:
        raise BusinessError(
            "所属自习室已停用，不可预约",
            code="C2",
            status_code=409,
            details=_details("C2", "BR-017", {"room_id": seat.room_id}),
        )
    open_time = _parse_room_time(room.open_time)
    close_time = _parse_room_time(room.close_time)
    if not (open_time <= start_time and end_time <= close_time):
        raise BusinessError(
            "预约时段超出自习室开放时间",
            code="C2",
            status_code=409,
            details=_details(
                "C2",
                "BR-017",
                {
                    "open_time": room.open_time,
                    "close_time": room.close_time,
                },
            ),
        )

    # C6 每日次数上限
    daily_count = (
        db.scalar(
            select(func.count())
            .select_from(Reservation)
            .where(
                Reservation.user_id == user_id,
                Reservation.reserve_date == reserve_date,
                Reservation.status.in_(ACTIVE_STATUSES),
            )
        )
        or 0
    )
    if daily_count >= settings.daily_reservation_limit:
        raise BusinessError(
            f"已超出每日预约次数上限（{settings.daily_reservation_limit} 条/日）",
            code="C6_BR-004",
            status_code=422,
            details=_details(
                "C6",
                "BR-004",
                {
                    "max_per_day": settings.daily_reservation_limit,
                    "current_count": daily_count,
                },
            ),
        )

    # C3 座位时段独占
    seat_conflicts = _active_overlaps(
        db,
        seat_id=seat_id,
        reserve_date=reserve_date,
        start_time=start_time,
        end_time=end_time,
    )
    if seat_conflicts:
        raise BusinessError(
            "该座位在所选时段已被占用",
            code="C3_BR-006",
            status_code=409,
            details=_details(
                "C3",
                "BR-006",
                {
                    "conflicts": [
                        {
                            "reservation_id": item.id,
                            "start_time": item.start_time.isoformat(),
                            "end_time": item.end_time.isoformat(),
                        }
                        for item in seat_conflicts
                    ]
                },
            ),
        )

    # C4 用户时段不重叠
    user_conflicts = _active_overlaps(
        db,
        user_id=user_id,
        reserve_date=reserve_date,
        start_time=start_time,
        end_time=end_time,
    )
    if user_conflicts:
        raise BusinessError(
            "你在该时段已有其他有效预约",
            code="C4_BR-005",
            status_code=409,
            details=_details(
                "C4",
                "BR-005",
                {
                    "conflicts": [
                        {
                            "reservation_id": item.id,
                            "start_time": item.start_time.isoformat(),
                            "end_time": item.end_time.isoformat(),
                        }
                        for item in user_conflicts
                    ]
                },
            ),
        )


def list_available_seats(
    db: Session,
    room_id: int,
    reserve_date: date,
    start_time: time,
    end_time: time,
    *,
    user_id: int,
) -> list[Seat]:
    """M2 / FR-013：查询某时段可预约的座位。

    只读查询，按 C1（资源状态）、C3（座位占用）、C4（本人冲突）过滤；
    C5/C6 在创建预约时强制校验。返回的座位**不包含**“已预约/使用中”状态，
    座位资源状态始终保持原值（第 10.0 节 MD-01）。
    """
    if end_time <= start_time:
        raise BusinessError(
            "结束时间必须晚于开始时间，且一次预约不得跨日",
            code="C6_BR-020",
            status_code=422,
        )

    room = db.get(Room, room_id)
    if room is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)
    if not room.enabled:
        raise BusinessError(
            "该自习室已停用，当前不可预约",
            code="C2",
            status_code=409,
        )
    open_time = _parse_room_time(room.open_time)
    close_time = _parse_room_time(room.close_time)
    if not (open_time <= start_time and end_time <= close_time):
        raise BusinessError(
            "查询时段超出自习室开放时间",
            code="C2",
            status_code=409,
            details=_details(
                "C2",
                "BR-017",
                {"open_time": room.open_time, "close_time": room.close_time},
            ),
        )

    seats = list(
        db.scalars(
            select(Seat)
            .where(
                Seat.room_id == room_id,
                Seat.status == SeatStatus.AVAILABLE.value,
            )
            .order_by(Seat.seat_no)
        ).all()
    )

    occupied_seat_ids = {
        item.seat_id
        for item in _active_overlaps(
            db,
            reserve_date=reserve_date,
            start_time=start_time,
            end_time=end_time,
        )
    }

    # C4：当前用户在该时段已有有效预约时，任何座位都会与其冲突
    user_conflict = bool(
        _active_overlaps(
            db,
            user_id=user_id,
            reserve_date=reserve_date,
            start_time=start_time,
            end_time=end_time,
        )
    )
    if user_conflict:
        return []

    return [seat for seat in seats if seat.id not in occupied_seat_ids]
