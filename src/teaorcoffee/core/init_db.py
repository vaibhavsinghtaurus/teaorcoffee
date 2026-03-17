import logging
from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings

logger = logging.getLogger(__name__)


async def initialize_database():
    """Seed allowed users into the spreadsheet (creates sheets if missing)"""
    if not settings.apps_script_url:
        logger.warning(
            "TOC_APPS_SCRIPT_URL is not set — skipping startup seeding. "
            "Add it to your .env to enable Google Sheets."
        )
        return
    await db.seed_users(settings.allowed_names)
