from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.room import Area, Room
from app.schemas.room import AreaCreate, RoomCreate


def _parse_time(value: str, field: str) -> time:
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise BusinessError(
            f"{field}格式应为 HH:MM", code="VALIDATION_ERROR", status_code=422
        ) from exc
    return parsed


def list_rooms(db: Session) -> list[Room]:
    """M1 / FR-001：查询自习室列表。"""
    return list(db.scalars(select(Room).order_by(Room.id)).all())


def create_room(db: Session, payload: RoomCreate) -> Room:
    """M1 / FR-001：管理员新建自习室。"""
    open_time = _parse_time(payload.open_time, "开放时间")
    close_time = _parse_time(payload.close_time, "关闭时间")
    if close_time <= open_time:
        raise BusinessError(
            "关闭时间必须晚于开放时间", code="VALIDATION_ERROR", status_code=422
        )

    exists = db.scalar(select(Room).where(Room.name == payload.name.strip()))
    if exists is not None:
        raise BusinessError(
            "自习室名称已存在", code="ROOM_NAME_DUPLICATED", status_code=409
        )

    room = Room(
        name=payload.name.strip(),
        location=payload.location.strip(),
        open_time=open_time.strftime("%H:%M"),
        close_time=close_time.strftime("%H:%M"),
        capacity=payload.capacity,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def create_area(db: Session, room_id: int, payload: AreaCreate) -> Area:
    """M1 / FR-001：管理员在自习室内新建区域。"""
    room = db.get(Room, room_id)
    if room is None:
        raise BusinessError("自习室不存在", code="ROOM_NOT_FOUND", status_code=404)

    exists = db.scalar(
        select(Area).where(Area.room_id == room_id, Area.name == payload.name.strip())
    )
    if exists is not None:
        raise BusinessError(
            "该自习室内区域名称已存在", code="AREA_NAME_DUPLICATED", status_code=409
        )

    area = Area(room_id=room_id, name=payload.name.strip())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area
