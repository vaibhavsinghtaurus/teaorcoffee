import logging

from src.teaorcoffee.core.database import db

logger = logging.getLogger(__name__)


async def initialize_database():
    if db._db is None:
        logger.warning("Database not initialized — skipping DB initialization.")
        return

    await _create_indexes()

    logger.info("Database initialization complete.")


# ── Indexes ──────────────────────────────────────────────────────────────────
#
# Every replica runs this on boot with no coordination between them, so two
# replicas can race the same drop/create — MongoDB aborts the loser's index
# build (OperationFailure: IndexBuildAborted) rather than queuing it. That's
# a transient startup race, not a real failure (the winning replica leaves the
# index in the correct state), so it must not crash the whole app's lifespan.

async def _safe_index_op(coro):
    try:
        await coro
    except Exception as e:
        logger.warning(f"Index operation skipped (likely a race with another replica): {e}")


async def _create_indexes():
    await _safe_index_op(db.users.create_index("name", unique=True))
    await _safe_index_op(db.users.create_index("session_token", sparse=True))
    try:
        await db.users.drop_index("nickname_1")
    except Exception:
        pass
    await _safe_index_op(db.users.create_index("nickname", unique=True, sparse=True))

    try:
        await db.votes.drop_index("user_id_1_date_1")
    except Exception:
        pass
    await _safe_index_op(db.votes.create_index(
        [("user_id", 1), ("date", 1)], unique=True,
        partialFilterExpression={"status": "pending"},
        name="user_id_1_date_1_pending",
    ))
    await _safe_index_op(db.votes.create_index("date"))
    await _safe_index_op(db.votes.create_index("company_id"))

    await _safe_index_op(db.companies.create_index("slug", unique=True))
    await _safe_index_op(db.distributor_products.create_index([("company_id", 1), ("name", 1)], unique=True))
    await _safe_index_op(db.company_products.create_index([("company_id", 1), ("distributor_product_id", 1)], unique=True))
    await _safe_index_op(db.product_price_history.create_index("distributor_product_id"))
