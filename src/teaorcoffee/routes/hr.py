"""HR routes: view/manage orders and stats for their office."""
from fastapi import APIRouter, HTTPException, Depends

from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    AuthUser,
    RemoveOrderRequest, RemoveOrderResponse,
    PlaceOrderForUserRequest, PlaceOrderForUserResponse,
    OrdersBreakdownResponse, OrderDetail, ProductTotal,
    DailyTotals, StatsRangeResponse,
    UserNamesResponse, UserOrderDetail, UserOrdersForDateResponse,
    UserStatsDayEntry, UserStatsResponse,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

_STATS_MIN_DATE = "2026-01-01"
_HR_ROLES = ("main_admin", "office_admin", "office_hr")

router = APIRouter(prefix="/hr", tags=["HR"])


def _check_hr(user: AuthUser) -> str:
    require_role(user, *_HR_ROLES)
    if not user.office_id:
        raise HTTPException(400, "No office assigned")
    return user.office_id


@router.get("/orders", response_model=OrdersBreakdownResponse)
async def hr_get_orders(user: AuthUser = Depends(get_current_user)):
    office_id = _check_hr(user)
    rows = await db.get_today_breakdown(office_id)
    orders = [OrderDetail(name=r["name"], product_name=r["product_name"],
                          product_emoji=r["product_emoji"], qty=r["qty"]) for r in rows]
    totals_raw = await db.get_today_totals(office_id)
    order_count = await db.get_today_order_count(office_id)
    return OrdersBreakdownResponse(
        orders=orders,
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )


@router.post("/remove-order", response_model=RemoveOrderResponse)
async def hr_remove_order(request: RemoveOrderRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_hr(user)
    name = request.name.strip()
    target = await db.get_user_by_name(name)
    if not target or target.get("office_id") != office_id:
        raise HTTPException(404, f"User '{name}' not found in your office")
    deleted = await db.delete_user_today_vote(int(target["id"]))
    if not deleted:
        raise HTTPException(404, f"No order for '{name}' today")
    await broadcast_votes(office_id)
    return RemoveOrderResponse(success=True, name=name, message=f"Order removed for '{name}'")


@router.post("/place-order", response_model=PlaceOrderForUserResponse)
async def hr_place_order(request: PlaceOrderForUserRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_hr(user)
    name = request.name.strip()
    target = await db.get_user_by_name(name)
    if not target or target.get("office_id") != office_id:
        raise HTTPException(404, f"User '{name}' not found in your office")
    product = await db.get_product_by_id(request.product_id)
    if not product or not product.get("is_active") or product.get("office_id") != office_id:
        raise HTTPException(400, "Invalid product for this office")
    if request.qty < 1 or request.qty > product["max_qty"]:
        raise HTTPException(400, f"Quantity must be 1–{product['max_qty']}")
    if await db.has_user_voted_today(int(target["id"])):
        raise HTTPException(409, f"'{name}' already ordered today")
    await db.insert_vote(int(target["id"]), office_id, request.product_id, product["name"], product["emoji"], request.qty)
    await broadcast_votes(office_id)
    return PlaceOrderForUserResponse(success=True, name=name, message=f"Ordered {request.qty}x {product['name']} for '{name}'")


@router.get("/stats/daily", response_model=StatsRangeResponse)
async def hr_daily_stats(start: str, end: str, user: AuthUser = Depends(get_current_user)):
    office_id = _check_hr(user)
    start = max(start, _STATS_MIN_DATE)
    rows = await db.get_daily_totals_range(start, end, office_id)
    return StatsRangeResponse(days=[DailyTotals(date=r["date"], tea=r["tea"], coffee=r["coffee"], products=r.get("products", {})) for r in rows])


@router.get("/stats/users/day", response_model=UserOrdersForDateResponse)
async def hr_users_day(date: str, user: AuthUser = Depends(get_current_user)):
    office_id = _check_hr(user)
    rows = await db.get_user_orders_for_date(date, office_id)
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
async def hr_user_names(user: AuthUser = Depends(get_current_user)):
    office_id = _check_hr(user)
    return UserNamesResponse(names=await db.get_all_user_names(office_id))


@router.get("/stats/user", response_model=UserStatsResponse)
async def hr_user_stats(name: str, start: str, end: str, user: AuthUser = Depends(get_current_user)):
    office_id = _check_hr(user)
    start = max(start, _STATS_MIN_DATE)
    rows = await db.get_user_stats_range(name, start, end, office_id)
    days = [UserStatsDayEntry(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    return UserStatsResponse(name=name, start=start, end=end, days=days,
                             total_tea=sum(d.tea for d in days), total_coffee=sum(d.coffee for d in days),
                             order_days=len(days))
