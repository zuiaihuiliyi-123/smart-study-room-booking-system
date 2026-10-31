from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.message import StationMessage
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.message import MessageRead, UnreadCount
from app.services import message_service

router = APIRouter(prefix="/messages", tags=["M7 站内通知"])


@router.get("/me", response_model=PageResult[MessageRead], summary="本人站内通知")
def list_my_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResult[MessageRead]:
    return message_service.list_my_messages(db, current_user.id, page, page_size)


@router.get("/unread-count", response_model=UnreadCount, summary="本人未读通知数")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCount:
    return UnreadCount(count=message_service.unread_count(db, current_user.id))


@router.post("/{message_id}/read", response_model=MessageRead, summary="标记已读")
def mark_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StationMessage:
    return message_service.mark_read(db, current_user.id, message_id)
