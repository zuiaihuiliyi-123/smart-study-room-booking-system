"""预约状态流转的原子写。

状态流转（签到/签退/取消/强制取消）采用带 ``WHERE status = 期望值`` 的条件更新：
- 只有一个并发请求能命中该行，其余请求 ``rowcount == 0``；
- 调用方据此返回 409，而不是覆盖已变化的终态，避免出现
  「使用中 + cancel_time」这类矛盾数据。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.reservation import Reservation


def transition_if_status(
    db: Session,
    reservation_id: int,
    expected_status: str,
    **values: Any,
) -> bool:
    """仅当预约当前状态等于 ``expected_status`` 时写入 ``values``。

    返回是否命中并更新。本函数不提交事务，由调用方统一提交/回滚。
    """
    result = db.execute(
        update(Reservation)
        .where(
            Reservation.id == reservation_id,
            Reservation.status == expected_status,
        )
        .values(**values)
    )
    return bool(result.rowcount)
