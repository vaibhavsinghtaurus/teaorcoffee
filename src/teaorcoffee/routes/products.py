"""Employee-facing product list — the calling user's company's enabled distributor products."""
from fastapi import APIRouter, Depends

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import AuthUser, CompanyProductOut, ProductNameSuggestion, ProductSearchResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
async def list_my_products(user: AuthUser = Depends(get_current_user)):
    if not user.company_id:
        return {"products": []}
    rows = await db.get_company_products(user.company_id, enabled_only=True)
    return {"products": [CompanyProductOut(**r) for r in rows]}


@router.get("/search-names", response_model=ProductSearchResponse)
async def search_product_names(q: str = ""):
    """Public — powers the debounced autocomplete on every "add a product" form (distributor
    registration, company registration, and a distributor's own catalog), so a name/price
    that's already in use elsewhere can be reused instead of retyped from scratch."""
    query = q.strip()
    if len(query) < 2:
        return ProductSearchResponse(products=[])
    results = await db.search_distributor_product_names(query)
    return ProductSearchResponse(products=[ProductNameSuggestion(**r) for r in results])
