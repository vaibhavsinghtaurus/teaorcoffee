from src.teaorcoffee.core.state import chat_connections


async def broadcast_chat(message: dict):
    dead = set()

    for ws in chat_connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)

    chat_connections.difference_update(dead)
