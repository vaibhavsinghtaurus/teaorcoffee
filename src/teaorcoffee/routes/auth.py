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

    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT id, name, is_active FROM allowed_users WHERE name = ?",
            (name,),
        )
        user = await cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Name not in allowed list",
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        token = secrets.token_urlsafe(32)

        await conn.execute(
            "UPDATE allowed_users SET session_token = ?, last_login_at = ? WHERE id = ?",
            (token, datetime.now().isoformat(), user["id"]),
        )
        await conn.commit()

        return LoginResponse(
            success=True,
            name=name,
            message=f"Welcome {name}!",
            token=token,
        )
