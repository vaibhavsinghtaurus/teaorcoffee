from fastapi import APIRouter, Depends, HTTPException

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    AuthUser,
    DailyTotals,
    StatsRangeResponse,
    UserNamesResponse,
    UserOrdersForDateResponse,
    UserStatsDayEntry,
    UserStatsResponse,
)

router = APIRouter(tags=["Stats"])

_MIN_DATE = "2026-01-01"


@router.get("/stats/daily", response_model=StatsRangeResponse)
async def get_stats_daily(start: str, end: str):
    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    rows = await db.get_daily_totals_range(start, end)
    return StatsRangeResponse(days=[DailyTotals(**r) for r in rows])


@router.get("/stats/users/day", response_model=UserOrdersForDateResponse)
async def get_stats_users_day(date: str):
    orders = await db.get_user_orders_for_date(date)
    return UserOrdersForDateResponse(
        date=date,
        orders=orders,
        total_tea=sum(o["tea"] for o in orders),
        total_coffee=sum(o["coffee"] for o in orders),
    )


@router.get("/stats/user-names", response_model=UserNamesResponse)
async def get_stat_user_names():
    names = await db.get_all_user_names()
    return UserNamesResponse(names=names)


@router.get("/stats/user", response_model=UserStatsResponse)
async def get_stats_user_range(name: str, start: str, end: str):
    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    rows = await db.get_user_stats_range(name, start, end)
    days = [UserStatsDayEntry(**r) for r in rows]
    return UserStatsResponse(
        name=name,
        start=start,
        end=end,
        days=days,
        total_tea=sum(d.tea for d in days),
        total_coffee=sum(d.coffee for d in days),
        order_days=len(days),
    )


@router.get("/stats/me", response_model=UserStatsResponse)
async def get_my_stats(
    start: str,
    end: str,
    current_user: AuthUser = Depends(get_current_user),
):
    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    rows = await db.get_user_stats_range(current_user.name, start, end)
    days = [UserStatsDayEntry(**r) for r in rows]
    return UserStatsResponse(
        name=current_user.name,
        start=start,
        end=end,
        days=days,
        total_tea=sum(d.tea for d in days),
        total_coffee=sum(d.coffee for d in days),
        order_days=len(days),
    )
