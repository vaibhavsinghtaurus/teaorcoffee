from typing import Set, List
from fastapi import WebSocket

# vote ws: maps websocket -> office_id for per-office broadcast
connections: dict[WebSocket, str] = {}

# chat ws
chat_connections: Set[WebSocket] = set()
chat_history: List[dict] = []
CHAT_HISTORY_LIMIT = 50
