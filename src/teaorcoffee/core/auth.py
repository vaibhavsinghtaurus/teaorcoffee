from fastapi import Request, HTTPException, status, WebSocket
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import AuthUser


async def get_current_user(request: Request) -> AuthUser:
    """
    FastAPI dependency to validate authenticated user by session token.
    Expects: Authorization: Bearer <token>
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first.",
        )
    token = auth_header[7:]

    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT id, name, session_token FROM allowed_users WHERE session_token = ? AND is_active = 1",
            (token,),
        )
        user = await cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please login first.",
            )

        return AuthUser(id=user["id"], name=user["name"], token=user["session_token"])


async def get_current_user_from_websocket(websocket: WebSocket) -> AuthUser:
    """
    Authenticate WebSocket connection by session token query param.
    Expects: /ws/votes?token=<token>
    """
    token = websocket.query_params.get("token", "")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket authentication failed",
        )

    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT id, name, session_token FROM allowed_users WHERE session_token = ? AND is_active = 1",
            (token,),
        )
        user = await cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="WebSocket authentication failed",
            )

        return AuthUser(id=user["id"], name=user["name"], token=user["session_token"])
