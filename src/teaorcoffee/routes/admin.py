from fastapi import APIRouter, HTTPException, status, Depends

from src.teaorcoffee.core.database import db, today_ist
from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.routes.auth import register_company_impl
from src.teaorcoffee.models.schema import (
    AuthUser,
    ResetRequest, VotesResponse, ProductTotal,
    UnbindRequest, UnbindResponse,
    RemoveOrderRequest, RemoveOrderResponse,
    RemoveAllLoginsRequest, RemoveAllLoginsResponse,
    SetUserDisabledRequest, SetUserDisabledResponse,
    PendingPasswordUsersResponse,
    UpdateUserNameRequest, UpdateUserNameResponse,
    PlaceOrderForUserRequest, PlaceOrderForUserResponse,
    SetNicknameRequest, SetNicknameResponse,
    SetUserRoleRequest, SetUserRoleResponse,
    UsersListResponse, UserOut,
    CompanyOut, CreateCompanyRequest, UpdateCompanyRequest, UpdateCompanyAddressRequest, CompanyActiveRequest,
    SetCompanyDistributorRequest, SetCompanyModeRequest,
    RegisterCompanyRequest, RegisterCompanyResponse,
    DailyTotals, StatsRangeResponse,
    UserNamesResponse, UserOrderDetail, UserOrdersForDateResponse,
    UserStatsDayEntry, UserStatsResponse,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

_STATS_MIN_DATE = "2026-01-01"

router = APIRouter(tags=["Admin"])


def _require_super_admin(user: AuthUser):
    require_role(user, "super_admin")


# ── Companies ──────────────────────────────────────────────────────────────────

@router.get("/companies")
async def list_companies(user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    companies = await db.get_all_companies()
    return {"companies": [CompanyOut(id=c["id"], name=c["name"], slug=c["slug"], mode=c["mode"],
                                     address=c.get("address", ""), distributor_id=c.get("distributor_id"), is_active=c["is_active"]) for c in companies]}


@router.post("/companies")
async def create_company(request: CreateCompanyRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    name = request.name.strip()
    slug = request.slug.strip().lower().replace(" ", "-")
    address = request.address.strip()
    if not name or not slug:
        raise HTTPException(400, "Name and slug are required")
    if not address:
        raise HTTPException(400, "Address is required — it's what distinguishes this branch.")
    if request.mode not in ("company", "distributor"):
        raise HTTPException(400, "mode must be 'company' or 'distributor'")
    company_id = await db.create_company_branch(name, slug, mode=request.mode, address=address,
                                                 distributor_id=request.distributor_id)
    return {"success": True, "company_id": company_id, "message": f"Company '{name}' created"}


@router.put("/companies")
async def update_company(request: UpdateCompanyRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    updated = await db.update_company(request.company_id, request.name.strip())
    if not updated:
        raise HTTPException(404, "Company not found")
    return {"success": True, "message": f"Company updated to '{request.name}'"}


@router.put("/companies/address")
async def set_company_address(request: UpdateCompanyAddressRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    address = request.address.strip()
    if not address:
        raise HTTPException(400, "Address cannot be empty")
    updated = await db.update_company_address(request.company_id, address)
    if not updated:
        raise HTTPException(404, "Company not found")
    return {"success": True, "message": "Address updated"}


@router.post("/companies/active")
async def set_company_active(request: CompanyActiveRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    updated = await db.set_company_active(request.company_id, request.is_active)
    if not updated:
        raise HTTPException(404, "Company not found")
    action = "activated" if request.is_active else "marked inoperative"
    if not request.is_active:
        await db.clear_all_tokens(request.company_id)
    return {"success": True, "message": f"Company {action}"}


@router.post("/companies/distributor")
async def set_company_distributor(request: SetCompanyDistributorRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    distributor = await db.get_company_by_id(request.distributor_id)
    if not distributor or distributor.get("mode") != "distributor":
        raise HTTPException(400, "Invalid distributor company")
    updated = await db.set_company_distributor(request.company_id, request.distributor_id)
    if not updated:
        raise HTTPException(404, "Company not found")
    return {"success": True, "message": "Distributor updated"}


@router.post("/companies/mode")
async def set_company_mode(request: SetCompanyModeRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    if request.mode not in ("company", "distributor"):
        raise HTTPException(400, "mode must be 'company' or 'distributor'")
    updated = await db.set_company_mode(request.company_id, request.mode)
    if not updated:
        raise HTTPException(404, "Company not found")
    return {"success": True, "message": f"Mode updated to '{request.mode}'"}


@router.post("/companies/create-full", response_model=RegisterCompanyResponse)
async def create_full_company(request: RegisterCompanyRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    return await register_company_impl(request)


# ── Orders ─────────────────────────────────────────────────────────────────────

@router.post("/reset")
async def reset_votes(request: ResetRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    await db.delete_all_votes(request.company_id)
    if request.company_id:
        await broadcast_votes(request.company_id)
    totals = await db.get_today_totals(request.company_id)
    return VotesResponse(totals={k: ProductTotal(**v) for k, v in totals.items()}, order_count=0)


@router.post("/remove-order", response_model=RemoveOrderResponse)
async def remove_order(request: RemoveOrderRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    name = request.name.strip()
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    deleted = await db.delete_user_today_vote(int(u["id"]))
    if not deleted:
        raise HTTPException(404, f"No pending order for '{name}' today")
    if u.get("company_id"):
        await broadcast_votes(u["company_id"])
    return RemoveOrderResponse(success=True, name=name, message=f"Order removed for '{name}'")


@router.post("/place-order", response_model=PlaceOrderForUserResponse)
async def place_order_for_user(request: PlaceOrderForUserRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    name = request.name.strip()
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    company_id = u.get("company_id")
    if not company_id:
        raise HTTPException(400, f"User '{name}' has no company assigned")
    product = await db.get_company_product(company_id, request.product_id)
    if not product or not product["is_enabled"]:
        raise HTTPException(400, "Invalid or unavailable product for this company")
    if request.qty < 1 or request.qty > product["max_qty"]:
        raise HTTPException(400, f"Quantity must be 1–{product['max_qty']}")
    date_str = request.date or today_ist()
    if await db.has_user_pending_vote(int(u["id"]), date_str):
        raise HTTPException(409, f"'{name}' already has a pending order for that date")
    await db.insert_vote(int(u["id"]), company_id, request.product_id, product["name"], product["emoji"],
                          request.qty, price_at_order=product["price"], date_str=date_str)
    if date_str == today_ist():
        await broadcast_votes(company_id)
    return PlaceOrderForUserResponse(success=True, name=name, message=f"Ordered {request.qty}x {product['name']} for '{name}'")


# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=UsersListResponse)
async def list_all_users(company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    if company_id:
        users = await db.get_users_for_company(company_id)
    else:
        users = await db.get_all_users()
    return UsersListResponse(users=[UserOut(
        id=u["_id"], name=u["name"], role=u.get("role", "employee"),
        company_id=u.get("company_id"), is_disabled=u.get("is_disabled", 0),
        nickname=u.get("nickname"),
    ) for u in users])


@router.post("/users/role", response_model=SetUserRoleResponse)
async def set_user_role(request: SetUserRoleRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    u = await db.get_user_by_name(request.name.strip())
    if not u:
        raise HTTPException(404, f"User '{request.name}' not found")
    valid_roles = {"super_admin", "company_admin", "manager", "hr", "employee", "distributor_boy"}
    if request.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    await db.set_user_role(int(u["id"]), request.role)
    return SetUserRoleResponse(success=True, name=request.name, role=request.role, message=f"Role updated to '{request.role}'")


@router.post("/unbind", response_model=UnbindResponse)
async def unbind_user(request: UnbindRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    name = request.name.strip()
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    if not u["session_token"]:
        return UnbindResponse(success=True, name=name, message=f"User '{name}' has no active session")
    await db.update_user_token(int(u["id"]), None)
    return UnbindResponse(success=True, name=name, message=f"Session removed for '{name}'")


@router.post("/remove-all-logins", response_model=RemoveAllLoginsResponse)
async def remove_all_logins(request: RemoveAllLoginsRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    count = await db.clear_all_tokens(request.company_id)
    return RemoveAllLoginsResponse(success=True, count=count, message=f"Logged out {count} user(s)")


@router.post("/set-user-disabled", response_model=SetUserDisabledResponse)
async def set_user_disabled(request: SetUserDisabledRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    name = request.name.strip()
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    await db.set_user_disabled(int(u["id"]), request.disabled)
    action = "disabled" if request.disabled else "enabled"
    return SetUserDisabledResponse(success=True, name=name, message=f"User '{name}' {action}")


@router.get("/users/pending-password", response_model=PendingPasswordUsersResponse)
async def get_pending_password_users(company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    users = await db.get_users_without_password(company_id)
    return PendingPasswordUsersResponse(users=users, count=len(users))


@router.put("/users/rename", response_model=UpdateUserNameResponse)
async def rename_user(request: UpdateUserNameRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    old_name, new_name = request.old_name.strip(), request.new_name.strip()
    if not old_name or not new_name:
        raise HTTPException(400, "Names cannot be empty")
    if await db.get_user_by_name(new_name):
        raise HTTPException(409, f"User '{new_name}' already exists")
    if not await db.update_user_name(old_name, new_name):
        raise HTTPException(404, f"User '{old_name}' not found")
    return UpdateUserNameResponse(success=True, old_name=old_name, new_name=new_name, message=f"'{old_name}' → '{new_name}'")


@router.put("/users/nickname", response_model=SetNicknameResponse)
async def set_user_nickname(request: SetNicknameRequest, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    name = request.name.strip()
    nickname = request.nickname.strip() if request.nickname else None
    if nickname == "":
        nickname = None
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    if nickname:
        existing = await db.get_user_by_nickname(nickname)
        if existing and existing["_id"] != u["_id"]:
            raise HTTPException(409, f"Nickname '{nickname}' already taken")
    await db.set_nickname(int(u["id"]), nickname)
    action = f"set to '{nickname}'" if nickname else "cleared"
    return SetNicknameResponse(success=True, name=name, nickname=nickname, message=f"Nickname {action}")


# ── Admin Stats (global — the only place cross-company stats are allowed) ────

@router.get("/admin/stats/daily", response_model=StatsRangeResponse)
async def admin_get_daily_stats(start: str, end: str, company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    if end < start:
        raise HTTPException(400, "end must be >= start")
    rows = await db.get_daily_totals_range(start, end, company_id)
    return StatsRangeResponse(days=[DailyTotals(date=r["date"], tea=r["tea"], coffee=r["coffee"], products=r.get("products", {})) for r in rows])


@router.get("/admin/stats/users/day", response_model=UserOrdersForDateResponse)
async def admin_get_user_stats_for_day(date: str, company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    rows = await db.get_user_orders_for_date(date, company_id)
    orders = [UserOrderDetail(name=r["name"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), product_emoji=r.get("product_emoji", ""), qty=r.get("qty", 0)) for r in rows]
    totals: dict = {}
    for r in rows:
        pn = r.get("product_name", "")
        if pn:
            totals[pn] = totals.get(pn, 0) + r.get("qty", 0)
    return UserOrdersForDateResponse(date=date, orders=orders,
                                     total_tea=sum(o.tea for o in orders),
                                     total_coffee=sum(o.coffee for o in orders),
                                     totals=totals)


@router.get("/admin/stats/user-names", response_model=UserNamesResponse)
async def admin_get_stat_user_names(company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    return UserNamesResponse(names=await db.get_all_user_names(company_id))


@router.get("/admin/stats/user", response_model=UserStatsResponse)
async def admin_get_user_stats_range(name: str, start: str, end: str, company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_super_admin(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    if end < start:
        raise HTTPException(400, "end must be >= start")
    rows = await db.get_user_stats_range(name, start, end, company_id)
    days = [UserStatsDayEntry(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    return UserStatsResponse(name=name, start=start, end=end, days=days,
                             total_tea=sum(d.tea for d in days), total_coffee=sum(d.coffee for d in days),
                             order_days=len(days))
