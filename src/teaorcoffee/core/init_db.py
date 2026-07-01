import logging
from datetime import datetime, timezone

from src.teaorcoffee.core.database import db

logger = logging.getLogger(__name__)

_DEFAULT_EMPLOYEE_NAMES = [
    "Sourabh", "Nitin", "Hemang", "Om",
    "Bhavya Shah", "Bhavya Prajapati", "Meet", "Gopal",
    "Sashikant", "Gaurav", "Devesh",
    "Pratik", "Abhi", "Abhishek",
]

_ROLE_RENAME = {
    "main_admin": "super_admin",
    "office_admin": "company_admin",
    "office_hr": "hr",
    "user": "employee",
    "distributor_staff": "distributor_boy",
    "company_admin": "company_admin",
}


async def initialize_database():
    if db._db is None:
        logger.warning("Database not initialized — skipping DB initialization.")
        return

    await _migrate_companies_and_links()
    await _ensure_default_distributor()   # Zaff exists + every buyer company has a resolved distributor_id
    await _migrate_legacy_products()      # legacy products claim their names/ids first
    await _seed_defaults()                # default Tea/Coffee + Implevision + identities — no-ops where already migrated
    await _create_indexes()

    logger.info("Database initialization complete.")


# ── Migration from the old offices/distributor_companies/products schema ──────

async def _migrate_companies_and_links():
    # 1. offices -> companies (mode=company), preserving _id
    async for office in db.legacy_offices.find({}):
        await db.create_company(
            name=office["name"], slug=office["slug"], mode="company",
            is_active=office.get("is_active", True), force_id=office["_id"],
        )

    # 2. distributor_companies -> companies (mode=distributor), preserving _id
    async for dist in db.legacy_distributor_companies.find({}):
        slug = dist["name"].strip().lower().replace(" ", "-")
        await db.create_company(
            name=dist["name"], slug=slug, mode="distributor",
            is_active=dist.get("is_active", True), force_id=dist["_id"],
        )

    # 3. link buyer company -> distributor, from the legacy office_id on distributor_companies
    async for dist in db.legacy_distributor_companies.find({"office_id": {"$exists": True, "$ne": None}}):
        company = await db.get_company_by_id(dist["office_id"])
        if company and not company.get("distributor_id"):
            await db.set_company_distributor(dist["office_id"], str(dist["_id"]))

    # 4. users: office_id -> company_id, role rename
    await db.users.update_many(
        {"office_id": {"$exists": True}, "company_id": {"$exists": False}},
        {"$rename": {"office_id": "company_id"}},
    )
    for old_role, new_role in _ROLE_RENAME.items():
        if old_role != new_role:
            await db.users.update_many({"role": old_role}, {"$set": {"role": new_role}})

    # 5. votes: office_id -> company_id, product_id -> distributor_product_id
    await db.votes.update_many(
        {"office_id": {"$exists": True}, "company_id": {"$exists": False}},
        {"$rename": {"office_id": "company_id"}},
    )
    await db.votes.update_many(
        {"product_id": {"$exists": True}, "distributor_product_id": {"$exists": False}},
        {"$rename": {"product_id": "distributor_product_id"}},
    )
    await db.votes.update_many(
        {"price_at_order": {"$exists": False}}, {"$set": {"price_at_order": 10}},
    )
    # Pre-existing orders predate the delivery workflow — treat as already fulfilled
    await db.votes.update_many(
        {"status": {"$exists": False}},
        {"$set": {"status": "delivered", "delivered_at": None, "delivered_by_user_id": None}},
    )


_ZAFF_ADDRESS = "711 K11, Subhanpura, Vadodara"
_IMPLEVISION_ADDRESS = "611 K10 Grand, Subhanpura, Vadodara"


# ── Ensure a default distributor exists and every buyer company has one ───────

async def _ensure_default_distributor():
    # Look up by NAME first — a migrated legacy distributor may have an existing
    # slug that isn't exactly "zaff" (whatever it was created with historically),
    # so matching by slug alone can miss it and spawn a duplicate empty company.
    zaff = await db.get_company_by_name("Zaff", mode="distributor")
    zaff_id = zaff["id"] if zaff else await db.create_company("Zaff", "zaff", mode="distributor",
                                                                is_active=True, address=_ZAFF_ADDRESS)
    zaff = await db.get_company_by_id(zaff_id)
    if not zaff.get("address"):
        await db.update_company_address(zaff_id, _ZAFF_ADDRESS)
    for company in await db.get_all_companies():
        if company.get("mode") == "company" and not company.get("distributor_id"):
            await db.set_company_distributor(company["id"], zaff_id)


# ── Default seed data (idempotent — only creates what's missing) ──────────────

async def _seed_defaults():
    zaff = await db.get_company_by_name("Zaff", mode="distributor")
    zaff_id = zaff["id"]
    await db.seed_distributor_products(zaff_id, [
        {"name": "Tea", "emoji": "🍵", "price": 10, "max_qty": 2},
        {"name": "Coffee", "emoji": "☕", "price": 10, "max_qty": 1},
    ])

    # Same name-first lookup as above — the migrated legacy office's slug may differ
    # from "implevision", so this must not blindly create a second, empty company.
    implevision = await db.get_company_by_name("Implevision", mode="company")
    implevision_id = implevision["id"] if implevision else await db.create_company(
        "Implevision", "implevision", mode="company", distributor_id=zaff_id,
        is_active=True, address=_IMPLEVISION_ADDRESS,
    )
    implevision = await db.get_company_by_id(implevision_id)
    if not implevision.get("distributor_id"):
        await db.set_company_distributor(implevision_id, zaff_id)
    if not implevision.get("address"):
        await db.update_company_address(implevision_id, _IMPLEVISION_ADDRESS)

    zaff_products = await db.get_distributor_products(zaff_id)
    for p in zaff_products:
        await db.enable_company_product(implevision_id, p["id"])

    # Vaibhav is THE designated super_admin — always ensure that, regardless of
    # whatever role he was migrated in with (e.g. a legacy office_admin/office_hr
    # mapping, or a plain employee). This is a global role, not company-scoped.
    vaibhav_created = await db.add_company_member("Vaibhav", implevision_id, "super_admin")
    if not vaibhav_created:
        vaibhav = await db.get_user_by_name("Vaibhav")
        if vaibhav and vaibhav.get("role") != "super_admin":
            await db.set_user_role(int(vaibhav["id"]), "super_admin")

    for name, role in (("Jimish", "manager"), ("Ranjeet", "hr")):
        created = await db.add_company_member(name, implevision_id, role)
        if not created:
            # Already existed (e.g. migrated from the old schema as a plain employee) —
            # promote to their intended role, but only if nobody has since customized it.
            user = await db.get_user_by_name(name)
            if user and user.get("company_id") == implevision_id and user.get("role") == "employee":
                await db.set_user_role(int(user["id"]), role)
    await db.add_company_members(_DEFAULT_EMPLOYEE_NAMES, implevision_id, "employee")

    # Backfill missing fields on any pre-existing users
    await db.users.update_many({"is_disabled": {"$exists": False}}, {"$set": {"is_disabled": 0}})
    await db.users.update_many({"company_id": {"$exists": False}}, {"$set": {"company_id": implevision_id}})
    await db.users.update_many({"role": {"$exists": False}}, {"$set": {"role": "employee"}})

    logger.info("Default seed ready — Implevision (buyer) -> Zaff (distributor).")


async def _migrate_legacy_products():
    """Old per-office `products` -> `distributor_products`, owned by that office's
    (by now always-resolved) distributor. Preserves _id so votes.distributor_product_id
    keeps resolving without any rewrite."""
    async for product in db.legacy_products.find({}):
        office_id = product.get("office_id")
        if not office_id:
            continue
        company = await db.get_company_by_id(office_id)
        distributor_id = company.get("distributor_id") if company else None
        if not distributor_id:
            continue
        existing = await db.distributor_products.find_one({"_id": product["_id"]})
        if not existing:
            price = product.get("current_price", 10)
            await db.distributor_products.insert_one({
                "_id": product["_id"],
                "company_id": distributor_id,
                "name": product["name"],
                "emoji": product["emoji"],
                "current_price": price,
                "max_qty": product.get("max_qty", 1),
                "is_active": product.get("is_active", True),
                "sort_order": product.get("sort_order", 0),
                "created_at": product.get("created_at", datetime.now(timezone.utc).isoformat()),
            })
            await db.product_price_history.insert_one({
                "distributor_product_id": str(product["_id"]),
                "price": price,
                "changed_by_user_id": None,
                "effective_at": datetime.now(timezone.utc).isoformat(),
            })
        await db.enable_company_product(office_id, str(product["_id"]))


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
