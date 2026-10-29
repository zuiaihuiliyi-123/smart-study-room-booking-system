from datetime import date, time

from sqlalchemy.orm import Session

from app.models.seat import Seat


def list_available_seats(
    db: Session,
    room_id: int,
    reserve_date: date,
    start_time: time,
    end_time: time,
) -> list[Seat]:
    """M2 / FR-013：查询某时段可预约的座位。

    判定项 C1～C6（§10.4.2）：
    C1 座位资源状态为“可用”；
    C2 自习室启用且时段位于开放时间内；
    C3 该座位无重叠的有效预约（[s, e)）；
    C4 当前用户无重叠的有效预约；
    C5 账户状态为“正常”；
    C6 满足粒度、提前天数、单次时长、每日次数限制。
    """
    raise NotImplementedError("可预约座位查询待实现")


def check_reservation_rules(
    db: Session,
    *,
    user_id: int,
    seat_id: int,
    reserve_date: date,
    start_time: time,
    end_time: time,
) -> None:
    """M2 / FR-012：校验 C1～C6；失败时抛出带具体判定项的业务异常。"""
    raise NotImplementedError("预约规则校验待实现")
