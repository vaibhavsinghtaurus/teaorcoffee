from fastapi import APIRouter, HTTPException, status, Depends

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import (
    VotesResponse, VoteMeResponse, VoteRequest, AuthUser,
    OrdersBreakdownResponse, OrderDetail, ProductTotal,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

router = APIRouter(tags=["Votes"])


@router.get("/votes", response_model=VotesResponse)
async def get_votes(user: AuthUser = Depends(get_current_user)):
    totals_raw = await db.get_today_totals(user.office_id)
    order_count = await db.get_today_order_count(user.office_id)
    return VotesResponse(
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )


@router.get("/vote/me", response_model=VoteMeResponse)
async def get_my_vote(user: AuthUser = Depends(get_current_user)):
    vote = await db.get_user_today_vote(user.id)
    if not vote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You have not voted today")
    return VoteMeResponse(
        product_id=vote.get("product_id", ""),
        product_name=vote.get("product_name", ""),
        product_emoji=vote.get("product_emoji", ""),
        qty=int(vote.get("qty", 0)),
    )


@router.post("/vote", response_model=VotesResponse, status_code=201)
async def cast_vote(vote: VoteRequest, user: AuthUser = Depends(get_current_user)):
    if not user.office_id:
        raise HTTPException(400, "No office assigned to user")

    product = await db.get_product_by_id(vote.product_id)
    if not product or not product.get("is_active") or product.get("office_id") != user.office_id:
        raise HTTPException(400, "Invalid or inactive product")

    if vote.qty < 1:
        raise HTTPException(400, "Quantity must be at least 1")
    if vote.qty > product["max_qty"]:
        raise HTTPException(400, f"Maximum {product['max_qty']} allowed for {product['name']}")

    if await db.has_user_voted_today(user.id):
        raise HTTPException(409, "You have already placed an order today")

    if await db.get_today_order_count(user.office_id) >= 50:
        raise HTTPException(400, "Order limit reached for today")

    await db.insert_vote(
        user.id, user.office_id,
        vote.product_id, product["name"], product["emoji"], vote.qty,
    )
    await broadcast_votes(user.office_id)

    totals_raw = await db.get_today_totals(user.office_id)
    order_count = await db.get_today_order_count(user.office_id)
    return VotesResponse(
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )


@router.get("/orders/breakdown", response_model=OrdersBreakdownResponse)
async def get_orders_breakdown(user: AuthUser = Depends(get_current_user)):
    rows = await db.get_today_breakdown(user.office_id)
    orders = [OrderDetail(
        name=r["name"],
        product_name=r["product_name"],
        product_emoji=r["product_emoji"],
        qty=r["qty"],
    ) for r in rows]
    totals_raw = await db.get_today_totals(user.office_id)
    order_count = await db.get_today_order_count(user.office_id)
    return OrdersBreakdownResponse(
        orders=orders,
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )
