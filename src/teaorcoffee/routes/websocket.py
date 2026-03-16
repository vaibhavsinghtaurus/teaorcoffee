from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.teaorcoffee.core.state import connections
from src.teaorcoffee.core.auth import get_current_user_from_websocket
from src.teaorcoffee.core.database import db

router = APIRouter()


@router.websocket("/ws/votes")
async def votes_socket(websocket: WebSocket):
    """WebSocket endpoint for real-time vote updates (requires authentication)"""
    await websocket.accept()

    try:
        # Authenticate the websocket connection
        user = await get_current_user_from_websocket(websocket)

        # Add to connections
        connections.add(websocket)

        # Send current vote totals
        async with db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(tea), 0) as tea, COALESCE(SUM(coffee), 0) as coffee FROM user_votes"
            )
            result = await cursor.fetchone()
            votes = {"tea": result["tea"], "coffee": result["coffee"]}

        await websocket.send_json(votes)

        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)
    except Exception:
        # Authentication failed or other error
        connections.discard(websocket)
        await websocket.close(code=1008)  # Policy violation
