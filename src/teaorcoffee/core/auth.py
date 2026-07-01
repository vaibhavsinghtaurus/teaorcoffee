from fastapi import Request, HTTPException, status, WebSocket
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import AuthUser


async def get_current_user(request: Request) -> AuthUser:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    token = auth_header[7:]
    return await _resolve_token(token)


async def get_current_user_from_websocket(websocket: WebSocket) -> AuthUser:
    token = websocket.query_params.get("token", "")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="WebSocket auth failed.")
    return await _resolve_token(token)


async def _resolve_token(token: str) -> AuthUser:
    user = await db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    if not user.get("password_hash"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="password_setup_required")
    if user.get("role") != "super_admin" and user.get("company_id"):
        company = await db.get_company_by_id(user["company_id"])
        if company and not company.get("is_active", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your company has been deactivated.")
    return AuthUser(
        id=int(user["id"]),
        name=user["name"],
        token=user["session_token"],
        role=user.get("role", "employee"),
        company_id=user.get("company_id"),
        nickname=user.get("nickname"),
    )


def require_role(user: AuthUser, *roles: str):
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")


def require_company_admin_or_manager(user: AuthUser):
    require_role(user, "super_admin", "company_admin", "manager")
