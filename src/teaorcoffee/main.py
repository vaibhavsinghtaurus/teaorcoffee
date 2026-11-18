import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings
from src.teaorcoffee.core.init_db import initialize_database
from src.teaorcoffee.routes import health, votes, admin, hr, websocket, chat, auth, stats
from src.teaorcoffee.routes import company_admin, distributor, products, pages

_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

logger = logging.getLogger("uvicorn.error")


# ── Keep session tokens out of the logs ──────────────────────────────────────
#
# WebSocket clients authenticate with ?token=<session token>, and uvicorn logs
# the full path + query string of every request/connection, so live session
# tokens end up in plain text in the hosting platform's logs. Redact them.

_TOKEN_RE = re.compile(r"(\btoken=)[^&\s\"]+")


def _redact(value):
    return _TOKEN_RE.sub(r"\1[redacted]", value) if isinstance(value, str) else value


class _RedactTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(_redact(a) for a in record.args)
        record.msg = _redact(record.msg)
        return True


for _name in ("uvicorn.access", "uvicorn.error"):
    logging.getLogger(_name).addFilter(_RedactTokenFilter())


# ── Database initialization with retry ───────────────────────────────────────
#
# Startup must not die on a transient DB/DNS failure. On 2026-11-18 the hosting
# platform's internal DNS resolver timed out on the mongodb+srv SRV lookup;
# because initialize_database() was awaited directly in lifespan, the exception
# aborted startup and the app crash-looped until DNS recovered. Instead, run it
# in the background and keep retrying with backoff while the server stays up.

_DB_INIT_RETRY_DELAYS = (2, 5, 10, 20, 30)  # seconds; the last one repeats


async def _initialize_database_with_retry():
    attempt = 0
    while True:
        attempt += 1
        try:
            await initialize_database()
            if attempt > 1:
                logger.warning("Database initialization succeeded on attempt %d.", attempt)
            return
        except asyncio.CancelledError:
            raise
        except Exception as e:
            delay = _DB_INIT_RETRY_DELAYS[min(attempt, len(_DB_INIT_RETRY_DELAYS)) - 1]
            logger.error("Database initialization failed (attempt %d): %s — retrying in %ds.",
                         attempt, e, delay)
            await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.mongodb_uri:
        raise RuntimeError("TOC_MONGODB_URI environment variable is not set.")
    db.initialize(settings.mongodb_uri)
    init_task = asyncio.create_task(_initialize_database_with_retry())
    try:
        yield
    finally:
        init_task.cancel()
        with suppress(asyncio.CancelledError):
            await init_task
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
