from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.room import Area, Room
from app.models.user import User
from app.schemas.room import (
    AreaCreate,
    AreaRead,
    ConflictPreview,
    RoomClosureRead,
    RoomCloseRequest,
    RoomCloseResult,
    RoomCreate,
    RoomRead,
    RoomUpdate,
)
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


@router.patch(
    "/{room_id}",
    response_model=RoomRead,
    summary="修改自习室（管理员）",
)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Room:
    return room_service.update_room(db, room_id, payload, admin.id)


@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除自习室（管理员，仅限无预约历史）",
)
def delete_room(
    room_id: int,
    reason: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    room_service.delete_room(db, room_id, reason, admin.id)


@router.get(
    "/{room_id}/areas",
    response_model=list[AreaRead],
    summary="分区列表",
)
def list_areas(
    room_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Area]:
    return room_service.list_areas(db, room_id)


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


@router.get(
    "/{room_id}/close-preview",
    response_model=ConflictPreview,
    summary="临时关闭影响清单（管理员）",
)
def preview_room_close(
    room_id: int,
    start_at: datetime,
    end_at: datetime,
    area_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ConflictPreview:
    seats, reservations = room_service.preview_close(
        db, room_id, start_at, end_at, area_id
    )
    return ConflictPreview(seats=seats, reservations=reservations)


@router.post(
    "/{room_id}/close",
    response_model=RoomCloseResult,
    summary="临时关闭场地（管理员）",
)
def close_room(
    room_id: int,
    payload: RoomCloseRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> RoomCloseResult:
    return room_service.close_room(db, room_id, payload, admin.id)


@router.get(
    "/{room_id}/closures",
    response_model=list[RoomClosureRead],
    summary="临时关闭记录（未结束的）",
)
def list_closures(
    room_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    """学生端也要用：座位图按当前时段把这些座位标为「临时关闭」。"""
    return room_service.list_closures(db, room_id)


@router.delete(
    "/{room_id}/closures/{closure_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="提前解除临时关闭（管理员）",
)
def release_closure(
    room_id: int,
    closure_id: int,
    reason: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    room_service.release_closure(db, room_id, closure_id, reason, admin.id)
