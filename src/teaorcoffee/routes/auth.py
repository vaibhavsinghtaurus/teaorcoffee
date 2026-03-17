import secrets
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from src.teaorcoffee.models.schema import LoginRequest, LoginResponse
from src.teaorcoffee.core.database import db

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user by name and issue a session token.
    Each login generates a new token (previous token is invalidated).
    """
    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty"
        )

    user = await db.get_user_by_name(name)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Name not in allowed list",
        )

    if not int(user["is_active"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    token = secrets.token_urlsafe(32)
    await db.update_user_token(int(user["id"]), token, datetime.now().isoformat())

    return LoginResponse(
        success=True,
        name=name,
        message=f"Welcome {name}!",
        token=token,
    )
