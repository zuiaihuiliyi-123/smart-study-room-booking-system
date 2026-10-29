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
