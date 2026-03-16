from fastapi import APIRouter, HTTPException, Request, status
from datetime import datetime

from src.teaorcoffee.models.schema import LoginRequest, LoginResponse
from src.teaorcoffee.core.database import db

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request):
    """
    Authenticate user by name and bind to IP address

    Rules:
    1. Name must be in allowed list
    2. If name has no IP: bind to current IP
    3. If name has IP: must match current IP
    4. If IP already bound to different name: reject
    """
    client_ip = req.headers.get("x-forwarded-for", req.client.host).split(",")[0].strip()
    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty"
        )

    async with db.get_connection() as conn:
        # Check if name exists in allowed users
        cursor = await conn.execute(
            "SELECT id, name, ip_address, is_active FROM allowed_users WHERE name = ?",
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

        user_id = user["id"]
        existing_ip = user["ip_address"]

        # Case 1: User has no IP yet - bind to current IP
        if existing_ip is None:
            # Check if this IP is already bound to another user
            cursor = await conn.execute(
                "SELECT name FROM allowed_users WHERE ip_address = ? AND id != ?",
                (client_ip, user_id),
            )
            conflicting_user = await cursor.fetchone()

            if conflicting_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"IP already associated with user '{conflicting_user['name']}'",
                )

            # Bind IP to this user
            await conn.execute(
                "UPDATE allowed_users SET ip_address = ?, last_login_at = ? WHERE id = ?",
                (client_ip, datetime.now().isoformat(), user_id),
            )
            await conn.commit()

            return LoginResponse(
                success=True,
                name=name,
                message=f"Welcome {name}! IP address registered.",
            )

        # Case 2: User has IP - verify it matches
        if existing_ip != client_ip:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP mismatch: '{name}' can only login from registered IP",
            )

        # Update last login time
        await conn.execute(
            "UPDATE allowed_users SET last_login_at = ? WHERE id = ?",
            (datetime.now().isoformat(), user_id),
        )
        await conn.commit()

        return LoginResponse(success=True, name=name, message=f"Welcome back, {name}!")
