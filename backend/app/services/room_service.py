"""M1 座位资源：自习室与区域（FR-001）。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.enums import MessageType, ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.room import Area, Room, RoomClosure
from app.models.seat import Seat
from app.models.user import User
from app.schemas.room import (
    AreaCreate,
    RoomCloseRequest,
    RoomCloseResult,
    RoomCreate,
    RoomUpdate,
)
from app.services import audit_service, notification_service, reservation_service


def _parse_hhmm(value: str, field_name: str) -> datetime:
    """校验 HH:MM 格式，返回可比较的 datetime（仅用时分）。"""
    try:
        return datetime.strptime(value, "%H:%M")
    except ValueError:
        raise BusinessError(
            f"{field_name} 必须为 HH:MM 格式",
            code="ROOM_TIME_FORMAT_INVALID",
            status_code=422,
        ) from None


def list_rooms(db: Session) -> list[Room]:
    """M1 / FR-001：查询自习室列表（按 id 升序，含停用的自习室，供管理员查看）。"""
    return list(db.scalars(select(Room).order_by(Room.id)))


def create_room(db: Session, payload: RoomCreate) -> Room:
    """M1 / FR-001：管理员新建自习室。

    - 开放/关闭时间须为 HH:MM 且开放时间早于关闭时间；
    - 自习室名称唯一（DR-002）。
    """
    open_at = _parse_hhmm(payload.open_time, "开放时间")
    close_at = _parse_hhmm(payload.close_time, "关闭时间")
    if open_at >= close_at:
        raise BusinessError(
            "开放时间必须早于关闭时间",
            code="ROOM_TIME_RANGE_INVALID",
            status_code=422,
        )

    if db.scalar(select(Room).where(Room.name == payload.name)) is not None:
        raise BusinessError(
            "自习室名称已存在", code="ROOM_NAME_DUPLICATED", status_code=409
        )

    room = Room(
        name=payload.name,
        location=payload.location,
        open_time=payload.open_time,
        close_time=payload.close_time,
        capacity=payload.capacity,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def create_area(db: Session, room_id: int, payload: AreaCreate) -> Area:
    """M1 / FR-001：管理员在自习室内新建区域（同室内名称唯一）。"""
    if db.get(Room, room_id) is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)

    duplicated = db.scalar(
        select(Area).where(Area.room_id == room_id, Area.name == payload.name)
    )
    if duplicated is not None:
        raise BusinessError(
            "该自习室内已存在同名区域",
            code="AREA_NAME_DUPLICATED",
            status_code=409,
        )

    area = Area(room_id=room_id, name=payload.name)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def update_room(
    db: Session, room_id: int, payload: RoomUpdate, operator_id: int
) -> Room:
    """M1 / FR-001：管理员修改自习室属性，关键变更写入审计。"""
    room = db.get(Room, room_id)
    if room is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)

    before = {
        "name": room.name,
        "location": room.location,
        "open_time": room.open_time,
        "close_time": room.close_time,
        "capacity": room.capacity,
        "enabled": room.enabled,
    }

    if payload.name is not None and payload.name != room.name:
        if db.scalar(
            select(Room).where(Room.name == payload.name, Room.id != room_id)
        ):
            raise BusinessError(
                "自习室名称已存在", code="ROOM_NAME_DUPLICATED", status_code=409
            )
        room.name = payload.name
    if payload.location is not None:
        room.location = payload.location
    if payload.open_time is not None:
        room.open_time = payload.open_time
    if payload.close_time is not None:
        room.close_time = payload.close_time
    if payload.capacity is not None:
        room.capacity = payload.capacity
    if payload.enabled is not None:
        room.enabled = payload.enabled

    if room.open_time >= room.close_time:
        raise BusinessError(
            "开放时间必须早于关闭时间", code="ROOM_TIME_RANGE_INVALID", status_code=422
        )

    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="ROOM_UPDATE",
        target_type="ROOM",
        target_id=room.id,
        reason=payload.reason,
        before_value=str(before),
        after_value=str(
            {
                "name": room.name,
                "location": room.location,
                "open_time": room.open_time,
                "close_time": room.close_time,
                "capacity": room.capacity,
                "enabled": room.enabled,
            }
        ),
    )
    db.commit()
    db.refresh(room)
    return room


def delete_room(db: Session, room_id: int, reason: str, operator_id: int) -> None:
    """M1 / FR-001：删除自习室（仅限没有任何预约历史的自习室）。

    预约记录是审计与统计的依据（DR-002 / NFR-009），因此只要该馆的座位产生过预约，
    就不再允许物理删除，只能停用——停用后不再出现在可预约范围，历史数据仍可追溯。
    """
    text = reason.strip()
    if not text:
        raise BusinessError("请填写删除原因", code="REASON_REQUIRED", status_code=422)

    room = db.get(Room, room_id)
    if room is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)

    seats = list(db.scalars(select(Seat).where(Seat.room_id == room_id)).all())
    seat_ids = [seat.id for seat in seats]
    if seat_ids:
        history = db.scalar(
            select(Reservation.id).where(Reservation.seat_id.in_(seat_ids)).limit(1)
        )
        if history is not None:
            raise BusinessError(
                "该自习室已有预约记录，不能删除，请改为停用",
                code="ROOM_HAS_HISTORY",
                status_code=409,
            )
        # 取消后释放时段也可能留下时段占位记录，同样视为历史
        leftover = db.scalar(
            select(ReservationSlot.id)
            .where(ReservationSlot.seat_id.in_(seat_ids))
            .limit(1)
        )
        if leftover is not None:
            raise BusinessError(
                "该自习室已有预约记录，不能删除，请改为停用",
                code="ROOM_HAS_HISTORY",
                status_code=409,
            )

    areas = list(db.scalars(select(Area).where(Area.room_id == room_id)).all())
    # 先删子表再删父表，并逐段 flush，避免外键在同一个事务里仍在引用
    for seat in seats:
        db.delete(seat)
    db.flush()
    for area in areas:
        db.delete(area)
    db.flush()

    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="ROOM_DELETE",
        target_type="ROOM",
        target_id=room.id,
        reason=text,
        before_value=str(
            {
                "name": room.name,
                "location": room.location,
                "area_count": len(areas),
                "seat_count": len(seats),
            }
        ),
        after_value=str({"deleted": True}),
    )
    db.delete(room)
    db.commit()


def list_areas(db: Session, room_id: int) -> list[Area]:
    if db.get(Room, room_id) is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)
    return list(
        db.scalars(
            select(Area).where(Area.room_id == room_id).order_by(Area.id)
        ).all()
    )


def _affected(
    db: Session,
    room_id: int,
    area_id: int | None,
    start_at: datetime,
    end_at: datetime,
) -> tuple[list[Seat], list[Reservation]]:
    """返回窗口内受影响的座位与「待使用 / 使用中」预约（BR-019 / BR-022）。"""
    seat_stmt = select(Seat).where(Seat.room_id == room_id)
    if area_id is not None:
        seat_stmt = seat_stmt.where(Seat.area_id == area_id)
    seats = list(db.scalars(seat_stmt.order_by(Seat.seat_no)).all())
    seat_ids = {seat.id for seat in seats}
    if not seat_ids:
        return [], []

    records = list(
        db.scalars(
            select(Reservation)
            .where(
                Reservation.seat_id.in_(seat_ids),
                Reservation.status.in_(
                    (ReservationStatus.PENDING.value, ReservationStatus.IN_USE.value)
                ),
                Reservation.reserve_date >= start_at.date(),
                Reservation.reserve_date <= end_at.date(),
            )
            .order_by(Reservation.reserve_date, Reservation.start_time)
        ).all()
    )
    affected = [
        record
        for record in records
        if datetime.combine(record.reserve_date, record.start_time) < end_at
        and start_at < datetime.combine(record.reserve_date, record.end_time)
    ]
    return seats, affected


def preview_close(
    db: Session,
    room_id: int,
    start_at: datetime,
    end_at: datetime,
    area_id: int | None,
) -> tuple[list[Seat], list[Reservation]]:
    """BR-022 第一步：只读查询受影响清单，不产生任何数据变化。"""
    if db.get(Room, room_id) is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)
    if start_at >= end_at:
        raise BusinessError(
            "关闭窗口不合法：结束时间必须晚于开始时间",
            code="INVALID_ARGUMENT",
            status_code=422,
        )
    if area_id is not None:
        area = db.get(Area, area_id)
        if area is None or area.room_id != room_id:
            raise BusinessError(
                "分区不存在或不属于该自习室", code="AREA_NOT_IN_ROOM", status_code=404
            )
    return _affected(db, room_id, area_id, start_at, end_at)


def close_room(
    db: Session,
    room_id: int,
    payload: RoomCloseRequest,
    operator_id: int,
) -> RoomCloseResult:
    """BR-022 第二步：关闭座位；默认保留冲突预约，仅显式选择时批量取消。"""
    reason = payload.reason.strip()
    if not reason:
        raise BusinessError(
            "请填写关闭原因", code="REASON_REQUIRED", status_code=422
        )

    room = db.get(Room, room_id)
    if room is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)
    if payload.start_at >= payload.end_at:
        raise BusinessError(
            "关闭窗口不合法：结束时间必须晚于开始时间",
            code="INVALID_ARGUMENT",
            status_code=422,
        )
    if payload.area_id is not None:
        area = db.get(Area, payload.area_id)
        if area is None or area.room_id != room_id:
            raise BusinessError(
                "分区不存在或不属于该自习室",
                code="AREA_NOT_IN_ROOM",
                status_code=404,
            )
    seats, affected = _affected(
        db, room_id, payload.area_id, payload.start_at, payload.end_at
    )

    actual_ids = sorted(record.id for record in affected)
    if sorted(payload.expected_reservation_ids) != actual_ids:
        raise BusinessError(
            "影响清单已变化，请重新查询受影响预约后再确认",
            code="CONFLICT_LIST_CHANGED",
            status_code=409,
        )

    now = datetime.now()
    closure = RoomClosure(
        room_id=room.id,
        area_id=payload.area_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        reason=reason,
        operator_id=operator_id,
    )
    db.add(closure)

    cancelled = 0
    messages: list[dict] = []
    for record in affected:
        if payload.cancel_affected:
            record.status = ReservationStatus.CANCELLED.value
            record.cancel_time = now
            record.cancel_reason = f"场地临时关闭：{reason}"
            record.cancelled_by_id = operator_id
            reservation_service.release_slots(db, record.id)
            cancelled += 1
            messages.append(
                dict(
                    user_id=record.user_id,
                    message_type=MessageType.RESERVATION,
                    title="预约已被取消（场地临时关闭）",
                    content=(
                        f"因{room.name}场地临时关闭（原因：{reason}），"
                        f"你 {record.reserve_date} 的预约已被取消，该情形不计违约。"
                    ),
                    related_type="预约单",
                    related_id=record.id,
                )
            )
        else:
            messages.append(
                dict(
                    user_id=record.user_id,
                    message_type=MessageType.SYSTEM,
                    title="所选座位临时关闭",
                    content=(
                        f"{room.name} {record.reserve_date} 的场地临时关闭"
                        f"（原因：{reason}），你的预约暂时保留，请留意后续通知。"
                    ),
                    related_type="预约单",
                    related_id=record.id,
                )
            )

    # 关闭只生成时间窗记录，座位资源状态保持不变；窗口结束后自动失效，
    # 因此不再需要「窗口外孤儿预约」的停用提示。
    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="ROOM_TEMP_CLOSE",
        target_type="ROOM",
        target_id=room.id,
        reason=reason,
        before_value=str({"affected": actual_ids}),
        after_value=str(
            {
                "closure_id": None,
                "closed_seats": len(seats),
                "cancelled": cancelled,
                "kept": len(affected) - cancelled,
                "window": [payload.start_at.isoformat(), payload.end_at.isoformat()],
                "scope": "AREA" if payload.area_id else "ROOM",
            }
        ),
    )
    db.commit()
    db.refresh(closure)

    for message in messages:
        notification_service.notify_safe(**message)

    return RoomCloseResult(
        closed_seats=len(seats),
        cancelled=cancelled,
        kept=len(affected) - cancelled,
        notified_outside_window=0,
    )


def list_closures(db: Session, room_id: int) -> list[RoomClosure]:
    """列出该自习室「尚未结束」的临时关闭记录（含未来时段），按开始时间升序。"""
    if db.get(Room, room_id) is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)
    stmt = (
        select(RoomClosure)
        .where(RoomClosure.room_id == room_id, RoomClosure.end_at > datetime.now())
        .order_by(RoomClosure.start_at)
    )
    return list(db.scalars(stmt))


def release_closure(
    db: Session, room_id: int, closure_id: int, reason: str, operator_id: int
) -> None:
    """提前解除一条临时关闭记录。"""
    text = (reason or "").strip()
    if not text:
        raise BusinessError("请填写解除原因", code="REASON_REQUIRED", status_code=422)

    closure = db.get(RoomClosure, closure_id)
    if closure is None or closure.room_id != room_id:
        raise BusinessError(
            "关闭记录不存在", code="CLOSURE_NOT_FOUND", status_code=404
        )

    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="ROOM_CLOSURE_RELEASE",
        target_type="ROOM",
        target_id=room_id,
        reason=text,
        before_value=str(
            {
                "closure_id": closure.id,
                "area_id": closure.area_id,
                "window": [closure.start_at.isoformat(), closure.end_at.isoformat()],
            }
        ),
        after_value=str({"released": True}),
    )
    db.delete(closure)
    db.commit()


def active_closures(
    db: Session, room_id: int, start_at: datetime, end_at: datetime
) -> list[RoomClosure]:
    """返回与给定时间窗重叠的关闭记录（供预约校验与座位图使用）。"""
    stmt = (
        select(RoomClosure)
        .where(
            RoomClosure.room_id == room_id,
            RoomClosure.start_at < end_at,
            RoomClosure.end_at > start_at,
        )
        .order_by(RoomClosure.start_at)
    )
    return list(db.scalars(stmt))
