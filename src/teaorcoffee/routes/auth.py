import secrets
import bcrypt
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from src.teaorcoffee.models.schema import (
    LoginRequest, LoginResponse,
    CompanyOut, RegisterCompanyRequest, RegisterCompanyResponse,
    DistributorProductOut,
)
from src.teaorcoffee.core.database import db

router = APIRouter(tags=["Authentication"])


# ── Public: active companies / distributors ──────────────────────────────────

@router.get("/companies/active")
async def get_active_companies():
    companies = await db.get_active_companies(mode="company")
    return {"companies": [CompanyOut(id=c["id"], name=c["name"], slug=c["slug"], mode=c["mode"],
                                     address=c.get("address", ""), distributor_id=c.get("distributor_id"), is_active=c["is_active"]) for c in companies]}


@router.get("/distributors/active")
async def get_active_distributors():
    companies = await db.get_active_companies(mode="distributor")
    return {"companies": [CompanyOut(id=c["id"], name=c["name"], slug=c["slug"], mode=c["mode"],
                                     address=c.get("address", ""), distributor_id=c.get("distributor_id"), is_active=c["is_active"]) for c in companies]}


@router.get("/distributors/{distributor_id}/products")
async def get_distributor_products_public(distributor_id: str):
    """Public catalog preview — used by the registration page's product checklist."""
    distributor = await db.get_company_by_id(distributor_id)
    if not distributor or distributor.get("mode") != "distributor":
        raise HTTPException(404, "Distributor not found")
    products = await db.get_distributor_products(distributor_id)
    return {"products": [DistributorProductOut(id=p["id"], name=p["name"], emoji=p["emoji"],
                                               current_price=p.get("current_price", 0), max_qty=p["max_qty"],
                                               is_active=p.get("is_active", True)) for p in products]}


# ── Self-serve company registration (public, no approval) ───────────────────

@router.post("/register-company", response_model=RegisterCompanyResponse)
async def register_company(request: RegisterCompanyRequest):
    return await register_company_impl(request)


async def register_company_impl(request: RegisterCompanyRequest) -> RegisterCompanyResponse:
    name = request.name.strip()
    slug = request.slug.strip().lower().replace(" ", "-")
    admin_name = request.admin_name.strip()
    address = request.address.strip()
    if not name or not slug or not admin_name:
        raise HTTPException(400, "Company name, slug, and admin name are required.")
    if not address:
        raise HTTPException(400, "Address is required — it's what distinguishes this branch.")
    if request.mode not in ("company", "distributor"):
        raise HTTPException(400, "mode must be 'company' or 'distributor'.")
    if await db.get_user_by_name(admin_name):
        raise HTTPException(409, f"User '{admin_name}' already exists.")

    distributor_id = None
    if request.mode == "company":
        if not request.distributor_id:
            raise HTTPException(400, "distributor_id is required when mode='company'.")
        distributor = await db.get_company_by_id(request.distributor_id)
        if not distributor or distributor.get("mode") != "distributor" or not distributor.get("is_active"):
            raise HTTPException(400, "Invalid or inactive distributor selected.")
        distributor_id = request.distributor_id

    # A new branch — never reuses an existing row, even if the name matches another branch
    company_id = await db.create_company_branch(name, slug, mode=request.mode, address=address,
                                                 distributor_id=distributor_id)

    created = await db.add_company_member(admin_name, company_id, "company_admin")
    if not created:
        raise HTTPException(409, f"User '{admin_name}' already exists.")
    admin_user = await db.get_user_by_name(admin_name)
    if request.admin_password:
        password_hash = bcrypt.hashpw(request.admin_password.encode(), bcrypt.gensalt()).decode()
        await db.set_password_hash(int(admin_user["id"]), password_hash)

    await db.add_company_members(request.manager_names, company_id, "manager")
    await db.add_company_members(request.hr_names, company_id, "hr")
    staff_role = "employee" if request.mode == "company" else "distributor_boy"
    await db.add_company_members(request.staff_names, company_id, staff_role)

    if request.mode == "company" and request.new_products:
        for item in request.new_products:
            product_name = item.name.strip()
            if not product_name or item.price < 0:
                continue
            product_id, _ = await db.add_distributor_product(
                distributor_id, product_name, "🛒", item.price, max_qty=2,
            )
            await db.enable_company_product(company_id, product_id)

    return RegisterCompanyResponse(
        success=True, company_id=company_id, name=name,
        message=f"'{name}' registered successfully. Sign in as '{admin_name}' to get started.",
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    user = await db.get_user_by_name(name) or await db.get_user_by_nickname(name)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Name not in allowed list")

    if not int(user["is_active"]) or int(user.get("is_disabled", 0)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    user_role = user.get("role", "employee")
    user_company_id = user.get("company_id")

    company = await db.get_company_by_id(user_company_id) if user_company_id else None
    if company and not company.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your company has been deactivated")

    # Company check: if company_id provided, user must belong to that company (super_admin bypasses)
    if request.company_id and user_role != "super_admin":
        if user_company_id != request.company_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="User does not belong to the selected company")

    stored_hash = user.get("password_hash")
    display_name = user["name"]

    if not stored_hash:
        if not request.password:
            return LoginResponse(success=False, name=display_name, message="Password setup required",
                                 password_required=True, nickname=user.get("nickname"),
                                 role=user_role)
        new_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
        await db.set_password_hash(int(user["id"]), new_hash)
    else:
        if not request.password:
            return LoginResponse(success=False, name=display_name, message="Password required",
                                 password_required=True, nickname=user.get("nickname"),
                                 role=user_role)
        if not bcrypt.checkpw(request.password.encode(), stored_hash.encode()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

    token = secrets.token_urlsafe(32)
    await db.update_user_token(int(user["id"]), token, datetime.now().isoformat())

    return LoginResponse(
        success=True,
        name=display_name,
        message=f"Welcome {display_name}!",
        token=token,
        nickname=user.get("nickname"),
        role=user_role,
        company_id=user_company_id,
        company_name=company["name"] if company else None,
        company_mode=company["mode"] if company else None,
    )
