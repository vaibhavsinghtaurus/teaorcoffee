"""
Background WebSocket client for chat.
Module-level state persists across Streamlit reruns within the same process.
"""
import asyncio
import json
import queue
import threading
from typing import Optional

try:
    import websockets  # type: ignore
    _HAS_WS = True
except ImportError:
    _HAS_WS = False

_sessions: dict[str, "ChatSession"] = {}
_lock = threading.Lock()


class ChatSession:
    def __init__(self, token: str, ws_url: str) -> None:
        self.token = token
        self.ws_url = ws_url
        self.messages: list[dict] = []
        self.connected = False
        self.error: Optional[str] = None
        self._outbox: queue.Queue = queue.Queue()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"chat-ws-{token[:8]}"
        )
        self._thread.start()

    def _run(self) -> None:
        asyncio.run(self._main())

    async def _main(self) -> None:
        if not _HAS_WS:
            self.error = "websockets package not installed"
            return
        try:
            async with websockets.connect(self.ws_url, ping_interval=20) as ws:
                self.connected = True

                async def _recv() -> None:
                    async for raw in ws:
                        try:
                            self.messages.append(json.loads(raw))
                        except Exception:
                            pass

                async def _send() -> None:
                    while True:
                        try:
                            text = self._outbox.get_nowait()
                            await ws.send(json.dumps({"message": text}))
                        except queue.Empty:
                            await asyncio.sleep(0.05)

                await asyncio.gather(_recv(), _send())
        except Exception as exc:
            self.connected = False
            self.error = str(exc)

    def send(self, message: str) -> None:
        self._outbox.put(message)

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()


def get_session(token: str, ws_url: str) -> ChatSession:
    with _lock:
        session = _sessions.get(token)
        if session is None or not session.alive:
            _sessions[token] = ChatSession(token, ws_url)
        return _sessions[token]
