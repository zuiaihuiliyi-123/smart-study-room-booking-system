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
    occupied: int
    capacity: int
    rate: float
