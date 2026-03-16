from fastapi import APIRouter, HTTPException, status, Depends

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    VotesResponse,
    VoteMeResponse,
    VoteRequest,
    AuthUser,
    OrdersBreakdownResponse,
    UserOrderDetail,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

router = APIRouter(tags=["Votes"])


@router.get("/votes", response_model=VotesResponse)
async def get_votes(user: AuthUser = Depends(get_current_user)):
    """Get total vote counts from all authenticated users for today"""
    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(tea), 0) as tea, COALESCE(SUM(coffee), 0) as coffee FROM user_votes WHERE DATE(voted_at) = DATE('now', 'localtime')"
        )
        result = await cursor.fetchone()
        return {"tea": result["tea"], "coffee": result["coffee"]}


@router.get("/vote/me", response_model=VoteMeResponse)
async def get_my_vote(user: AuthUser = Depends(get_current_user)):
    """Get current authenticated user's vote for today"""
    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT tea, coffee FROM user_votes WHERE user_id = ? AND DATE(voted_at) = DATE('now', 'localtime')",
            (user.id,)
        )
        vote = await cursor.fetchone()

        if not vote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You have not voted today",
            )

        return {"ip": user.ip_address, "tea": vote["tea"], "coffee": vote["coffee"]}


@router.post("/vote", response_model=VotesResponse, status_code=201)
async def cast_vote(
    vote: VoteRequest, user: AuthUser = Depends(get_current_user)
):
    """Cast a vote for the authenticated user"""
    if vote.tea < 0 or vote.coffee < 0:
        raise HTTPException(400, "Tea and coffee must be >= 0")

    if vote.tea == 0 and vote.coffee == 0:
        raise HTTPException(400, "At least one drink must be ordered")

    # New rule: Either max 2 tea OR 1 coffee, not both
    if vote.tea > 0 and vote.coffee > 0:
        raise HTTPException(400, "You can only order tea OR coffee, not both")

    if vote.tea > 2:
        raise HTTPException(400, "You can order maximum 2 tea")

    if vote.coffee > 1:
        raise HTTPException(400, "You can order maximum 1 coffee")

    async with db.get_connection() as conn:
        # Check if user already voted today
        cursor = await conn.execute(
            "SELECT id FROM user_votes WHERE user_id = ? AND DATE(voted_at) = DATE('now', 'localtime')",
            (user.id,)
        )
        existing_vote = await cursor.fetchone()

        if existing_vote:
            raise HTTPException(409, "You have already placed an order today")

        # Check max users limit for today
        cursor = await conn.execute(
            "SELECT COUNT(*) as count FROM user_votes WHERE DATE(voted_at) = DATE('now', 'localtime')"
        )
        count_result = await cursor.fetchone()
        if count_result["count"] > 20:
            raise HTTPException(400, "Too many orders today")

        # Insert vote
        await conn.execute(
            "INSERT INTO user_votes (user_id, tea, coffee) VALUES (?, ?, ?)",
            (user.id, vote.tea, vote.coffee),
        )
        await conn.commit()

        # Get total votes
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(tea), 0) as tea, COALESCE(SUM(coffee), 0) as coffee FROM user_votes WHERE DATE(voted_at) = DATE('now', 'localtime')"
        )
        result = await cursor.fetchone()
        total_votes = {"tea": result["tea"], "coffee": result["coffee"]}

    await broadcast_votes()
    return total_votes


@router.get("/orders/breakdown", response_model=OrdersBreakdownResponse)
async def get_orders_breakdown(user: AuthUser = Depends(get_current_user)):
    """Get detailed breakdown of who ordered how much tea or coffee today"""
    async with db.get_connection() as conn:
        # Get individual user orders with names for today only
        cursor = await conn.execute("""
            SELECT u.name, v.tea, v.coffee
            FROM user_votes v
            INNER JOIN allowed_users u ON v.user_id = u.id
            WHERE DATE(v.voted_at) = DATE('now', 'localtime')
            ORDER BY u.name ASC
        """)
        rows = await cursor.fetchall()

        # Build list of user orders
        orders = [
            UserOrderDetail(
                name=row["name"],
                tea=row["tea"],
                coffee=row["coffee"]
            )
            for row in rows
        ]

        # Get totals for today only
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(tea), 0) as tea, COALESCE(SUM(coffee), 0) as coffee FROM user_votes WHERE DATE(voted_at) = DATE('now', 'localtime')"
        )
        totals = await cursor.fetchone()

        return {
            "orders": orders,
            "total_tea": totals["tea"],
            "total_coffee": totals["coffee"]
        }
