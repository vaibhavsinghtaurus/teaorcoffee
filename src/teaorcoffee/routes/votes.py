from fastapi import APIRouter, HTTPException, status, Depends

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db, today_ist
from src.teaorcoffee.models.schema import (
    VotesResponse, VoteMeResponse, VoteRequest, EditVoteRequest, VoteActionResponse, AuthUser,
    OrdersBreakdownResponse, OrderDetail, ProductTotal,
    MyOrdersResponse, MyOrderEntry,
)
from src.teaorcoffee.utils.broadcast import broadcast_votes

router = APIRouter(tags=["Votes"])


def _today() -> str:
    return today_ist()


def _validate_not_past(date_str: str):
    if date_str < _today():
        raise HTTPException(400, "Cannot place or edit an order for a past date")


@router.get("/votes", response_model=VotesResponse)
async def get_votes(user: AuthUser = Depends(get_current_user)):
    totals_raw = await db.get_today_totals(user.company_id)
    order_count = await db.get_today_order_count(user.company_id)
    return VotesResponse(
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )


@router.get("/vote/me", response_model=VoteMeResponse)
async def get_my_vote(user: AuthUser = Depends(get_current_user)):
    vote = await db.get_user_today_vote(user.id)
    if not vote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You have no pending order today")
    return VoteMeResponse(
        product_id=vote.get("distributor_product_id", ""),
        product_name=vote.get("product_name", ""),
        product_emoji=vote.get("product_emoji", ""),
        qty=int(vote.get("qty", 0)),
        date=vote.get("date", _today()),
        status=vote.get("status", "pending"),
    )


@router.post("/vote", response_model=VotesResponse, status_code=201)
async def cast_vote(vote: VoteRequest, user: AuthUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(400, "No company assigned to user")

    date_str = vote.date or _today()
    _validate_not_past(date_str)

    product = await db.get_company_product(user.company_id, vote.product_id)
    if not product or not product["is_enabled"]:
        raise HTTPException(400, "Invalid or unavailable product for this company")

    if vote.qty < 1:
        raise HTTPException(400, "Quantity must be at least 1")
    if vote.qty > product["max_qty"]:
        raise HTTPException(400, f"Maximum {product['max_qty']} allowed for {product['name']}")

    if await db.has_user_pending_vote(user.id, date_str):
        raise HTTPException(409, "You already have a pending order for that date")

    if await db.get_today_order_count(user.company_id) >= 200:
        raise HTTPException(400, "Order limit reached for today")

    await db.insert_vote(
        user.id, user.company_id, vote.product_id, product["name"], product["emoji"],
        vote.qty, price_at_order=product["price"], date_str=date_str,
    )
    if date_str == _today():
        await broadcast_votes(user.company_id)

    totals_raw = await db.get_today_totals(user.company_id)
    order_count = await db.get_today_order_count(user.company_id)
    return VotesResponse(
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )


@router.put("/vote", response_model=VoteActionResponse)
async def edit_vote(edit: EditVoteRequest, user: AuthUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(400, "No company assigned to user")

    date_str = edit.date or _today()
    _validate_not_past(date_str)

    existing = await db.get_user_vote_for_date(user.id, date_str, status="pending")
    if not existing:
        raise HTTPException(404, "No pending order found for that date")

    product = await db.get_company_product(user.company_id, edit.product_id)
    if not product or not product["is_enabled"]:
        raise HTTPException(400, "Invalid or unavailable product for this company")
    if edit.qty < 1 or edit.qty > product["max_qty"]:
        raise HTTPException(400, f"Quantity must be 1–{product['max_qty']}")

    await db.update_vote(user.id, date_str, edit.product_id, product["name"], product["emoji"],
                          edit.qty, price_at_order=product["price"])
    if date_str == _today():
        await broadcast_votes(user.company_id)
    return VoteActionResponse(success=True, message="Order updated")


@router.delete("/vote", response_model=VoteActionResponse)
async def cancel_vote(date: str | None = None, user: AuthUser = Depends(get_current_user)):
    date_str = date or _today()
    _validate_not_past(date_str)
    deleted = await db.delete_user_vote_for_date(user.id, date_str)
    if not deleted:
        raise HTTPException(404, "No pending order found for that date")
    if date_str == _today():
        await broadcast_votes(user.company_id)
    return VoteActionResponse(success=True, message="Order cancelled")


@router.get("/orders/mine", response_model=MyOrdersResponse)
async def get_my_orders(user: AuthUser = Depends(get_current_user)):
    rows = await db.get_user_orders_from_date(user.id, _today())
    return MyOrdersResponse(orders=[MyOrderEntry(
        id=r["id"], date=r["date"], product_id=r.get("distributor_product_id", ""),
        product_name=r["product_name"], product_emoji=r["product_emoji"],
        qty=r["qty"], status=r.get("status", "pending"),
    ) for r in rows])


@router.get("/orders/breakdown", response_model=OrdersBreakdownResponse)
async def get_orders_breakdown(user: AuthUser = Depends(get_current_user)):
    rows = await db.get_today_breakdown(user.company_id)
    orders = [OrderDetail(
        name=r["name"], product_name=r["product_name"], product_emoji=r["product_emoji"],
        qty=r["qty"], status=r.get("status", "delivered"),
    ) for r in rows]
    totals_raw = await db.get_today_totals(user.company_id)
    order_count = await db.get_today_order_count(user.company_id)
    return OrdersBreakdownResponse(
        orders=orders,
        totals={k: ProductTotal(**v) for k, v in totals_raw.items()},
        order_count=order_count,
    )
