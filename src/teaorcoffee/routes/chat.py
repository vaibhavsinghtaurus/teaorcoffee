from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.teaorcoffee.core.state import (
    chat_connections,
    chat_history,
    CHAT_HISTORY_LIMIT,
)
from src.teaorcoffee.utils.chat import broadcast_chat
from src.teaorcoffee.core.auth import get_current_user_from_websocket

router = APIRouter()


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket):
    """WebSocket endpoint for real-time chat (requires authentication)"""
    await websocket.accept()

    try:
        # Authenticate the websocket connection
        user = await get_current_user_from_websocket(websocket)

        # Add to connections
        chat_connections.add(websocket)

        # Use authenticated user's real name
        name = user.name

        # Send chat history
        for msg in chat_history:
            await websocket.send_json(msg)

        # Announce user joined
        await broadcast_chat({"name": "System", "message": f"{name} joined the chat"})

        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            text = data.get("message", "").strip()

            if not text:
                continue

            msg = {"name": name, "message": text}
            chat_history.append(msg)

            if len(chat_history) > CHAT_HISTORY_LIMIT:
                chat_history.pop(0)

            await broadcast_chat(msg)

    except WebSocketDisconnect:
        chat_connections.discard(websocket)
        await broadcast_chat({"name": "System", "message": f"{name} left the chat"})
    except Exception:
        # Authentication failed or other error
        chat_connections.discard(websocket)
        await websocket.close(code=1008)  # Policy violation
