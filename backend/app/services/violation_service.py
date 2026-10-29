from sqlalchemy.orm import Session

from app.models.user import User
from app.models.violation import ViolationRecord
from app.schemas.common import PageResult
from app.schemas.violation import ManualViolationCreate


def list_my_violations(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[ViolationRecord]:
    """M4 / FR-032：学生查询本人违约记录。"""
    raise NotImplementedError("个人违约记录查询待实现")


def list_all_violations(
    db: Session, page: int, page_size: int
) -> PageResult[ViolationRecord]:
    """M4 / FR-032：管理员查询全部违约记录。"""
    raise NotImplementedError("违约记录管理查询待实现")


def register_manual(
    db: Session, admin: User, payload: ManualViolationCreate
) -> ViolationRecord:
    """M3 / FR-023：管理员对“使用中”预约登记违约，必须填写原因。

    须与“强制取消”互斥；登记后累加违约次数，达到阈值触发账户受限。
    """
    raise NotImplementedError("手动违约登记待实现")


def apply_auto_violation(db: Session, reservation_id: int) -> ViolationRecord | None:
    """M3 / FR-022：自动违约登记（幂等，按预约单 + 类型去重）。"""
    raise NotImplementedError("自动违约登记待实现")
