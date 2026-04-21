from fastapi import APIRouter, HTTPException, status

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.models.schema import (
    VotesResponse,
    UnbindRequest,
    UnbindResponse,
    ResetRequest,
    RemoveOrderRequest,
    RemoveOrderResponse,
    RemoveAllLoginsRequest,
    RemoveAllLoginsResponse,
    SetUserDisabledRequest,
    SetUserDisabledResponse,
    PendingPasswordUsersResponse,
    UpdateUserNameRequest,
    UpdateUserNameResponse,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

router = APIRouter(tags=["Admin"])


@router.post("/reset", response_model=VotesResponse)
async def reset_votes(request: ResetRequest):
    """Clear all votes but preserve session tokens for authenticated users"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz")

    await db.delete_all_votes()
    await broadcast_votes()
    return {"tea": 0, "coffee": 0}


@router.post("/unbind", response_model=UnbindResponse)
async def unbind_user(request: UnbindRequest):
    """Remove session token from a user by name, forcing them to log in again"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz")

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    user = await db.get_user_by_name(name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{name}' not found in allowed list",
        )

    if not user["session_token"]:
        return UnbindResponse(success=True, name=name, message=f"User '{name}' has no active session")

    await db.update_user_token(int(user["id"]), None)
    return UnbindResponse(success=True, name=name, message=f"Session removed for user '{name}'")


@router.post("/remove-order", response_model=RemoveOrderResponse)
async def remove_order(request: RemoveOrderRequest):
    """Remove today's order for a user by name"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz")

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    user = await db.get_user_by_name(name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{name}' not found in allowed list",
        )

    deleted = await db.delete_user_today_vote(int(user["id"]))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No order found for '{name}' today",
        )

    await broadcast_votes()
    return RemoveOrderResponse(success=True, name=name, message=f"Order removed for '{name}'")


@router.post("/remove-all-logins", response_model=RemoveAllLoginsResponse)
async def remove_all_logins(request: RemoveAllLoginsRequest):
    """Remove session tokens for all users, forcing everyone to log in again"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz")

    count = await db.clear_all_tokens()
    return RemoveAllLoginsResponse(success=True, count=count, message=f"Logged out {count} user(s)")


@router.post("/set-user-disabled", response_model=SetUserDisabledResponse)
async def set_user_disabled(request: SetUserDisabledRequest):
    """Enable or disable a user's ability to log in"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz")

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    user = await db.get_user_by_name(name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{name}' not found in allowed list",
        )

    await db.set_user_disabled(int(user["id"]), request.disabled)
    action = "disabled" if request.disabled else "enabled"
    return SetUserDisabledResponse(success=True, name=name, message=f"User '{name}' has been {action}")


@router.get("/users/pending-password", response_model=PendingPasswordUsersResponse)
async def get_pending_password_users(password: str):
    """Get users who have not set up their password yet"""
    if password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz")

    users = await db.get_users_without_password()
    return PendingPasswordUsersResponse(users=users, count=len(users))


@router.put("/users/rename", response_model=UpdateUserNameResponse)
async def rename_user(request: UpdateUserNameRequest):
    """Rename a user in the allowed users list"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz")

    old_name = request.old_name.strip()
    new_name = request.new_name.strip()

    if not old_name or not new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Names cannot be empty")

    existing = await db.get_user_by_name(new_name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User '{new_name}' already exists")

    updated = await db.update_user_name(old_name, new_name)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{old_name}' not found")

    return UpdateUserNameResponse(success=True, old_name=old_name, new_name=new_name, message=f"'{old_name}' renamed to '{new_name}'")
