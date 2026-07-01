"""Employee-facing product list — the calling user's company's enabled distributor products."""
from fastapi import APIRouter, Depends

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import AuthUser, CompanyProductOut

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
async def list_my_products(user: AuthUser = Depends(get_current_user)):
    if not user.company_id:
        return {"products": []}
    rows = await db.get_company_products(user.company_id, enabled_only=True)
    return {"products": [CompanyProductOut(**r) for r in rows]}
