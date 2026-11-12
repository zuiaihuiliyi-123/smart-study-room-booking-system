"""预约服务兼容门面。

实现已拆分为：
- ``reservation_query_service``：只读查询；
- ``reservation_command_service``：写命令与事务边界。

保留本模块的公开函数名，API、任务与测试无需改动。
"""

from app.services.reservation_command_service import (
    _ensure_same_payload,
    _find_by_idempotency_key,
    cancel_my_reservation,
    create_reservation,
    force_cancel,
    release_slots,
)
from app.services.reservation_query_service import (
    ACTIVE_STATUSES,
    VALID_STATUSES,
    count_my_reservations,
    get_reservation,
    list_all_reservations,
    list_my_reservations,
)

# 兼容拆分前的私有查询函数名（内部/测试可直接引用）。
_get_reservation = get_reservation

__all__ = [
    "ACTIVE_STATUSES",
    "VALID_STATUSES",
    "cancel_my_reservation",
    "count_my_reservations",
    "create_reservation",
    "force_cancel",
    "get_reservation",
    "list_all_reservations",
    "list_my_reservations",
    "release_slots",
]
