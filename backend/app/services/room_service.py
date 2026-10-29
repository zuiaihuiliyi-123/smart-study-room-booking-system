from sqlalchemy.orm import Session

from app.models.room import Area, Room
from app.schemas.room import AreaCreate, RoomCreate


def list_rooms(db: Session) -> list[Room]:
    """M1 / FR-001：查询自习室列表。TODO 分页、启用状态过滤。"""
    raise NotImplementedError("自习室列表查询待实现")


def create_room(db: Session, payload: RoomCreate) -> Room:
    """M1 / FR-001：管理员新建自习室。"""
    raise NotImplementedError("自习室创建待实现")


def create_area(db: Session, room_id: int, payload: AreaCreate) -> Area:
    """M1 / FR-001：管理员在自习室内新建区域。"""
    raise NotImplementedError("区域创建待实现")
