from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.dashboard import ChartItem, StatOverview, TrendPoint
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["M6 数据分析"])


@router.get("/overview", response_model=StatOverview, summary="统计概览")
def overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> StatOverview:
    return dashboard_service.get_overview(db)


@router.get("/seat-usage", response_model=list[ChartItem], summary="座位使用柱状图")
def seat_usage(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[ChartItem]:
    return dashboard_service.get_seat_usage(db, start_date, end_date)


@router.get("/trend", response_model=list[TrendPoint], summary="预约与违约趋势")
def trend(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TrendPoint]:
    return dashboard_service.get_trend(db, start_date, end_date)
