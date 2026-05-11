from typing import Set, List
from fastapi import WebSocket

# ---- Vote WebSockets ----
connections: Set[WebSocket] = set()

# ---- Chat ----
chat_connections: Set[WebSocket] = set()
chat_history: List[dict] = []
CHAT_HISTORY_LIMIT = 50

# ---- CS Game ----
cs_connections: Set[WebSocket] = set()

# ---- CS WebRTC Signaling ----
# room_name -> list of (username, websocket)
signal_rooms: dict[str, list[tuple[str, WebSocket]]] = {}

# ---- CS Download Progress ----
# username -> {"pct": int, "mb": int, "done": bool}
download_progress: dict[str, dict] = {}
