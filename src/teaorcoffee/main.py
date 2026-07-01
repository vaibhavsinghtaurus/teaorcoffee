import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.core.init_db import initialize_database
from src.teaorcoffee.routes import health, votes, admin, hr, websocket, chat, auth, stats
from src.teaorcoffee.routes import company_admin, distributor, products, pages

_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.mongodb_uri:
        raise RuntimeError("TOC_MONGODB_URI environment variable is not set.")
    db.initialize(settings.mongodb_uri)
    await initialize_database()
    yield
    db.close()


app = FastAPI(
    title="Tea & Coffee Orders API",
    description="Multi-office beverage ordering with role-based access",
    version="6.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.1\.\d+)(:\d+)?|https://.*\.(netlify\.app|render\.com|railway\.app|fly\.dev|onrender\.com|fastapi\.cloud|fastapicloud\.dev)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=_STATIC), name="static")

app.include_router(pages.router)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(votes.router)
app.include_router(stats.router)
app.include_router(admin.router)
app.include_router(hr.router)
app.include_router(company_admin.router)
app.include_router(distributor.router)
app.include_router(products.router)
app.include_router(websocket.router)
app.include_router(chat.router)
