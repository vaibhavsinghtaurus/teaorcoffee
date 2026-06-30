"""Office-admin routes: scoped to one office, protected by admin password + role check."""
from fastapi import APIRouter, HTTPException, Depends

from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    AuthUser,
    AllowedNamesResponse, AddAllowedNameRequest, AddAllowedNameResponse,
    RemoveAllowedNameRequest, RemoveAllowedNameResponse,
    RemoveOrderRequest, RemoveOrderResponse,
    PlaceOrderForUserRequest, PlaceOrderForUserResponse,
    RemoveAllLoginsRequest, RemoveAllLoginsResponse,
    SetUserDisabledRequest, SetUserDisabledResponse,
    SetUserRoleRequest, SetUserRoleResponse,
    UsersListResponse, UserOut,
    OrdersBreakdownResponse, OrderDetail, ProductTotal,
    PendingPasswordUsersResponse,
    DailyTotals, StatsRangeResponse,
    UserNamesResponse, UserOrderDetail, UserOrdersForDateResponse,
    UserStatsDayEntry, UserStatsResponse,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

_STATS_MIN_DATE = "2026-01-01"
_OFFICE_ADMIN_ROLES = ("main_admin", "office_admin")

router = APIRouter(prefix="/office-admin", tags=["Office Admin"])


def _check_office(user: AuthUser) -> str:
    require_role(user, *_OFFICE_ADMIN_ROLES)
    if not user.office_id:
        raise HTTPException(400, "No office assigned")
    return user.office_id


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=OrdersBreakdownResponse)
async def oa_get_orders(user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
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


@router.post("/orders/reset")
async def oa_reset_orders(user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    await db.delete_all_votes(office_id)
    await broadcast_votes(office_id)
    return {"success": True, "message": "All orders reset for today"}


@router.post("/orders/remove", response_model=RemoveOrderResponse)
async def oa_remove_order(request: RemoveOrderRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    name = request.name.strip()
    target = await db.get_user_by_name(name)
    if not target or target.get("office_id") != office_id:
        raise HTTPException(404, f"User '{name}' not found in your office")
    deleted = await db.delete_user_today_vote(int(target["id"]))
    if not deleted:
        raise HTTPException(404, f"No order for '{name}' today")
    await broadcast_votes(office_id)
    return RemoveOrderResponse(success=True, name=name, message=f"Order removed for '{name}'")


@router.post("/orders/place", response_model=PlaceOrderForUserResponse)
async def oa_place_order(request: PlaceOrderForUserRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
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


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=UsersListResponse)
async def oa_list_users(user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    users = await db.get_users_for_office(office_id)
    return UsersListResponse(users=[UserOut(
        id=u["_id"], name=u["name"], role=u.get("role", "user"),
        office_id=u.get("office_id"), company_id=u.get("company_id"),
        position=u.get("position"), is_disabled=u.get("is_disabled", 0),
        nickname=u.get("nickname"),
    ) for u in users])


@router.post("/users/role", response_model=SetUserRoleResponse)
async def oa_set_user_role(request: SetUserRoleRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    target = await db.get_user_by_name(request.name.strip())
    if not target or target.get("office_id") != office_id:
        raise HTTPException(404, "User not found in your office")
    # Office admin can only assign roles within their office scope
    allowed_roles = {"office_admin", "office_hr", "user"}
    if user.role != "main_admin":
        if request.role not in allowed_roles:
            raise HTTPException(403, f"Office admin can only set: {', '.join(allowed_roles)}")
    await db.set_user_role(int(target["id"]), request.role)
    return SetUserRoleResponse(success=True, name=request.name, role=request.role, message=f"Role set to '{request.role}'")


@router.post("/users/disable", response_model=SetUserDisabledResponse)
async def oa_set_disabled(request: SetUserDisabledRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    target = await db.get_user_by_name(request.name.strip())
    if not target or target.get("office_id") != office_id:
        raise HTTPException(404, "User not found in your office")
    await db.set_user_disabled(int(target["id"]), request.disabled)
    action = "disabled" if request.disabled else "enabled"
    return SetUserDisabledResponse(success=True, name=request.name, message=f"User '{request.name}' {action}")


@router.post("/users/logout-all", response_model=RemoveAllLoginsResponse)
async def oa_logout_all(user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    count = await db.clear_all_tokens(office_id)
    return RemoveAllLoginsResponse(success=True, count=count, message=f"Logged out {count} user(s)")


@router.get("/users/pending-password", response_model=PendingPasswordUsersResponse)
async def oa_pending_password(user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    users = await db.get_users_without_password(office_id)
    return PendingPasswordUsersResponse(users=users, count=len(users))


# ── Allowed Names ─────────────────────────────────────────────────────────────

@router.get("/allowed-names", response_model=AllowedNamesResponse)
async def oa_list_allowed_names(user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    return AllowedNamesResponse(names=sorted(await db.get_allowed_names(office_id)))


@router.post("/allowed-names", response_model=AddAllowedNameResponse)
async def oa_add_allowed_name(request: AddAllowedNameRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    added = await db.add_allowed_name(name, office_id)
    if not added:
        raise HTTPException(409, f"'{name}' already in allowed list")
    return AddAllowedNameResponse(success=True, name=name, message=f"'{name}' added to office")


@router.delete("/allowed-names", response_model=RemoveAllowedNameResponse)
async def oa_remove_allowed_name(request: RemoveAllowedNameRequest, user: AuthUser = Depends(get_current_user)):
    _check_office(user)
    name = request.name.strip()
    removed = await db.remove_allowed_name(name)
    if not removed:
        raise HTTPException(404, f"'{name}' not in allowed list")
    return RemoveAllowedNameResponse(success=True, name=name, message=f"'{name}' removed")


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats/daily", response_model=StatsRangeResponse)
async def oa_daily_stats(start: str, end: str, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    rows = await db.get_daily_totals_range(start, end, office_id)
    return StatsRangeResponse(days=[DailyTotals(date=r["date"], tea=r["tea"], coffee=r["coffee"], products=r.get("products", {})) for r in rows])


@router.get("/stats/users/day", response_model=UserOrdersForDateResponse)
async def oa_users_day(date: str, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
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
async def oa_user_names(user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    return UserNamesResponse(names=await db.get_all_user_names(office_id))


@router.get("/stats/user", response_model=UserStatsResponse)
async def oa_user_stats(name: str, start: str, end: str, user: AuthUser = Depends(get_current_user)):
    office_id = _check_office(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    rows = await db.get_user_stats_range(name, start, end, office_id)
    days = [UserStatsDayEntry(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    return UserStatsResponse(name=name, start=start, end=end, days=days,
                             total_tea=sum(d.tea for d in days), total_coffee=sum(d.coffee for d in days),
                             order_days=len(days))
