from src.teaorcoffee.core.state import connections
from src.teaorcoffee.core.database import db


async def _build_payload(company_id: str | None) -> dict:
    totals = await db.get_today_totals(company_id)
    rows = await db.get_today_breakdown(company_id)
    order_count = await db.get_today_order_count(company_id)
    return {
        "totals": {k: {"total": v["total"], "emoji": v["emoji"]} for k, v in totals.items()},
        "orders": [{"name": r["name"], "product_name": r["product_name"],
                    "product_emoji": r["product_emoji"], "qty": r["qty"],
                    "status": r.get("status", "delivered")} for r in rows],
        "order_count": order_count,
    }


async def broadcast_votes(company_id: str | None = None):
    payload = await _build_payload(company_id)
    dead = []
    for ws, cid in list(connections.items()):
        if company_id is None or cid == company_id:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
    for ws in dead:
        connections.pop(ws, None)
