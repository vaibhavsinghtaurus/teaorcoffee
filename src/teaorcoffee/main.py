import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.core.init_db import initialize_database
from src.teaorcoffee.routes import health, votes, admin, websocket, chat, auth
from src.teaorcoffee.routes import cs

_ROOT      = Path(__file__).resolve().parents[3]
_VALVE_ZIP = _ROOT / "static" / "assets" / "valve.zip"
_HLDS_DIR  = _ROOT / "hlds"


def _run_setup_if_needed():
    """Run setup_cs_server.py in a background thread if assets are missing."""
    if _VALVE_ZIP.exists() and _HLDS_DIR.exists():
        return

    import importlib.util, sys
    setup_path = _ROOT / "scripts" / "setup_cs_server.py"
    spec   = importlib.util.spec_from_file_location("setup_cs_server", setup_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    db.initialize(settings.mongodb_uri)
    await initialize_database()
    # Download CS assets + HLDS in background if not already present
    threading.Thread(target=_run_setup_if_needed, daemon=True).start()
    yield
    db.close()

app = FastAPI(
    title="Tea & Coffee Orders API",
    description="Vote once per authenticated user + live chat",
    version="5.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.1\.\d+)(:\d+)?|https://.*\.(netlify\.app|streamlit\.app|streamlitapp\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(votes.router)
app.include_router(admin.router)
app.include_router(websocket.router)
app.include_router(chat.router)
app.include_router(cs.router)

_static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
app.mount("/game", StaticFiles(directory=_static_dir, html=True), name="static")
