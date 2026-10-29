from sqlalchemy.orm import Session

from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.reservation import (
    CancelRequest,
    ForceCancelRequest,
    ReservationCreate,
    ReservationRead,
)


def create_reservation(
    db: Session, user: User, payload: ReservationCreate
) -> Reservation:
    """M2 / FR-010：创建预约。

    流程：账户状态校验 → C1～C6 → 幂等键去重 → 事务内并发冲突控制 →
    创建“待使用”预约 → 站内通知。
    注意：不得修改座位资源状态（§10.0 MD-01）。
    """
    raise NotImplementedError("创建预约待实现")


def list_my_reservations(
    db: Session,
    user_id: int,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> PageResult[ReservationRead]:
    """M4 / FR-030：查询本人预约记录。"""
    raise NotImplementedError("个人预约记录查询待实现")


def list_all_reservations(
    db: Session,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> PageResult[ReservationRead]:
    """M4 / FR-031：管理员查询全部预约。"""
    raise NotImplementedError("预约记录管理查询待实现")


def cancel_my_reservation(
    db: Session,
    user_id: int,
    reservation_id: int,
    payload: CancelRequest,
) -> Reservation:
    """M2 / FR-011：用户在开始前 30 分钟无损取消。"""
    raise NotImplementedError("取消预约待实现")


def force_cancel(
    db: Session,
    admin_id: int,
    reservation_id: int,
    payload: ForceCancelRequest,
) -> Reservation:
    """M2 / FR-011：管理员强制取消“待使用”预约，必须记录原因并审计。"""
    raise NotImplementedError("管理员强制取消待实现")
