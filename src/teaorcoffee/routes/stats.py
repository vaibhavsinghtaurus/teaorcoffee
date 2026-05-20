from fastapi import APIRouter, HTTPException, status

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.models.schema import (
    DailyTotals,
    StatsRangeResponse,
    UserOrderDetail,
    UserOrdersForDateResponse,
)

router = APIRouter(tags=["Stats"])

_MIN_DATE = "2026-01-01"


def _check_password(password: str):
    if password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")


@router.get("/stats/daily", response_model=StatsRangeResponse)
async def get_daily_stats(password: str, start: str, end: str):
    """Daily tea/coffee totals for a date range (min start: 2026-01-01)"""
    _check_password(password)

    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")

    rows = await db.get_daily_totals_range(start, end)
    return StatsRangeResponse(days=[DailyTotals(**r) for r in rows])


@router.get("/stats/users/day", response_model=UserOrdersForDateResponse)
async def get_user_stats_for_day(password: str, date: str):
    """Per-user order breakdown for a specific date (min: 2026-01-01)"""
    _check_password(password)

    if date < _MIN_DATE:
        raise HTTPException(status_code=400, detail=f"Date cannot be before {_MIN_DATE}")

    rows = await db.get_user_orders_for_date(date)
    orders = [UserOrderDetail(**r) for r in rows]
    return UserOrdersForDateResponse(
        date=date,
        orders=orders,
        total_tea=sum(o.tea for o in orders),
        total_coffee=sum(o.coffee for o in orders),
    )
