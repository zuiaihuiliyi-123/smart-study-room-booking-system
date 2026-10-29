from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.room import Room
from app.models.user import User
from app.schemas.room import AreaCreate, AreaRead, RoomCreate, RoomRead
from app.services import room_service

router = APIRouter(prefix="/rooms", tags=["M1 座位资源"])


@router.get("", response_model=list[RoomRead], summary="自习室列表")
def list_rooms(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Room]:
    return room_service.list_rooms(db)


@router.post(
    "",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    summary="新建自习室（管理员）",
)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Room:
    return room_service.create_room(db, payload)


@router.post(
    "/{room_id}/areas",
    response_model=AreaRead,
    status_code=status.HTTP_201_CREATED,
    summary="新建区域（管理员）",
)
def create_area(
    room_id: int,
    payload: AreaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return room_service.create_area(db, room_id, payload)
