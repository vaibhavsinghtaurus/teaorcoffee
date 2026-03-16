from fastapi import Request, HTTPException, status, WebSocket
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import AuthUser


async def get_current_user(request: Request) -> AuthUser:
    """
    FastAPI dependency to validate authenticated user by IP

    Raises HTTPException if:
    - IP not registered
    - User inactive
    """
    client_ip = request.client.host

    async with db.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT id, name, ip_address
            FROM allowed_users
            WHERE ip_address = ? AND is_active = 1
            """,
            (client_ip,),
        )
        user = await cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please login first.",
            )

        return AuthUser(
            id=user["id"], name=user["name"], ip_address=user["ip_address"]
        )


async def get_current_user_from_websocket(websocket: WebSocket) -> AuthUser:
    """
    Authenticate WebSocket connection by IP
    """
    client_ip = websocket.client.host

    async with db.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT id, name, ip_address
            FROM allowed_users
            WHERE ip_address = ? AND is_active = 1
            """,
            (client_ip,),
        )
        user = await cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="WebSocket authentication failed",
            )

        return AuthUser(
            id=user["id"], name=user["name"], ip_address=user["ip_address"]
        )
