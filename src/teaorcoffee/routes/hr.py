"""HR/Manager routes: order management and stats, protected by HR password."""
from fastapi import APIRouter, HTTPException, status

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.models.schema import (
    DailyTotals,
    OrdersBreakdownResponse,
    PlaceOrderForUserRequest,
    PlaceOrderForUserResponse,
    RemoveOrderRequest,
    RemoveOrderResponse,
    StatsRangeResponse,
    UserNamesResponse,
    UserOrderDetail,
    UserOrdersForDateResponse,
    UserStatsDayEntry,
    UserStatsResponse,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

_STATS_MIN_DATE = "2026-01-01"

router = APIRouter(prefix="/hr", tags=["HR"])


def _require_hr(password: str):
    configured = settings.hr_password
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HR access is not configured on this server",
        )
    if password != configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HR password")


@router.get("/orders", response_model=OrdersBreakdownResponse)
async def hr_get_orders(password: str):
    """HR: get today's orders for all users"""
    _require_hr(password)
    rows = await db.get_today_breakdown()
    orders = [UserOrderDetail(name=r["name"], tea=r["tea"], coffee=r["coffee"]) for r in rows]
    totals = await db.get_today_totals()
    return OrdersBreakdownResponse(
        orders=orders,
        total_tea=totals["tea"],
        total_coffee=totals["coffee"],
    )


@router.post("/remove-order", response_model=RemoveOrderResponse)
async def hr_remove_order(request: RemoveOrderRequest):
    """HR: remove today's order for a user"""
    _require_hr(request.password)

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    user = await db.get_user_by_name(name)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{name}' not found")

    deleted = await db.delete_user_today_vote(int(user["id"]))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No order found for '{name}' today",
        )

    await broadcast_votes()
    return RemoveOrderResponse(success=True, name=name, message=f"Order removed for '{name}'")


@router.post("/place-order", response_model=PlaceOrderForUserResponse)
async def hr_place_order(request: PlaceOrderForUserRequest):
    """HR: place an order on behalf of a user"""
    _require_hr(request.password)

    if request.tea < 0 or request.coffee < 0:
        raise HTTPException(400, "Tea and coffee must be >= 0")
    if request.tea == 0 and request.coffee == 0:
        raise HTTPException(400, "At least one drink must be ordered")
    if request.tea > 0 and request.coffee > 0:
        raise HTTPException(400, "You can only order tea OR coffee, not both")
    if request.tea > 2:
        raise HTTPException(400, "You can order maximum 2 tea")
    if request.coffee > 1:
        raise HTTPException(400, "You can order maximum 1 coffee")

    name = request.name.strip()
    user = await db.get_user_by_name(name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{name}' not found"
        )

    if await db.has_user_voted_today(int(user["id"])):
        raise HTTPException(409, f"'{name}' has already placed an order today")

    await db.insert_vote(int(user["id"]), request.tea, request.coffee)
    await broadcast_votes()

    drink = f"{request.tea} tea" if request.tea else f"{request.coffee} coffee"
    return PlaceOrderForUserResponse(
        success=True, name=name, message=f"Ordered {drink} for '{name}'"
    )


# ── HR Stats (password-protected mirrors of public stats) ─────────────────────

@router.get("/stats/daily", response_model=StatsRangeResponse)
async def hr_get_daily_stats(password: str, start: str, end: str):
    """HR: daily tea/coffee totals for a date range"""
    _require_hr(password)
    start = max(start, _STATS_MIN_DATE)
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    rows = await db.get_daily_totals_range(start, end)
    return StatsRangeResponse(days=[DailyTotals(**r) for r in rows])


@router.get("/stats/users/day", response_model=UserOrdersForDateResponse)
async def hr_get_users_day(password: str, date: str):
    """HR: per-user order breakdown for a specific date"""
    _require_hr(password)
    rows = await db.get_user_orders_for_date(date)
    orders = [UserOrderDetail(**r) for r in rows]
    return UserOrdersForDateResponse(
        date=date,
        orders=orders,
        total_tea=sum(o.tea for o in orders),
        total_coffee=sum(o.coffee for o in orders),
    )


@router.get("/stats/user-names", response_model=UserNamesResponse)
async def hr_get_user_names(password: str):
    """HR: list of all active user names"""
    _require_hr(password)
    names = await db.get_all_user_names()
    return UserNamesResponse(names=names)


@router.get("/stats/user", response_model=UserStatsResponse)
async def hr_get_user_stats(password: str, name: str, start: str, end: str):
    """HR: daily tea/coffee totals for any user over a date range"""
    _require_hr(password)
    start = max(start, _STATS_MIN_DATE)
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
