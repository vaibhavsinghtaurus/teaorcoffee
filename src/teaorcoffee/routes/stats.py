from fastapi import APIRouter, Depends, HTTPException

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    AuthUser, DailyTotals, StatsRangeResponse,
    UserNamesResponse, UserOrderDetail, UserOrdersForDateResponse,
    UserStatsDayEntry, UserStatsResponse,
)

router = APIRouter(tags=["Stats"])
_MIN_DATE = "2026-01-01"


@router.get("/stats/daily", response_model=StatsRangeResponse)
async def get_stats_daily(start: str, end: str, user: AuthUser = Depends(get_current_user)):
    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(400, "end must be >= start")
    rows = await db.get_daily_totals_range(start, end, user.company_id)
    return StatsRangeResponse(days=[DailyTotals(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                                                 products=r.get("products", {})) for r in rows])


@router.get("/stats/users/day", response_model=UserOrdersForDateResponse)
async def get_stats_users_day(date: str, user: AuthUser = Depends(get_current_user)):
    rows = await db.get_user_orders_for_date(date, user.company_id)
    orders = [UserOrderDetail(name=r["name"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    totals: dict = {}
    for r in rows:
        pn = r.get("product_name", "")
        if pn:
            totals[pn] = totals.get(pn, 0) + r.get("qty", 0)
    return UserOrdersForDateResponse(date=date, orders=orders,
                                     total_tea=sum(o.tea for o in orders),
                                     total_coffee=sum(o.coffee for o in orders), totals=totals)


@router.get("/stats/user-names", response_model=UserNamesResponse)
async def get_stat_user_names(user: AuthUser = Depends(get_current_user)):
    return UserNamesResponse(names=await db.get_all_user_names(user.company_id))


@router.get("/stats/user", response_model=UserStatsResponse)
async def get_stats_user_range(name: str, start: str, end: str, user: AuthUser = Depends(get_current_user)):
    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(400, "end must be >= start")
    rows = await db.get_user_stats_range(name, start, end, user.company_id)
    days = [UserStatsDayEntry(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    return UserStatsResponse(name=name, start=start, end=end, days=days,
                             total_tea=sum(d.tea for d in days), total_coffee=sum(d.coffee for d in days),
                             order_days=len(days))


@router.get("/stats/me", response_model=UserStatsResponse)
async def get_my_stats(start: str, end: str, user: AuthUser = Depends(get_current_user)):
    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(400, "end must be >= start")
    rows = await db.get_user_stats_range(user.name, start, end, user.company_id)
    days = [UserStatsDayEntry(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    return UserStatsResponse(name=user.name, start=start, end=end, days=days,
                             total_tea=sum(d.tea for d in days), total_coffee=sum(d.coffee for d in days),
                             order_days=len(days))
