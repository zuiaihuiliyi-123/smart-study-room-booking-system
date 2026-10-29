from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services import attendance_service

router = APIRouter(prefix="/reservations", tags=["M3 签到与签退"])


@router.post("/{reservation_id}/check-in", response_model=MessageResponse, summary="签到")
def check_in(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    attendance_service.check_in(db, current_user.id, reservation_id)
    return MessageResponse(message="签到成功")


@router.post("/{reservation_id}/check-out", response_model=MessageResponse, summary="签退")
def check_out(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    attendance_service.check_out(db, current_user.id, reservation_id)
    return MessageResponse(message="签退成功")
