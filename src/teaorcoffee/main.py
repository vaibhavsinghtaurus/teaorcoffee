from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.core.init_db import initialize_database
from src.teaorcoffee.routes import health, votes, admin, websocket, chat, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    db.initialize(settings.mongodb_uri)
    await initialize_database()
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
