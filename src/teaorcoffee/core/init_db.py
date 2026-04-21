import logging
from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings

logger = logging.getLogger(__name__)


async def initialize_database():
    """Create indexes and seed allowed users into MongoDB"""
    if not settings.mongodb_uri:
        logger.warning(
            "TOC_MONGODB_URI is not set — skipping startup initialization. "
            "Add it to your .env to enable MongoDB."
        )
        return

    await db.users.create_index("name", unique=True)
    await db.users.create_index("session_token", sparse=True)
    await db.votes.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.votes.create_index("date")
    await db.allowed_names.create_index("name", unique=True)

    # Migrate hardcoded list into allowed_names collection on first run
    await db.seed_allowed_names(settings.allowed_names)

    # Seed users from allowed_names (source of truth going forward)
    names = await db.get_allowed_names()
    await db.seed_users(names)
