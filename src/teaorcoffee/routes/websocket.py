from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.teaorcoffee.core.state import connections
from src.teaorcoffee.core.auth import get_current_user_from_websocket
from src.teaorcoffee.utils.broadcast import _build_payload

router = APIRouter()


@router.websocket("/ws/votes")
async def votes_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        user = await get_current_user_from_websocket(websocket)
        connections[websocket] = user.office_id or ""
        await websocket.send_json(await _build_payload(user.office_id))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.pop(websocket, None)
    except Exception:
        connections.pop(websocket, None)
        try:
            await websocket.close(code=1008)
        except Exception:
            pass
