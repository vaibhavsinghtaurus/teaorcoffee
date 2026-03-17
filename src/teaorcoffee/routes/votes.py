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
    return await db.get_today_totals()


@router.get("/vote/me", response_model=VoteMeResponse)
async def get_my_vote(user: AuthUser = Depends(get_current_user)):
    """Get current authenticated user's vote for today"""
    vote = await db.get_user_today_vote(user.id)

    if not vote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not voted today",
        )

    return {"tea": int(vote["tea"]), "coffee": int(vote["coffee"])}


@router.post("/vote", response_model=VotesResponse, status_code=201)
async def cast_vote(vote: VoteRequest, user: AuthUser = Depends(get_current_user)):
    """Cast a vote for the authenticated user"""
    if vote.tea < 0 or vote.coffee < 0:
        raise HTTPException(400, "Tea and coffee must be >= 0")

    if vote.tea == 0 and vote.coffee == 0:
        raise HTTPException(400, "At least one drink must be ordered")

    if vote.tea > 0 and vote.coffee > 0:
        raise HTTPException(400, "You can only order tea OR coffee, not both")

    if vote.tea > 2:
        raise HTTPException(400, "You can order maximum 2 tea")

    if vote.coffee > 1:
        raise HTTPException(400, "You can order maximum 1 coffee")

    if await db.has_user_voted_today(user.id):
        raise HTTPException(409, "You have already placed an order today")

    if await db.count_today_votes() > 20:
        raise HTTPException(400, "Too many orders today")

    await db.insert_vote(user.id, vote.tea, vote.coffee)
    total_votes = await db.get_today_totals()

    await broadcast_votes()
    return total_votes


@router.get("/orders/breakdown", response_model=OrdersBreakdownResponse)
async def get_orders_breakdown(user: AuthUser = Depends(get_current_user)):
    """Get detailed breakdown of who ordered how much tea or coffee today"""
    rows = await db.get_today_breakdown()
    orders = [UserOrderDetail(name=r["name"], tea=r["tea"], coffee=r["coffee"]) for r in rows]

    totals = await db.get_today_totals()
    return {
        "orders": orders,
        "total_tea": totals["tea"],
        "total_coffee": totals["coffee"],
    }
