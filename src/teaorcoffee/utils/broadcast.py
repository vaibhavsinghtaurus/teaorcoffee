from src.teaorcoffee.core.state import connections
from src.teaorcoffee.core.database import db


async def _build_payload(office_id: str | None) -> dict:
    totals = await db.get_today_totals(office_id)
    rows = await db.get_today_breakdown(office_id)
    order_count = await db.get_today_order_count(office_id)
    return {
        "totals": {k: {"total": v["total"], "emoji": v["emoji"]} for k, v in totals.items()},
        "orders": [{"name": r["name"], "product_name": r["product_name"],
                    "product_emoji": r["product_emoji"], "qty": r["qty"]} for r in rows],
        "order_count": order_count,
    }


async def broadcast_votes(office_id: str | None = None):
    payload = await _build_payload(office_id)
    dead = []
    for ws, oid in list(connections.items()):
        if office_id is None or oid == office_id:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
    for ws in dead:
        connections.pop(ws, None)
