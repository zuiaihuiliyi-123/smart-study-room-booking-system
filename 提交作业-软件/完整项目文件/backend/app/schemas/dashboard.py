from datetime import date

from pydantic import BaseModel


class StatOverview(BaseModel):
    seat_total: int
    in_use: int
    today_reservations: int
    today_violations: int
    restricted_accounts: int


class ChartItem(BaseModel):
    name: str
    value: float


class TrendPoint(BaseModel):
    date: date
    reservations: int
    violations: int


class SeatUsageSlotRow(BaseModel):
    """图 1：某自习室在某时段桶内的座位占用率。"""

    room_id: int
    room_name: str
    slot: str
    #: 折算成 30 分钟统计块的占用数；5 分钟预约会产生 .5 等小数
    occupied: float
    capacity: int
    rate: float


class ViolationTopItem(BaseModel):
    """图 3：某用户在一个统计区间内的违约次数（后端聚合）。"""

    user_id: int
    name: str
    student_no: str
    count: int


class ViolationTopResponse(BaseModel):
    """图 3 的聚合结果：Top N 用户 + 区间内违约记录总数。"""

    items: list[ViolationTopItem]
    total_records: int
