from datetime import date

from sqlalchemy.orm import Session

from app.schemas.dashboard import ChartItem, StatOverview, TrendPoint


def get_overview(db: Session) -> StatOverview:
    """M6 / FR-052：座位总数、使用中、今日预约、今日违约、受限账户数。"""
    raise NotImplementedError("数据概览统计待实现")


def get_seat_usage(
    db: Session, start_date: date, end_date: date
) -> list[ChartItem]:
    """M6 / FR-050：统计周期内各座位的被使用时段数（柱状图）。"""
    raise NotImplementedError("座位使用统计待实现")


def get_trend(
    db: Session, start_date: date, end_date: date
) -> list[TrendPoint]:
    """M6 / FR-051：按日统计有效预约数与违约数（折线图）。"""
    raise NotImplementedError("预约趋势统计待实现")
