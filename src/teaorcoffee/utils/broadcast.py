from src.teaorcoffee.core.state import connections
from src.teaorcoffee.core.database import db


async def broadcast_votes():
    """Broadcast current vote totals to all connected websocket clients"""
    votes = await db.get_today_totals()

    dead = set()

    for ws in connections:
        try:
            await ws.send_json(votes)
        except Exception:
            dead.add(ws)

    connections.difference_update(dead)
