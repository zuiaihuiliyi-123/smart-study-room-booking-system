from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReservationSlot(Base):
    """预约占用槽位（实现层辅助表，NFR-011 / BR-005 / BR-006）。

    每 30 分钟一行，把预约区间 [s, e) 物化为可被数据库唯一约束检查的行：

    - ``(seat_id, slot_start)``：同一座位同一时段至多一条有效预约（BR-006）
    - ``(user_id, slot_start)``：同一用户同一时段至多一条有效预约（BR-005）

    预约进入终态（取消 / 违约 / 完成）时删除对应行即可释放时段，无需回写座位状态
    （第 10.0 节 MD-02、LK-03）。该表不对前端暴露。
    """

    __tablename__ = "reservation_slots"
    __table_args__ = (
        UniqueConstraint("seat_id", "slot_start", name="uq_slot_seat_start"),
        UniqueConstraint("user_id", "slot_start", name="uq_slot_user_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), index=True
    )
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    slot_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
