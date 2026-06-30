import logging
from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_ALLOWED_NAMES = [
    "Vaibhav", "Sourabh", "Nitin", "Hemang", "Om",
    "Bhavya Shah", "Bhavya Prajapati", "Meet", "Gopal",
    "Sashikant", "Ranjeet", "Gaurav", "Jimish", "Devesh",
    "Pratik", "Abhi", "Abhishek",
]

_DEFAULT_PRODUCTS = [
    {"name": "Tea",    "emoji": "🍵", "max_qty": 2},
    {"name": "Coffee", "emoji": "☕", "max_qty": 1},
]

_DEFAULT_HR_NAMES = {"Ranjeet", "Jimish"}


async def initialize_database():
    if not settings.mongodb_uri:
        logger.warning("TOC_MONGODB_URI not set — skipping DB initialization.")
        return

    # ── Indexes ──────────────────────────────────────────────────────────────
    await db.users.create_index("name", unique=True)
    await db.users.create_index("session_token", sparse=True)
    try:
        await db.users.drop_index("nickname_1")
    except Exception:
        pass
    await db.users.create_index("nickname", unique=True, sparse=True)
    await db.votes.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.votes.create_index("date")
    await db.votes.create_index("office_id")
    await db.allowed_names.create_index("name", unique=True)
    await db.offices.create_index("slug", unique=True)
    await db.products.create_index([("office_id", 1), ("name", 1)], unique=True)

    # ── Default office ────────────────────────────────────────────────────────
    implevision_id = await db.create_office("Implevision", "implevision")
    logger.info("Default office 'implevision' ready: %s", implevision_id)

    # ── Products ──────────────────────────────────────────────────────────────
    await db.seed_products(implevision_id, _DEFAULT_PRODUCTS)
    products = await db.get_products(implevision_id)
    tea_p = next((p for p in products if p["name"] == "Tea"), None)
    coffee_p = next((p for p in products if p["name"] == "Coffee"), None)

    # ── Allowed names ─────────────────────────────────────────────────────────
    await db.seed_allowed_names(_DEFAULT_ALLOWED_NAMES, implevision_id)

    # ── Users ─────────────────────────────────────────────────────────────────
    names = await db.get_allowed_names(implevision_id)
    await db.seed_users(names, implevision_id, role="user")

    # Backfill missing fields on pre-existing users
    await db.users.update_many({"is_disabled": {"$exists": False}}, {"$set": {"is_disabled": 0}})
    await db.users.update_many({"office_id": {"$exists": False}}, {"$set": {"office_id": implevision_id}})
    await db.users.update_many({"role": {"$exists": False}}, {"$set": {"role": "user"}})

    # ── Set roles ─────────────────────────────────────────────────────────────
    admin_user = await db.get_user_by_name(settings.main_admin_name)
    if admin_user:
        await db.set_user_role(int(admin_user["id"]), "main_admin")

    for hr_name in _DEFAULT_HR_NAMES:
        hr_user = await db.get_user_by_name(hr_name)
        if hr_user and hr_user.get("role") == "user":
            await db.set_user_role(int(hr_user["id"]), "office_hr")

    # ── Migrate old votes ─────────────────────────────────────────────────────
    if tea_p and coffee_p:
        await _migrate_old_votes(implevision_id, tea_p, coffee_p)

    await db.allowed_names.update_many(
        {"office_id": {"$exists": False}},
        {"$set": {"office_id": implevision_id}},
    )

    logger.info("Database initialization complete.")


async def _migrate_old_votes(implevision_id: str, tea_p: dict, coffee_p: dict):
    """Convert old {tea, coffee} votes to new flat schema."""
    migrated = 0
    async for vote in db.votes.find({"product_id": {"$exists": False}}):
        tea = int(vote.get("tea", 0))
        coffee = int(vote.get("coffee", 0))
        if tea:
            p = tea_p
            qty = tea
        elif coffee:
            p = coffee_p
            qty = coffee
        else:
            continue
        await db.votes.update_one({"_id": vote["_id"]}, {"$set": {
            "office_id": implevision_id,
            "product_id": p["id"],
            "product_name": p["name"],
            "product_emoji": p["emoji"],
            "qty": qty,
        }})
        migrated += 1
    if migrated:
        logger.info("Migrated %d old votes to new schema.", migrated)
