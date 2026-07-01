import secrets
import bcrypt
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from src.teaorcoffee.models.schema import (
    LoginRequest, LoginResponse,
    SetupStatusResponse, SetupRequest, SetupResponse,
    OfficeRequestCreate, OfficeRequestOut,
    OfficeOut,
)
from src.teaorcoffee.core.database import db

router = APIRouter(tags=["Authentication"])


# ── Setup ─────────────────────────────────────────────────────────────────────

@router.get("/setup/status", response_model=SetupStatusResponse)
async def setup_status():
    """Returns whether initial main admin setup is still needed."""
    return SetupStatusResponse(needs_setup=not await db.has_main_admin())


@router.post("/setup", response_model=SetupResponse)
async def setup_main_admin(request: SetupRequest):
    """Create the first main admin. Fails if one already exists."""
    if await db.has_main_admin():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Main admin already exists.")
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty.")
    if not request.password or len(request.password) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 4 characters.")

    user = await db.get_user_by_name(name)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"'{name}' is not in the allowed names list. Add them first or use an existing name.")

    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    await db.set_password_hash(int(user["id"]), password_hash)
    await db.set_user_role(int(user["id"]), "main_admin")
    return SetupResponse(success=True, message=f"Main admin '{name}' created successfully.")


# ── Public: active offices (for login dropdown) ───────────────────────────────

@router.get("/offices/active")
async def get_active_offices():
    offices = await db.get_active_offices()
    return {"offices": [OfficeOut(id=o["id"], name=o["name"], slug=o["slug"], is_active=o["is_active"]) for o in offices]}


# ── Office request (public, no auth) ─────────────────────────────────────────

@router.post("/request-office")
async def request_office(request: OfficeRequestCreate):
    office_name = request.office_name.strip()
    requester_name = request.requester_name.strip()
    if not office_name or not requester_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Office name and requester name are required.")
    request_id = await db.create_office_request(office_name, requester_name, request.contact_info.strip())
    return {"success": True, "request_id": request_id,
            "message": "Office addition request submitted. The main admin will review it."}


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

    # Office check: if office_id provided, user must belong to that office
    # (main_admin and distributor users bypass this check)
    user_role = user.get("role", "user")
    user_company = user.get("company_id")
    if request.office_id and user_role != "main_admin" and not user_company:
        if user.get("office_id") != request.office_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="User does not belong to the selected office")

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

    office_name = None
    office_id = user.get("office_id")
    if office_id:
        office = await db.get_office_by_id(office_id)
        if office:
            office_name = office["name"]

    return LoginResponse(
        success=True,
        name=display_name,
        message=f"Welcome {display_name}!",
        token=token,
        nickname=user.get("nickname"),
        role=user_role,
        office_id=office_id,
        office_name=office_name,
        company_id=user.get("company_id"),
        position=user.get("position"),
    )
