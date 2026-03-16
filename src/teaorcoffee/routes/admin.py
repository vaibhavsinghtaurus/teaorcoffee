from fastapi import APIRouter, HTTPException, status

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.models.schema import VotesResponse, UnbindRequest, UnbindResponse, ResetRequest, RemoveOrderRequest, RemoveOrderResponse, RemoveAllLoginsRequest, RemoveAllLoginsResponse
from src.teaorcoffee.utils.broadcast import broadcast_votes

router = APIRouter(tags=["Admin"])


@router.post("/reset", response_model=VotesResponse)
async def reset_votes(request: ResetRequest):
    """Clear all votes but preserve IP bindings for authenticated users"""
    if request.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz"
        )

    async with db.get_connection() as conn:
        # Delete all votes from user_votes table
        await conn.execute("DELETE FROM user_votes")
        await conn.commit()

    # Broadcast updated (zero) votes to all connected clients
    await broadcast_votes()

    return {"tea": 0, "coffee": 0}


@router.post("/unbind", response_model=UnbindResponse)
async def unbind_user(request: UnbindRequest):
    """Remove IP binding from a user by name"""
    if request.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz"
        )

    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty"
        )

    async with db.get_connection() as conn:
        # Check if user exists
        cursor = await conn.execute(
            "SELECT id, name, ip_address FROM allowed_users WHERE name = ?", (name,)
        )
        user = await cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{name}' not found in allowed list",
            )

        if user["ip_address"] is None:
            return UnbindResponse(
                success=True,
                name=name,
                message=f"User '{name}' has no IP binding",
            )

        # Remove IP binding
        await conn.execute(
            "UPDATE allowed_users SET ip_address = NULL WHERE id = ?", (user["id"],)
        )
        await conn.commit()

        return UnbindResponse(
            success=True,
            name=name,
            message=f"IP binding removed for user '{name}'",
        )


@router.post("/remove-order", response_model=RemoveOrderResponse)
async def remove_order(request: RemoveOrderRequest):
    """Remove today's order for a user by name"""
    if request.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz"
        )

    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty"
        )

    async with db.get_connection() as conn:
        # Find the user
        cursor = await conn.execute(
            "SELECT id FROM allowed_users WHERE name = ?", (name,)
        )
        user = await cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{name}' not found in allowed list",
            )

        # Check if they have an order today
        cursor = await conn.execute(
            "SELECT id FROM user_votes WHERE user_id = ? AND DATE(voted_at) = DATE('now', 'localtime')",
            (user["id"],),
        )
        vote = await cursor.fetchone()

        if not vote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No order found for '{name}' today",
            )

        await conn.execute(
            "DELETE FROM user_votes WHERE user_id = ? AND DATE(voted_at) = DATE('now', 'localtime')",
            (user["id"],),
        )
        await conn.commit()

    await broadcast_votes()

    return RemoveOrderResponse(
        success=True,
        name=name,
        message=f"Order removed for '{name}'",
    )


@router.post("/remove-all-logins", response_model=RemoveAllLoginsResponse)
async def remove_all_logins(request: RemoveAllLoginsRequest):
    """Remove IP bindings for all users, forcing everyone to log in again"""
    if request.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bhadwa saala randibaaz"
        )

    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "UPDATE allowed_users SET ip_address = NULL WHERE ip_address IS NOT NULL"
        )
        count = cursor.rowcount
        await conn.commit()

    return RemoveAllLoginsResponse(
        success=True,
        count=count,
        message=f"Logged out {count} user(s)",
    )
