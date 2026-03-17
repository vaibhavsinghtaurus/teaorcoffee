from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings


async def initialize_database():
    """Seed allowed users into the spreadsheet (creates sheets if missing)"""
    await db.seed_users(settings.allowed_names)
