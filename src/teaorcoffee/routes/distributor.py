"""Distributor routes: company, position, and staff management."""
from fastapi import APIRouter, HTTPException, Depends

from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    AuthUser,
    DistributorCompanyOut, CreateCompanyRequest,
    PositionOut, AddPositionRequest, RemovePositionRequest,
    DistributorStaffOut, AddStaffRequest, RemoveStaffRequest,
    OrdersBreakdownResponse, OrderDetail, ProductTotal,
)

router = APIRouter(prefix="/distributor", tags=["Distributor"])

_ADMIN_ROLES = ("main_admin",)
_COMPANY_ROLES = ("main_admin", "company_admin")
_VIEW_ROLES = ("main_admin", "company_admin", "distributor_staff")


def _check_can_view(user: AuthUser):
    require_role(user, *_VIEW_ROLES)


def _check_company_admin(user: AuthUser):
    require_role(user, *_COMPANY_ROLES)


def _check_admin(user: AuthUser):
    require_role(user, *_ADMIN_ROLES)


# ── Companies ─────────────────────────────────────────────────────────────────

@router.get("/companies")
async def list_companies(user: AuthUser = Depends(get_current_user)):
    _check_can_view(user)
    # Company admin / staff only see their own company
    if user.role in ("company_admin", "distributor_staff") and user.company_id:
        companies = await db.get_distributor_companies()
        companies = [c for c in companies if c["id"] == user.company_id]
    else:
        office_id = user.office_id
        companies = await db.get_distributor_companies(office_id)
    return {"companies": [DistributorCompanyOut(id=c["id"], name=c["name"],
                                                 office_id=c["office_id"], is_active=c.get("is_active", True)) for c in companies]}


@router.post("/companies")
async def create_company(request: CreateCompanyRequest, user: AuthUser = Depends(get_current_user)):
    _check_admin(user)
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Company name required")
    company_id, created = await db.create_distributor_company(name, request.office_id)
    if not created:
        raise HTTPException(409, f"Company '{name}' already exists for this office")
    return {"success": True, "company_id": company_id, "message": f"Company '{name}' created"}


@router.post("/companies/active")
async def set_company_active(company_id: str, is_active: bool, user: AuthUser = Depends(get_current_user)):
    _check_admin(user)
    updated = await db.set_company_active(company_id, is_active)
    if not updated:
        raise HTTPException(404, "Company not found")
    return {"success": True, "message": f"Company {'activated' if is_active else 'deactivated'}"}


# ── Positions ─────────────────────────────────────────────────────────────────

@router.get("/companies/{company_id}/positions")
async def list_positions(company_id: str, user: AuthUser = Depends(get_current_user)):
    _check_can_view(user)
    positions = await db.get_positions(company_id)
    return {"positions": [PositionOut(id=p["id"], name=p["name"], level=p["level"]) for p in positions]}


@router.post("/positions")
async def add_position(request: AddPositionRequest, user: AuthUser = Depends(get_current_user)):
    _check_company_admin(user)
    # Company admin can only manage their own company
    if user.role == "company_admin" and user.company_id != request.company_id:
        raise HTTPException(403, "Cannot manage another company")
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Position name required")
    pos_id, created = await db.add_position(request.company_id, name, request.level)
    if not created:
        raise HTTPException(409, f"Position '{name}' already exists")
    return {"success": True, "position_id": pos_id, "message": f"Position '{name}' added"}


@router.delete("/positions")
async def remove_position(request: RemovePositionRequest, user: AuthUser = Depends(get_current_user)):
    _check_company_admin(user)
    removed = await db.remove_position(request.position_id)
    if not removed:
        raise HTTPException(404, "Position not found")
    return {"success": True, "message": "Position removed"}


# ── Staff ─────────────────────────────────────────────────────────────────────

@router.get("/companies/{company_id}/staff")
async def list_staff(company_id: str, user: AuthUser = Depends(get_current_user)):
    _check_can_view(user)
    if user.role in ("company_admin", "distributor_staff") and user.company_id != company_id:
        raise HTTPException(403, "Access denied")
    staff = await db.get_distributor_staff(company_id)
    return {"staff": [DistributorStaffOut(id=s["_id"], name=s["name"], role=s.get("role", "distributor_staff"),
                                          position=s.get("position"), is_disabled=s.get("is_disabled", 0)) for s in staff]}


@router.post("/staff")
async def add_staff(request: AddStaffRequest, user: AuthUser = Depends(get_current_user)):
    _check_company_admin(user)
    if user.role == "company_admin" and user.company_id != request.company_id:
        raise HTTPException(403, "Cannot add staff to another company")
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Name required")
    valid_roles = {"company_admin", "distributor_staff"}
    if request.role not in valid_roles:
        raise HTTPException(400, f"Role must be one of: {', '.join(valid_roles)}")
    added = await db.add_distributor_staff(name, request.company_id, request.role, request.position.strip())
    if not added:
        raise HTTPException(409, f"User '{name}' already exists")
    return {"success": True, "message": f"'{name}' added as {request.position}"}


@router.delete("/staff")
async def remove_staff(request: RemoveStaffRequest, user: AuthUser = Depends(get_current_user)):
    _check_company_admin(user)
    removed = await db.remove_distributor_staff(request.user_id)
    if not removed:
        raise HTTPException(404, "Staff member not found")
    return {"success": True, "message": "Staff member removed"}


# ── Orders (read-only view for distributor) ───────────────────────────────────

@router.get("/orders")
async def distributor_get_orders(user: AuthUser = Depends(get_current_user)):
    _check_can_view(user)
    # Find office_id from company
    office_id = None
    if user.company_id:
        company = await db.get_distributor_company_by_id(user.company_id)
        if company:
            office_id = company["office_id"]
    elif user.office_id:
        office_id = user.office_id

    if not office_id:
        return OrdersBreakdownResponse(orders=[], totals={}, order_count=0)

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
