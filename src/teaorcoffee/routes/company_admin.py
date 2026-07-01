"""Company-admin routes: scoped to one company. company_admin and manager have equal permissions."""
from fastapi import APIRouter, HTTPException, Depends

from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.core.database import db, today_ist
from src.teaorcoffee.models.schema import (
    AuthUser,
    RemoveOrderRequest, RemoveOrderResponse,
    PlaceOrderForUserRequest, PlaceOrderForUserResponse,
    RemoveAllLoginsRequest, RemoveAllLoginsResponse,
    SetUserDisabledRequest, SetUserDisabledResponse,
    SetUserRoleRequest, SetUserRoleResponse,
    UsersListResponse, UserOut,
    AddCompanyMemberRequest, AddCompanyMemberResponse,
    RemoveCompanyMemberRequest,
    OrdersBreakdownResponse, OrderDetail, ProductTotal,
    PendingPasswordUsersResponse,
    DailyTotals, StatsRangeResponse,
    UserNamesResponse, UserOrderDetail, UserOrdersForDateResponse,
    UserStatsDayEntry, UserStatsResponse,
    CompanyProductOut, EnableCompanyProductRequest, DisableCompanyProductRequest,
    SetCompanyProductMaxQtyRequest,
    CompanyOut, SetMyAddressRequest,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

_STATS_MIN_DATE = "2026-01-01"
_COMPANY_ROLES = ("super_admin", "company_admin", "manager")
_ASSIGNABLE_ROLES = {"company_admin", "manager", "hr", "employee", "distributor_boy"}

router = APIRouter(prefix="/company-admin", tags=["Company Admin"])


def _check_company(user: AuthUser, requested_company_id: str | None = None) -> str:
    require_role(user, *_COMPANY_ROLES)
    if user.role == "super_admin" and requested_company_id:
        return requested_company_id
    if not user.company_id:
        raise HTTPException(400, "No company assigned")
    return user.company_id


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=OrdersBreakdownResponse)
async def ca_get_orders(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    rows = await db.get_today_breakdown(company_id)
    orders = [OrderDetail(name=r["name"], product_name=r["product_name"],
                          product_emoji=r["product_emoji"], qty=r["qty"], status=r.get("status", "delivered")) for r in rows]
    totals_raw = await db.get_today_totals(company_id)
    order_count = await db.get_today_order_count(company_id)
    return OrdersBreakdownResponse(
        orders=orders,
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )


@router.post("/orders/reset")
async def ca_reset_orders(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    await db.delete_all_votes(company_id)
    await broadcast_votes(company_id)
    return {"success": True, "message": "All orders reset for today"}


@router.post("/orders/remove", response_model=RemoveOrderResponse)
async def ca_remove_order(request: RemoveOrderRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    name = request.name.strip()
    target = await db.get_user_by_name(name)
    if not target or target.get("company_id") != company_id:
        raise HTTPException(404, f"User '{name}' not found in your company")
    deleted = await db.delete_user_today_vote(int(target["id"]))
    if not deleted:
        raise HTTPException(404, f"No pending order for '{name}' today")
    await broadcast_votes(company_id)
    return RemoveOrderResponse(success=True, name=name, message=f"Order removed for '{name}'")


@router.post("/orders/place", response_model=PlaceOrderForUserResponse)
async def ca_place_order(request: PlaceOrderForUserRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    name = request.name.strip()
    target = await db.get_user_by_name(name)
    if not target or target.get("company_id") != company_id:
        raise HTTPException(404, f"User '{name}' not found in your company")
    product = await db.get_company_product(company_id, request.product_id)
    if not product or not product["is_enabled"]:
        raise HTTPException(400, "Invalid or unavailable product for this company")
    if request.qty < 1 or request.qty > product["max_qty"]:
        raise HTTPException(400, f"Quantity must be 1–{product['max_qty']}")
    date_str = request.date or today_ist()
    if await db.has_user_pending_vote(int(target["id"]), date_str):
        raise HTTPException(409, f"'{name}' already has a pending order for that date")
    await db.insert_vote(int(target["id"]), company_id, request.product_id, product["name"], product["emoji"],
                          request.qty, price_at_order=product["price"], date_str=date_str)
    if date_str == today_ist():
        await broadcast_votes(company_id)
    return PlaceOrderForUserResponse(success=True, name=name, message=f"Ordered {request.qty}x {product['name']} for '{name}'")


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=UsersListResponse)
async def ca_list_users(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    users = await db.get_users_for_company(company_id)
    return UsersListResponse(users=[UserOut(
        id=u["_id"], name=u["name"], role=u.get("role", "employee"),
        company_id=u.get("company_id"), is_disabled=u.get("is_disabled", 0),
        nickname=u.get("nickname"),
    ) for u in users])


@router.post("/staff", response_model=AddCompanyMemberResponse)
async def ca_add_staff(request: AddCompanyMemberRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user, request.company_id)
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Name required")
    if request.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(400, f"Role must be one of: {', '.join(_ASSIGNABLE_ROLES)}")
    added = await db.add_company_member(name, company_id, request.role)
    if not added:
        raise HTTPException(409, f"User '{name}' already exists")
    return AddCompanyMemberResponse(success=True, name=name, message=f"'{name}' added as {request.role}")


@router.delete("/staff")
async def ca_remove_staff(request: RemoveCompanyMemberRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    target = await db.users.find_one({"_id": request.user_id})
    if not target or target.get("company_id") != company_id:
        raise HTTPException(404, "Staff member not found in your company")
    removed = await db.remove_company_member(request.user_id)
    if not removed:
        raise HTTPException(404, "Staff member not found")
    return {"success": True, "message": "Staff member removed"}


@router.post("/users/role", response_model=SetUserRoleResponse)
async def ca_set_user_role(request: SetUserRoleRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    target = await db.get_user_by_name(request.name.strip())
    if not target or target.get("company_id") != company_id:
        raise HTTPException(404, "User not found in your company")
    if request.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(403, f"Can only set: {', '.join(_ASSIGNABLE_ROLES)}")
    await db.set_user_role(int(target["id"]), request.role)
    return SetUserRoleResponse(success=True, name=request.name, role=request.role, message=f"Role set to '{request.role}'")


@router.post("/users/disable", response_model=SetUserDisabledResponse)
async def ca_set_disabled(request: SetUserDisabledRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    target = await db.get_user_by_name(request.name.strip())
    if not target or target.get("company_id") != company_id:
        raise HTTPException(404, "User not found in your company")
    await db.set_user_disabled(int(target["id"]), request.disabled)
    action = "disabled" if request.disabled else "enabled"
    return SetUserDisabledResponse(success=True, name=request.name, message=f"User '{request.name}' {action}")


@router.post("/users/logout-all", response_model=RemoveAllLoginsResponse)
async def ca_logout_all(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    count = await db.clear_all_tokens(company_id)
    return RemoveAllLoginsResponse(success=True, count=count, message=f"Logged out {count} user(s)")


@router.get("/users/pending-password", response_model=PendingPasswordUsersResponse)
async def ca_pending_password(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    users = await db.get_users_without_password(company_id)
    return PendingPasswordUsersResponse(users=users, count=len(users))


# ── Company Profile (own branch address) ──────────────────────────────────────

@router.get("/company")
async def ca_get_company(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    c = await db.get_company_by_id(company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return CompanyOut(id=c["id"], name=c["name"], slug=c["slug"], mode=c["mode"],
                      address=c.get("address", ""), distributor_id=c.get("distributor_id"), is_active=c["is_active"])


@router.put("/company/address")
async def ca_set_address(request: SetMyAddressRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    address = request.address.strip()
    if not address:
        raise HTTPException(400, "Address cannot be empty")
    await db.update_company_address(company_id, address)
    return {"success": True, "message": "Address updated"}


# ── Product Catalog (enable/disable distributor's products) ─────────────────

@router.get("/catalog")
async def ca_get_catalog(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    rows = await db.get_company_products(company_id)
    return {"catalog": [CompanyProductOut(**r) for r in rows]}


@router.post("/catalog/enable")
async def ca_enable_product(request: EnableCompanyProductRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    await db.enable_company_product(company_id, request.distributor_product_id, request.max_qty_override)
    return {"success": True, "message": "Product enabled"}


@router.post("/catalog/disable")
async def ca_disable_product(request: DisableCompanyProductRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    await db.disable_company_product(company_id, request.distributor_product_id)
    return {"success": True, "message": "Product disabled"}


@router.post("/catalog/max-qty")
async def ca_set_max_qty(request: SetCompanyProductMaxQtyRequest, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    await db.set_company_product_max_qty(company_id, request.distributor_product_id, request.max_qty)
    return {"success": True, "message": "Max quantity updated"}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats/daily", response_model=StatsRangeResponse)
async def ca_daily_stats(start: str, end: str, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    rows = await db.get_daily_totals_range(start, end, company_id)
    return StatsRangeResponse(days=[DailyTotals(date=r["date"], tea=r["tea"], coffee=r["coffee"], products=r.get("products", {})) for r in rows])


@router.get("/stats/users/day", response_model=UserOrdersForDateResponse)
async def ca_users_day(date: str, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    rows = await db.get_user_orders_for_date(date, company_id)
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
async def ca_user_names(user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    return UserNamesResponse(names=await db.get_all_user_names(company_id))


@router.get("/stats/user", response_model=UserStatsResponse)
async def ca_user_stats(name: str, start: str, end: str, user: AuthUser = Depends(get_current_user)):
    company_id = _check_company(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    rows = await db.get_user_stats_range(name, start, end, company_id)
    days = [UserStatsDayEntry(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    return UserStatsResponse(name=name, start=start, end=end, days=days,
                             total_tea=sum(d.tea for d in days), total_coffee=sum(d.coffee for d in days),
                             order_days=len(days))
