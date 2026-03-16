from typing import Set, List
from fastapi import WebSocket

# ---- Vote WebSockets ----
connections: Set[WebSocket] = set()

# ---- Chat ----
chat_connections: Set[WebSocket] = set()
chat_history: List[dict] = []
CHAT_HISTORY_LIMIT = 50
