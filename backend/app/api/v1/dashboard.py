from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.exceptions import BusinessError
from app.models.user import User
from app.schemas.dashboard import (
    ChartItem,
    SeatUsageSlotRow,
    StatOverview,
    TrendPoint,
    ViolationTopResponse,
)
from app.services import dashboard_service
from app.utils import time_utils

router = APIRouter(prefix="/dashboard", tags=["M6 数据分析"])

MAX_RANGE_DAYS = 31


def _validate_range(start_date: date, end_date: date) -> None:
    days = (end_date - start_date).days
    if days < 0:
        raise BusinessError(
            "结束日期不能早于开始日期", code="INVALID_ARGUMENT", status_code=422
        )
    if days > MAX_RANGE_DAYS:
        raise BusinessError(
            f"统计区间不能超过 {MAX_RANGE_DAYS} 天",
            code="INVALID_ARGUMENT",
            status_code=422,
        )


@router.get("/overview", response_model=StatOverview, summary="统计概览")
def overview(
    room_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> StatOverview:
    """统计概览：5～10 秒服务端短缓存，降低 10 秒轮询的数据库 QPS。"""
    key = (id(db.get_bind()), room_id, time_utils.now().date())
    cached = dashboard_cache.get(key)
    if isinstance(cached, StatOverview):
        return cached
    result = dashboard_service.get_overview(db, room_id)
    dashboard_cache.set(key, result)
    return result


@router.get(
    "/seat-usage",
    response_model=list[SeatUsageSlotRow] | list[ChartItem],
    summary="座位使用柱状图",
)
def seat_usage(
    start_date: date,
    end_date: date,
    room_id: int | None = None,
    group_by: str = Query("seat", pattern="^(seat|slot)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[SeatUsageSlotRow] | list[ChartItem]:
    _validate_range(start_date, end_date)
    if group_by == "slot":
        return dashboard_service.get_seat_usage_by_slot(
            db, start_date, end_date, room_id
        )
    return dashboard_service.get_seat_usage(db, start_date, end_date, room_id)


@router.get(
    "/violation-top",
    response_model=ViolationTopResponse,
    summary="用户违约次数 Top N（全站）",
)
def violation_top(
    start_date: date,
    end_date: date,
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ViolationTopResponse:
    """按用户聚合违约次数，供看板图 3 直接展示，不再由前端聚合明细。"""
    _validate_range(start_date, end_date)
    return dashboard_service.get_violation_top(db, start_date, end_date, limit)


@router.get("/trend", response_model=list[TrendPoint], summary="预约与违约趋势")
def trend(
    start_date: date,
    end_date: date,
    room_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TrendPoint]:
    _validate_range(start_date, end_date)
    return dashboard_service.get_trend(db, start_date, end_date, room_id)
