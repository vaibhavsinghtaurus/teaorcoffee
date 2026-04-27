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

    user = await db.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first.",
        )

    if not user.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="password_setup_required",
        )

    return AuthUser(id=int(user["id"]), name=user["name"], token=user["session_token"], nickname=user.get("nickname"))


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

    user = await db.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket authentication failed",
        )

    if not user.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="password_setup_required",
        )

    return AuthUser(id=int(user["id"]), name=user["name"], token=user["session_token"], nickname=user.get("nickname"))
