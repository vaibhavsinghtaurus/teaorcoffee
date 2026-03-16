from src.teaorcoffee.core.state import connections
from src.teaorcoffee.core.database import db


async def broadcast_votes():
    """Broadcast current vote totals to all connected websocket clients"""
    # Get current vote totals from database
    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(tea), 0) as tea, COALESCE(SUM(coffee), 0) as coffee FROM user_votes WHERE DATE(voted_at) = DATE('now', 'localtime')"
        )
        result = await cursor.fetchone()
        votes = {"tea": result["tea"], "coffee": result["coffee"]}

    dead = set()

    for ws in connections:
        try:
            await ws.send_json(votes)
        except Exception:
            dead.add(ws)

    connections.difference_update(dead)
