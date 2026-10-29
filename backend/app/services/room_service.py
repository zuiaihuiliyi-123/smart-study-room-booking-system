"""M1 座位资源：自习室与区域（FR-001）。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.room import Area, Room
from app.schemas.room import AreaCreate, RoomCreate


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
