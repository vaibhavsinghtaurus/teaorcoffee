import secrets
import bcrypt
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from src.teaorcoffee.models.schema import LoginRequest, LoginResponse
from src.teaorcoffee.core.database import db

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty"
        )

    user = await db.get_user_by_name(name)

    if not user:
        user = await db.get_user_by_nickname(name)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Name not in allowed list",
        )

    if not int(user["is_active"]) or int(user.get("is_disabled", 0)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    stored_hash = user.get("password_hash")
    display_name = user["name"]

    if not stored_hash:
        # No password set yet — require the client to provide one
        if not request.password:
            return LoginResponse(
                success=False,
                name=display_name,
                message="Password setup required",
                password_required=True,
                nickname=user.get("nickname"),
            )
        # First time setting password — hash and store it
        new_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
        await db.set_password_hash(int(user["id"]), new_hash)
    else:
        # Password already set — validate it
        if not request.password:
            return LoginResponse(
                success=False,
                name=display_name,
                message="Password required",
                password_required=True,
                nickname=user.get("nickname"),
            )
        if not bcrypt.checkpw(request.password.encode(), stored_hash.encode()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
            )

    token = secrets.token_urlsafe(32)
    await db.update_user_token(int(user["id"]), token, datetime.now().isoformat())

    return LoginResponse(
        success=True,
        name=display_name,
        message=f"Welcome {display_name}!",
        token=token,
        nickname=user.get("nickname"),
    )
