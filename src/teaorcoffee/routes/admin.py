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
    AllowedNamesResponse,
    AddAllowedNameRequest,
    AddAllowedNameResponse,
    RemoveAllowedNameRequest,
    RemoveAllowedNameResponse,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

router = APIRouter(tags=["Admin"])


@router.post("/reset", response_model=VotesResponse)
async def reset_votes(request: ResetRequest):
    """Clear all votes but preserve session tokens for authenticated users"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

    await db.delete_all_votes()
    await broadcast_votes()
    return {"tea": 0, "coffee": 0}


@router.post("/unbind", response_model=UnbindResponse)
async def unbind_user(request: UnbindRequest):
    """Remove session token from a user by name, forcing them to log in again"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

    count = await db.clear_all_tokens()
    return RemoveAllLoginsResponse(success=True, count=count, message=f"Logged out {count} user(s)")


@router.post("/set-user-disabled", response_model=SetUserDisabledResponse)
async def set_user_disabled(request: SetUserDisabledRequest):
    """Enable or disable a user's ability to log in"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

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


@router.get("/allowed-names", response_model=AllowedNamesResponse)
async def list_allowed_names(password: str):
    """List all names in the allowed_names collection"""
    if password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

    names = await db.get_allowed_names()
    return AllowedNamesResponse(names=sorted(names))


@router.post("/allowed-names", response_model=AddAllowedNameResponse)
async def add_allowed_name(request: AddAllowedNameRequest):
    """Add a name to allowed_names and create their user account"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    added = await db.add_allowed_name(name)
    if not added:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"'{name}' is already in the allowed list")

    return AddAllowedNameResponse(success=True, name=name, message=f"'{name}' added and user account created")


@router.delete("/allowed-names", response_model=RemoveAllowedNameResponse)
async def remove_allowed_name(request: RemoveAllowedNameRequest):
    """Remove a name from allowed_names (existing user record is preserved)"""
    if request.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    removed = await db.remove_allowed_name(name)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"'{name}' not found in allowed list")

    return RemoveAllowedNameResponse(success=True, name=name, message=f"'{name}' removed from allowed list")
