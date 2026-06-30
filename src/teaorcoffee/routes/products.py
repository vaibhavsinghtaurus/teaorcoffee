"""Product management — admin and HR can add/edit/remove products per office."""
from fastapi import APIRouter, HTTPException, Depends

from src.teaorcoffee.core.auth import get_current_user, require_role
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    AuthUser, ProductOut,
    AddProductRequest, UpdateProductRequest, ProductActiveRequest,
)

router = APIRouter(prefix="/products", tags=["Products"])

_CAN_MANAGE = ("main_admin", "office_admin", "office_hr")


def _check_can_manage(user: AuthUser) -> str:
    require_role(user, *_CAN_MANAGE)
    if not user.office_id:
        raise HTTPException(400, "No office assigned")
    return user.office_id


@router.get("")
async def list_products(user: AuthUser = Depends(get_current_user)):
    office_id = user.office_id
    if not office_id:
        return {"products": []}
    is_admin = user.role in _CAN_MANAGE
    prods = await db.get_products(office_id, include_inactive=is_admin)
    return {"products": [ProductOut(id=p["id"], name=p["name"], emoji=p["emoji"],
                                    max_qty=p["max_qty"], is_active=p.get("is_active", True),
                                    sort_order=p.get("sort_order", 0)) for p in prods]}


@router.post("")
async def add_product(request: AddProductRequest, user: AuthUser = Depends(get_current_user)):
    office_id = _check_can_manage(user)
    # Validate office ownership (office_admin can only add to their own office)
    if user.role != "main_admin" and request.office_id != office_id:
        raise HTTPException(403, "Cannot add products to another office")
    name = request.name.strip()
    emoji = request.emoji.strip() or "🍶"
    if not name:
        raise HTTPException(400, "Product name required")
    if request.max_qty < 1:
        raise HTTPException(400, "max_qty must be >= 1")
    product_id, created = await db.add_product(request.office_id, name, emoji, request.max_qty)
    return {"success": True, "product_id": product_id, "created": created,
            "message": f"Product '{name}' {'created' if created else 'already exists'}"}


@router.put("")
async def update_product(request: UpdateProductRequest, user: AuthUser = Depends(get_current_user)):
    _check_can_manage(user)
    name = request.name.strip()
    if not name:
        raise HTTPException(400, "Product name required")
    if request.max_qty < 1:
        raise HTTPException(400, "max_qty must be >= 1")
    updated = await db.update_product(request.product_id, name, request.emoji.strip() or "🍶", request.max_qty)
    if not updated:
        raise HTTPException(404, "Product not found")
    return {"success": True, "message": f"Product updated to '{name}'"}


@router.post("/active")
async def set_product_active(request: ProductActiveRequest, user: AuthUser = Depends(get_current_user)):
    _check_can_manage(user)
    updated = await db.set_product_active(request.product_id, request.is_active)
    if not updated:
        raise HTTPException(404, "Product not found")
    action = "activated" if request.is_active else "deactivated"
    return {"success": True, "message": f"Product {action}"}
