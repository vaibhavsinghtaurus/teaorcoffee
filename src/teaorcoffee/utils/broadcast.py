from src.teaorcoffee.core.state import connections, cs_connections
from src.teaorcoffee.core.database import db


async def _build_payload() -> dict:
    votes = await db.get_today_totals()
    rows = await db.get_today_breakdown()
    return {
        "tea": votes["tea"],
        "coffee": votes["coffee"],
        "orders": [{"name": r["name"], "tea": r["tea"], "coffee": r["coffee"]} for r in rows],
    }


async def broadcast_votes():
    """Broadcast current vote totals + breakdown to all connected websocket clients"""
    payload = await _build_payload()

    dead = set()
    for ws in connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)

    connections.difference_update(dead)


async def broadcast_cs_stats():
    """Broadcast updated CS leaderboard to all CS WebSocket clients"""
    players = await db.get_all_cs_stats()
    payload = {"type": "cs_stats", "players": players}

    dead = set()
    for ws in cs_connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)

    cs_connections.difference_update(dead)
