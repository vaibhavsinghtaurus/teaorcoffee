"""Distributor routes: own product catalog + pricing, buyer companies, order summary, deliveries."""
from fastapi import APIRouter, HTTPException, Depends

from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.core.database import db
from src.teaorcoffee.utils.broadcast import broadcast_votes
from src.teaorcoffee.models.schema import (
    AuthUser,
    DistributorProductOut, AddDistributorProductRequest, UpdateDistributorProductRequest,
    UpdateProductPriceRequest, ProductActiveRequest, PriceHistoryResponse, PriceHistoryEntry,
    AddCompanyMemberRequest, AddCompanyMemberResponse, RemoveCompanyMemberRequest,
    UsersListResponse, UserOut,
    DistributorOrderSummaryResponse, ProductSummaryRow, CompanySummaryRow, UserSummaryRow,
    PendingOrdersResponse, PendingOrderRow, DeliverOrderResponse,
    CompanyOut, SetMyAddressRequest,
)

router = APIRouter(prefix="/distributor", tags=["Distributor"])

_MANAGE_ROLES = ("super_admin", "company_admin", "manager")
_VIEW_ROLES = ("super_admin", "company_admin", "manager", "hr", "distributor_boy")
_ASSIGNABLE_ROLES = {"company_admin", "manager", "hr", "distributor_boy"}


def _resolve_scope(user: AuthUser, requested_company_id: str | None = None) -> str:
    """Resolve which distributor company a request applies to. Non-super-admins are
    always scoped to their own company; super_admin must pass an explicit id."""
    if user.role == "super_admin":
        if not requested_company_id:
            raise HTTPException(400, "company_id is required for super_admin")
        return requested_company_id
    if not user.company_id:
        raise HTTPException(400, "No company assigned")
    return user.company_id


def _check_manage(user: AuthUser, requested_company_id: str | None = None) -> str:
    require_role(user, *_MANAGE_ROLES)
    return _resolve_scope(user, requested_company_id)


def _check_view(user: AuthUser, requested_company_id: str | None = None) -> str:
    require_role(user, *_VIEW_ROLES)
    return _resolve_scope(user, requested_company_id)


async def _verify_product_scope(user: AuthUser, product_id: str):
    """For non-super-admins, ensure the product actually belongs to their own company."""
    if user.role == "super_admin":
        return
    product = await db.get_distributor_product_by_id(product_id)
    if not product or product["company_id"] != user.company_id:
        raise HTTPException(404, "Product not found")


# ── Own branch profile (address) ──────────────────────────────────────────────

@router.get("/company")
async def get_my_company(company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    scope = _check_view(user, company_id)
    c = await db.get_company_by_id(scope)
    if not c:
        raise HTTPException(404, "Company not found")
    return CompanyOut(id=c["id"], name=c["name"], slug=c["slug"], mode=c["mode"],
                      address=c.get("address", ""), distributor_id=c.get("distributor_id"), is_active=c["is_active"])


@router.put("/company/address")
async def set_my_address(request: SetMyAddressRequest, user: AuthUser = Depends(get_current_user)):
    require_role(user, *_MANAGE_ROLES)
    if not user.company_id:
        raise HTTPException(400, "No company assigned")
    address = request.address.strip()
    if not address:
        raise HTTPException(400, "Address cannot be empty")
    await db.update_company_address(user.company_id, address)
    return {"success": True, "message": "Address updated"}


# ── Buyer companies ───────────────────────────────────────────────────────────

@router.get("/buyers")
async def list_buyers(company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    scope = _check_view(user, company_id)
    all_companies = await db.get_all_companies()
    buyers = [c for c in all_companies if c.get("distributor_id") == scope]
    return {"companies": [CompanyOut(id=c["id"], name=c["name"], slug=c["slug"], mode=c["mode"],
                                     address=c.get("address", ""), distributor_id=c.get("distributor_id"), is_active=c["is_active"]) for c in buyers]}


# ── Products & Pricing ────────────────────────────────────────────────────────

@router.get("/products")
async def list_products(company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    scope = _check_view(user, company_id)
    prods = await db.get_distributor_products(scope, include_inactive=True)
    return {"products": [DistributorProductOut(id=p["id"], name=p["name"], emoji=p["emoji"],
                                               current_price=p.get("current_price", 0), max_qty=p["max_qty"],
                                               is_active=p.get("is_active", True)) for p in prods]}


@router.post("/products")
async def add_product(request: AddDistributorProductRequest, user: AuthUser = Depends(get_current_user)):
    scope = _check_manage(user, request.company_id)
    name = request.name.strip()
    emoji = request.emoji.strip() or "🛒"
    if not name:
        raise HTTPException(400, "Product name required")
    if request.max_qty < 1:
        raise HTTPException(400, "max_qty must be >= 1")
    if request.price < 0:
        raise HTTPException(400, "price must be >= 0")
    product_id, created = await db.add_distributor_product(scope, name, emoji, request.price, request.max_qty, user.id)
    return {"success": True, "product_id": product_id, "created": created,
            "message": f"Product '{name}' {'created' if created else 'already exists'}"}


@router.put("/products")
async def update_product(request: UpdateDistributorProductRequest, user: AuthUser = Depends(get_current_user)):
    require_role(user, *_MANAGE_ROLES)
    await _verify_product_scope(user, request.product_id)
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Product name required")
    if request.max_qty < 1:
        raise HTTPException(400, "max_qty must be >= 1")
    updated = await db.update_distributor_product(request.product_id, name, request.emoji.strip() or "🛒", request.max_qty)
    if not updated:
        raise HTTPException(404, "Product not found")
    return {"success": True, "message": f"Product updated to '{name}'"}


@router.put("/products/price")
async def update_price(request: UpdateProductPriceRequest, user: AuthUser = Depends(get_current_user)):
    require_role(user, *_MANAGE_ROLES)
    await _verify_product_scope(user, request.product_id)
    if request.new_price < 0:
        raise HTTPException(400, "price must be >= 0")
    updated = await db.update_distributor_product_price(request.product_id, request.new_price, user.id)
    if not updated:
        raise HTTPException(404, "Product not found")
    return {"success": True, "message": f"Price updated to ₹{request.new_price}"}


@router.get("/products/{product_id}/price-history", response_model=PriceHistoryResponse)
async def price_history(product_id: str, user: AuthUser = Depends(get_current_user)):
    require_role(user, *_VIEW_ROLES)
    await _verify_product_scope(user, product_id)
    history = await db.get_price_history(product_id)
    return PriceHistoryResponse(history=[PriceHistoryEntry(
        id=h["id"], price=h["price"], changed_by_user_id=h.get("changed_by_user_id"), effective_at=h["effective_at"],
    ) for h in history])


@router.post("/products/active")
async def set_product_active(request: ProductActiveRequest, user: AuthUser = Depends(get_current_user)):
    require_role(user, *_MANAGE_ROLES)
    await _verify_product_scope(user, request.product_id)
    updated = await db.set_distributor_product_active(request.product_id, request.is_active)
    if not updated:
        raise HTTPException(404, "Product not found")
    action = "activated" if request.is_active else "removed"
    return {"success": True, "message": f"Product {action}"}


# ── Staff ─────────────────────────────────────────────────────────────────────

@router.get("/staff", response_model=UsersListResponse)
async def list_staff(company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    scope = _check_view(user, company_id)
    staff = await db.get_users_for_company(scope)
    return UsersListResponse(users=[UserOut(
        id=s["_id"], name=s["name"], role=s.get("role", "distributor_boy"),
        company_id=s.get("company_id"), is_disabled=s.get("is_disabled", 0), nickname=s.get("nickname"),
    ) for s in staff])


@router.post("/staff", response_model=AddCompanyMemberResponse)
async def add_staff(request: AddCompanyMemberRequest, user: AuthUser = Depends(get_current_user)):
    scope = _check_manage(user, request.company_id)
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Name required")
    if request.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(400, f"Role must be one of: {', '.join(_ASSIGNABLE_ROLES)}")
    added = await db.add_company_member(name, scope, request.role)
    if not added:
        raise HTTPException(409, f"User '{name}' already exists")
    return AddCompanyMemberResponse(success=True, name=name, message=f"'{name}' added as {request.role}")


@router.delete("/staff")
async def remove_staff(request: RemoveCompanyMemberRequest, user: AuthUser = Depends(get_current_user)):
    require_role(user, *_MANAGE_ROLES)
    target = await db.users.find_one({"_id": request.user_id})
    if not target:
        raise HTTPException(404, "Staff member not found")
    if user.role != "super_admin" and target.get("company_id") != user.company_id:
        raise HTTPException(404, "Staff member not found in your company")
    removed = await db.remove_company_member(request.user_id)
    if not removed:
        raise HTTPException(404, "Staff member not found")
    return {"success": True, "message": "Staff member removed"}


# ── Order Summary (delivered vs pending) ──────────────────────────────────────

@router.get("/orders/summary", response_model=DistributorOrderSummaryResponse)
async def order_summary(date: str | None = None, company_id: str | None = None, user: AuthUser = Depends(get_current_user)):
    scope = _check_view(user, company_id)
    summary = await db.get_distributor_order_summary(scope, date)
    return DistributorOrderSummaryResponse(
        by_product=[ProductSummaryRow(**r) for r in summary["by_product"]],
        by_company=[CompanySummaryRow(**r) for r in summary["by_company"]],
        by_user=[UserSummaryRow(**r) for r in summary["by_user"]],
    )


# ── Deliveries (fulfillment queue) ────────────────────────────────────────────

@router.get("/orders/pending", response_model=PendingOrdersResponse)
async def pending_orders(buyer_company_id: str | None = None, distributor_id: str | None = None,
                          user: AuthUser = Depends(get_current_user)):
    scope = _check_view(user, distributor_id)
    rows = await db.get_pending_orders_for_distributor(scope, buyer_company_id)
    return PendingOrdersResponse(orders=[PendingOrderRow(
        id=r["_id"], user_name=r["user_name"], company_name=r["company_name"],
        company_address=r.get("company_address", ""), company_id=r["company_id"],
        product_name=r["product_name"], product_emoji=r["product_emoji"], qty=r["qty"], date=r["date"],
    ) for r in rows])


@router.post("/orders/{vote_id}/deliver", response_model=DeliverOrderResponse)
async def deliver_order(vote_id: str, user: AuthUser = Depends(get_current_user)):
    require_role(user, *_VIEW_ROLES)
    vote = await db.get_vote_by_id(vote_id)
    distributor_scope = None if user.role == "super_admin" else user.company_id
    delivered = await db.mark_order_delivered(vote_id, user.id, distributor_company_id=distributor_scope)
    if not delivered:
        raise HTTPException(404, "Pending order not found")
    if vote:
        await broadcast_votes(vote["company_id"])
    return DeliverOrderResponse(success=True, message="Order marked delivered")
