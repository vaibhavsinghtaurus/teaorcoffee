from fastapi import APIRouter, Depends, HTTPException

from src.teaorcoffee.core.auth import get_current_user
from src.teaorcoffee.core.database import db
from src.teaorcoffee.models.schema import AuthUser, UserStatsDayEntry, UserStatsResponse

router = APIRouter(tags=["Stats"])

_MIN_DATE = "2026-01-01"


@router.get("/stats/me", response_model=UserStatsResponse)
async def get_my_stats(
    start: str,
    end: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Authenticated user's own tea/coffee totals for a date range"""
    if start < _MIN_DATE:
        start = _MIN_DATE
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")

    rows = await db.get_user_stats_range(current_user.name, start, end)
    days = [UserStatsDayEntry(**r) for r in rows]
    return UserStatsResponse(
        name=current_user.name,
        start=start,
        end=end,
        days=days,
        total_tea=sum(d.tea for d in days),
        total_coffee=sum(d.coffee for d in days),
        order_days=len(days),
    )
