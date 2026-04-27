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

    # Drop and recreate nickname index to ensure it is sparse
    # (an earlier version may have created it without sparse=True)
    try:
        await db.users.drop_index("nickname_1")
    except Exception:
        pass
    await db.users.create_index("nickname", unique=True, sparse=True)

    await db.votes.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.votes.create_index("date")
    await db.allowed_names.create_index("name", unique=True)

    # Migrate hardcoded list into allowed_names collection on first run
    await db.seed_allowed_names(settings.allowed_names)

    # Seed users from allowed_names (source of truth going forward)
    names = await db.get_allowed_names()
    await db.seed_users(names)

    # Backfill is_disabled for users that predate that field
    await db.users.update_many({"is_disabled": {"$exists": False}}, {"$set": {"is_disabled": 0}})
