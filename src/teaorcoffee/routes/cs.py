import subprocess
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

_ROOT      = Path(__file__).resolve().parents[4]
_VALVE_ZIP = _ROOT / "static" / "assets" / "valve.zip"
_HLDS_DIR  = _ROOT / "hlds"

from src.teaorcoffee.core.auth import get_current_user, get_current_user_from_websocket
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.state import cs_connections, signal_rooms, download_progress
from src.teaorcoffee.models.schema import (
    AuthUser,
    CSEventRequest,
    CSLeaderboardResponse,
    CSStatsResponse,
)
from src.teaorcoffee.utils.broadcast import broadcast_cs_stats

router = APIRouter(prefix="/cs", tags=["CS Game"])


@router.post("/download/progress", status_code=204)
async def report_download_progress(
    body: dict,
    user: AuthUser = Depends(get_current_user),
):
    download_progress[user.name] = {
        "pct":  body.get("pct", 0),
        "mb":   body.get("mb", 0),
        "done": body.get("done", False),
    }


@router.get("/download/progress")
async def get_download_progress(user: AuthUser = Depends(get_current_user)):
    return download_progress.get(user.name, {"pct": 0, "mb": 0, "done": False})


VALID_EVENTS = {
    "kill", "death", "headshot",
    "round_win", "round_loss",
    "session_start", "session_end",
}

EVENT_STAT_MAP = {
    "kill":          "kills",
    "death":         "deaths",
    "headshot":      "headshots",
    "round_win":     "wins",
    "round_loss":    "losses",
    "session_start": "sessions",
}

# ── HLDS process handle ───────────────────────────────────────────────────────
_hlds_process: subprocess.Popen | None = None
HLDS_MAX_PLAYERS = 16
HLDS_MAP = "de_dust2"


def _hlds_running() -> bool:
    return _hlds_process is not None and _hlds_process.poll() is None


def _hlds_cmd() -> list[str]:
    base = [
        "-game", "cstrike",
        "+maxplayers", str(HLDS_MAX_PLAYERS),
        "+map", HLDS_MAP,
        "-noipx", "-nojoy", "-nowinmouse",
    ]
    if sys.platform == "win32":
        return ["hlds/hlds.exe"] + base
    return ["./hlds/hlds_run"] + base


# ── Setup status ─────────────────────────────────────────────────────────────

@router.get("/setup/status")
async def setup_status():
    """
    Polled by game.html on load to know whether server-side assets are ready.
    No auth required — called before the engine starts.
    """
    assets_ready = _VALVE_ZIP.exists()
    hlds_ready   = _HLDS_DIR.exists()
    return {
        "assets_ready": assets_ready,
        "hlds_ready":   hlds_ready,
        "ready":        assets_ready and hlds_ready,
    }


# ── Stats endpoints ───────────────────────────────────────────────────────────

@router.post("/event", status_code=204)
async def receive_game_event(
    body: CSEventRequest,
    user: AuthUser = Depends(get_current_user),
):
    """Receive a CS game event from the browser and update player stats"""
    if body.event not in VALID_EVENTS:
        return

    stat_field = EVENT_STAT_MAP.get(body.event)
    if stat_field:
        await db.increment_cs_stat(user.id, stat_field)

    await broadcast_cs_stats()


@router.get("/stats", response_model=CSLeaderboardResponse)
async def get_leaderboard(user: AuthUser = Depends(get_current_user)):
    """Full CS stats leaderboard"""
    players = await db.get_all_cs_stats()
    return CSLeaderboardResponse(players=[CSStatsResponse(**p) for p in players])


@router.get("/stats/me", response_model=CSStatsResponse)
async def get_my_stats(user: AuthUser = Depends(get_current_user)):
    """Authenticated user's own CS stats"""
    stats = await db.get_cs_stats(user.id)
    kills  = stats["kills"]
    deaths = stats["deaths"]
    return CSStatsResponse(
        name=user.name,
        nickname=user.nickname,
        kills=kills,
        deaths=deaths,
        headshots=stats["headshots"],
        wins=stats["wins"],
        losses=stats["losses"],
        sessions=stats["sessions"],
        kd_ratio=round(kills / deaths, 2) if deaths > 0 else float(kills),
    )


# ── HLDS server management ────────────────────────────────────────────────────

@router.get("/server/status")
async def server_status(user: AuthUser = Depends(get_current_user)):
    """Check whether the HLDS game server is running"""
    running = _hlds_running()
    host    = "127.0.0.1"
    port    = "27015"
    return {
        "running":    running,
        "address":    f"{host}:{port}" if running else None,
        "players":    0,
        "max_players": HLDS_MAX_PLAYERS,
        "map":        HLDS_MAP,
    }


@router.post("/server/start")
async def start_server(password: str):
    """Admin: start the HLDS dedicated server"""
    if password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid admin password")

    global _hlds_process
    if _hlds_running():
        return {"status": "already_running"}

    try:
        _hlds_process = subprocess.Popen(
            _hlds_cmd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"status": "started", "pid": _hlds_process.pid}
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="HLDS not found. Run scripts/setup_cs_server.py first.",
        )


@router.post("/server/stop")
async def stop_server(password: str):
    """Admin: stop the HLDS dedicated server"""
    if password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid admin password")

    global _hlds_process
    if not _hlds_running():
        return {"status": "not_running"}

    _hlds_process.terminate()
    _hlds_process = None
    return {"status": "stopped"}


# ── Live leaderboard WebSocket ────────────────────────────────────────────────

@router.websocket("/ws/cs")
async def cs_stats_socket(websocket: WebSocket):
    """Push live CS leaderboard updates to connected clients"""
    await websocket.accept()
    try:
        await get_current_user_from_websocket(websocket)
        cs_connections.add(websocket)

        players = await db.get_all_cs_stats()
        await websocket.send_json({"type": "cs_stats", "players": players})

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        cs_connections.discard(websocket)
    except Exception:
        cs_connections.discard(websocket)
        await websocket.close(code=1008)


# ── WebRTC signaling relay ────────────────────────────────────────────────────
# Relays SDP offers/answers and ICE candidates between the browser clients
# and the HLDS WebRTC bridge, enabling multiplayer through the game server.

@router.websocket("/ws/signal")
async def signal_socket(websocket: WebSocket, room: str = "main"):
    """WebRTC signaling relay — forwards SDP/ICE messages within a room"""
    await websocket.accept()
    try:
        user = await get_current_user_from_websocket(websocket)

        if room not in signal_rooms:
            signal_rooms[room] = []

        signal_rooms[room].append((user.name, websocket))

        # Tell everyone else in the room that this peer joined
        for name, ws in signal_rooms[room]:
            if ws is not websocket:
                await ws.send_json({"type": "peer_joined", "peer": user.name})

        while True:
            data = await websocket.receive_json()
            data["from"] = user.name
            # Relay to all other peers in the same room
            dead = []
            for name, ws in signal_rooms[room]:
                if ws is websocket:
                    continue
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append((name, ws))

            for entry in dead:
                signal_rooms[room].remove(entry)

    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close(code=1008)
    finally:
        signal_rooms.setdefault(room, [])
        signal_rooms[room] = [
            (n, w) for n, w in signal_rooms[room] if w is not websocket
        ]
        # Notify remaining peers this one left
        for _, ws in signal_rooms[room]:
            try:
                await ws.send_json({"type": "peer_left", "peer": user.name})
            except Exception:
                pass
