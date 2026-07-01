from fastapi import APIRouter, HTTPException, status, Depends

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.models.schema import (
    AuthUser,
    ResetRequest, VotesResponse, ProductTotal,
    UnbindRequest, UnbindResponse,
    RemoveOrderRequest, RemoveOrderResponse,
    RemoveAllLoginsRequest, RemoveAllLoginsResponse,
    SetUserDisabledRequest, SetUserDisabledResponse,
    PendingPasswordUsersResponse,
    UpdateUserNameRequest, UpdateUserNameResponse,
    AllowedNamesResponse, AddAllowedNameRequest, AddAllowedNameResponse,
    RemoveAllowedNameRequest, RemoveAllowedNameResponse,
    PlaceOrderForUserRequest, PlaceOrderForUserResponse,
    SetNicknameRequest, SetNicknameResponse,
    SetUserRoleRequest, SetUserRoleResponse,
    UsersListResponse, UserOut,
    OfficeOut, CreateOfficeRequest, UpdateOfficeRequest, OfficeActiveRequest,
    CreateFullOfficeRequest, CreateFullOfficeResponse,
    DailyTotals, StatsRangeResponse,
    UserNamesResponse, UserOrderDetail, UserOrdersForDateResponse,
    UserStatsDayEntry, UserStatsResponse,
    OfficeRequestOut,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

_STATS_MIN_DATE = "2026-01-01"

router = APIRouter(tags=["Admin"])


def _require_main_admin(user: AuthUser):
    require_role(user, "main_admin")


# ── Offices ────────────────────────────────────────────────────────────────────

@router.get("/offices")
async def list_offices(user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    offices = await db.get_all_offices()
    return {"offices": [OfficeOut(id=o["id"], name=o["name"], slug=o["slug"], is_active=o["is_active"]) for o in offices]}


@router.post("/offices")
async def create_office(request: CreateOfficeRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    name = request.name.strip()
    slug = request.slug.strip().lower().replace(" ", "-")
    if not name or not slug:
        raise HTTPException(400, "Name and slug are required")
    office_id = await db.create_office(name, slug)
    return {"success": True, "office_id": office_id, "message": f"Office '{name}' created"}


@router.put("/offices")
async def update_office(request: UpdateOfficeRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    updated = await db.update_office(request.office_id, request.name.strip())
    if not updated:
        raise HTTPException(404, "Office not found")
    return {"success": True, "message": f"Office updated to '{request.name}'"}


@router.post("/offices/active")
async def set_office_active(request: OfficeActiveRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    updated = await db.set_office_active(request.office_id, request.is_active)
    if not updated:
        raise HTTPException(404, "Office not found")
    action = "activated" if request.is_active else "deactivated"
    return {"success": True, "message": f"Office {action}"}


@router.post("/offices/create-full", response_model=CreateFullOfficeResponse)
async def create_full_office(request: CreateFullOfficeRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    name = request.name.strip()
    slug = request.slug.strip().lower().replace(" ", "-")
    if not name or not slug:
        raise HTTPException(400, "Name and slug are required")
    result = await db.create_full_office(
        name=name,
        slug=slug,
        employee_names=request.employee_names,
        admin_names=request.admin_names,
        hr_names=request.hr_names,
    )
    if request.approve_request_id:
        await db.update_office_request_status(request.approve_request_id, "approved")
    return CreateFullOfficeResponse(
        success=True,
        office_id=result["office_id"],
        name=result["name"],
        message=f"Office '{name}' created with {len(request.employee_names)} employees, "
                f"{len(request.admin_names)} admin(s), {len(request.hr_names)} HR(s).",
    )


# ── Office Requests ────────────────────────────────────────────────────────────

@router.get("/admin/office-requests")
async def list_office_requests(status_filter: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    requests = await db.get_office_requests(status_filter)
    pending_count = await db.count_pending_office_requests()
    return {
        "requests": [OfficeRequestOut(
            id=r["id"], office_name=r["office_name"],
            requester_name=r["requester_name"], contact_info=r["contact_info"],
            status=r["status"], created_at=r["created_at"],
        ) for r in requests],
        "pending_count": pending_count,
    }


@router.post("/admin/office-requests/{request_id}/reject")
async def reject_office_request(request_id: str, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    req = await db.get_office_request_by_id(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    await db.update_office_request_status(request_id, "rejected")
    return {"success": True, "message": "Request rejected."}


# ── Orders ─────────────────────────────────────────────────────────────────────

@router.post("/reset")
async def reset_votes(request: ResetRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    await db.delete_all_votes(request.office_id)
    if request.office_id:
        await broadcast_votes(request.office_id)
    totals = await db.get_today_totals(request.office_id)
    return VotesResponse(totals={k: ProductTotal(**v) for k, v in totals.items()}, order_count=0)


@router.post("/remove-order", response_model=RemoveOrderResponse)
async def remove_order(request: RemoveOrderRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    name = request.name.strip()
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    deleted = await db.delete_user_today_vote(int(u["id"]))
    if not deleted:
        raise HTTPException(404, f"No order for '{name}' today")
    if u.get("office_id"):
        await broadcast_votes(u["office_id"])
    return RemoveOrderResponse(success=True, name=name, message=f"Order removed for '{name}'")


@router.post("/place-order", response_model=PlaceOrderForUserResponse)
async def place_order_for_user(request: PlaceOrderForUserRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    name = request.name.strip()
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    office_id = u.get("office_id")
    if not office_id:
        raise HTTPException(400, f"User '{name}' has no office assigned")
    product = await db.get_product_by_id(request.product_id)
    if not product or not product.get("is_active"):
        raise HTTPException(400, "Invalid product")
    if request.qty < 1 or request.qty > product["max_qty"]:
        raise HTTPException(400, f"Quantity must be 1–{product['max_qty']}")
    if await db.has_user_voted_today(int(u["id"])):
        raise HTTPException(409, f"'{name}' already ordered today")
    await db.insert_vote(int(u["id"]), office_id, request.product_id, product["name"], product["emoji"], request.qty)
    await broadcast_votes(office_id)
    return PlaceOrderForUserResponse(success=True, name=name, message=f"Ordered {request.qty}x {product['name']} for '{name}'")


# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=UsersListResponse)
async def list_all_users(office_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    if office_id:
        users = await db.get_users_for_office(office_id)
    else:
        users = await db.get_all_users()
    return UsersListResponse(users=[UserOut(
        id=u["_id"], name=u["name"], role=u.get("role", "user"),
        office_id=u.get("office_id"), company_id=u.get("company_id"),
        position=u.get("position"), is_disabled=u.get("is_disabled", 0),
        nickname=u.get("nickname"),
    ) for u in users])


@router.post("/users/role", response_model=SetUserRoleResponse)
async def set_user_role(request: SetUserRoleRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    u = await db.get_user_by_name(request.name.strip())
    if not u:
        raise HTTPException(404, f"User '{request.name}' not found")
    valid_roles = {"main_admin", "office_admin", "office_hr", "user", "company_admin", "distributor_staff"}
    if request.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    await db.set_user_role(int(u["id"]), request.role)
    return SetUserRoleResponse(success=True, name=request.name, role=request.role, message=f"Role updated to '{request.role}'")


@router.post("/unbind", response_model=UnbindResponse)
async def unbind_user(request: UnbindRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
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
    _require_main_admin(user)
    count = await db.clear_all_tokens(request.office_id)
    return RemoveAllLoginsResponse(success=True, count=count, message=f"Logged out {count} user(s)")


@router.post("/set-user-disabled", response_model=SetUserDisabledResponse)
async def set_user_disabled(request: SetUserDisabledRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    name = request.name.strip()
    u = await db.get_user_by_name(name)
    if not u:
        raise HTTPException(404, f"User '{name}' not found")
    await db.set_user_disabled(int(u["id"]), request.disabled)
    action = "disabled" if request.disabled else "enabled"
    return SetUserDisabledResponse(success=True, name=name, message=f"User '{name}' {action}")


@router.get("/users/pending-password", response_model=PendingPasswordUsersResponse)
async def get_pending_password_users(office_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    users = await db.get_users_without_password(office_id)
    return PendingPasswordUsersResponse(users=users, count=len(users))


@router.put("/users/rename", response_model=UpdateUserNameResponse)
async def rename_user(request: UpdateUserNameRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
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
    _require_main_admin(user)
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


# ── Allowed Names ─────────────────────────────────────────────────────────────

@router.get("/allowed-names", response_model=AllowedNamesResponse)
async def list_allowed_names(office_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    names = await db.get_allowed_names(office_id)
    return AllowedNamesResponse(names=sorted(names))


@router.post("/allowed-names", response_model=AddAllowedNameResponse)
async def add_allowed_name(request: AddAllowedNameRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    office_id = request.office_id
    if not office_id:
        office = await db.get_office_by_slug("implevision")
        office_id = office["id"] if office else None
    if not office_id:
        raise HTTPException(400, "No office specified")
    added = await db.add_allowed_name(name, office_id)
    if not added:
        raise HTTPException(409, f"'{name}' already in allowed list")
    return AddAllowedNameResponse(success=True, name=name, message=f"'{name}' added")


@router.delete("/allowed-names", response_model=RemoveAllowedNameResponse)
async def remove_allowed_name(request: RemoveAllowedNameRequest, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    name = request.name.strip()
    removed = await db.remove_allowed_name(name)
    if not removed:
        raise HTTPException(404, f"'{name}' not in allowed list")
    return RemoveAllowedNameResponse(success=True, name=name, message=f"'{name}' removed")


# ── Admin Stats ────────────────────────────────────────────────────────────────

@router.get("/admin/stats/daily", response_model=StatsRangeResponse)
async def admin_get_daily_stats(start: str, end: str, office_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    if end < start:
        raise HTTPException(400, "end must be >= start")
    rows = await db.get_daily_totals_range(start, end, office_id)
    return StatsRangeResponse(days=[DailyTotals(date=r["date"], tea=r["tea"], coffee=r["coffee"], products=r.get("products", {})) for r in rows])


@router.get("/admin/stats/users/day", response_model=UserOrdersForDateResponse)
async def admin_get_user_stats_for_day(date: str, office_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    rows = await db.get_user_orders_for_date(date, office_id)
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
async def admin_get_stat_user_names(office_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    return UserNamesResponse(names=await db.get_all_user_names(office_id))


@router.get("/admin/stats/user", response_model=UserStatsResponse)
async def admin_get_user_stats_range(name: str, start: str, end: str, office_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    _require_main_admin(user)
    if start < _STATS_MIN_DATE:
        start = _STATS_MIN_DATE
    if end < start:
        raise HTTPException(400, "end must be >= start")
    rows = await db.get_user_stats_range(name, start, end, office_id)
    days = [UserStatsDayEntry(date=r["date"], tea=r["tea"], coffee=r["coffee"],
                              product_name=r.get("product_name", ""), qty=r.get("qty", 0)) for r in rows]
    return UserStatsResponse(name=name, start=start, end=end, days=days,
                             total_tea=sum(d.tea for d in days), total_coffee=sum(d.coffee for d in days),
                             order_days=len(days))
