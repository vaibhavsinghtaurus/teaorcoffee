from datetime import date, datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        return ObjectId()


def _branch_label(company: dict) -> str:
    """Disambiguate branches that share the same company name."""
    address = company.get("address")
    return f'{company["name"]} — {address}' if address else company["name"]


class MongoDatabase:
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, uri: str):
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client["teaorcoffee"]

    def close(self):
        if self._client:
            self._client.close()

    @property
    def users(self):
        return self._db["users"]

    @property
    def votes(self):
        return self._db["votes"]

    @property
    def companies(self):
        return self._db["companies"]

    @property
    def distributor_products(self):
        return self._db["distributor_products"]

    @property
    def product_price_history(self):
        return self._db["product_price_history"]

    @property
    def company_products(self):
        return self._db["company_products"]

    # ── Legacy collections (read-only, migration source only) ───────────────────

    @property
    def legacy_offices(self):
        return self._db["offices"]

    @property
    def legacy_distributor_companies(self):
        return self._db["distributor_companies"]

    @property
    def legacy_products(self):
        return self._db["products"]

    def _today(self) -> str:
        return date.today().isoformat()

    # ── Setup / Super Admin ──────────────────────────────────────────────────────

    async def has_super_admin(self) -> bool:
        return await self.users.count_documents({"role": "super_admin"}) > 0

    async def get_super_admin(self) -> Optional[dict]:
        user = await self.users.find_one({"role": "super_admin"})
        if user:
            user["id"] = user["_id"]
        return user

    # ── Companies ─────────────────────────────────────────────────────────────────

    async def create_company(self, name: str, slug: str, mode: str,
                              distributor_id: Optional[str] = None, is_active: bool = True,
                              force_id: Optional[ObjectId] = None, address: str = "") -> str:
        """Idempotent by slug — used for seeding/migration where re-running must not
        create duplicates. Returns the existing company's id if the slug is taken."""
        existing = await self.companies.find_one({"slug": slug})
        if existing:
            return str(existing["_id"])
        doc = {
            "name": name,
            "slug": slug,
            "mode": mode,
            "address": address,
            "distributor_id": distributor_id,
            "is_active": is_active,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if force_id is not None:
            doc["_id"] = force_id
        result = await self.companies.insert_one(doc)
        return str(result.inserted_id)

    async def create_company_branch(self, name: str, slug: str, mode: str, address: str,
                                     distributor_id: Optional[str] = None, is_active: bool = True) -> str:
        """Always creates a NEW company row — multiple branches can share the same
        `name` (e.g. two "Implevision" branches), differentiated by `address`.
        Auto-uniquifies `slug` on collision rather than reusing an existing row."""
        base_slug = slug
        n = 2
        while await self.companies.find_one({"slug": slug}):
            slug = f"{base_slug}-{n}"
            n += 1
        result = await self.companies.insert_one({
            "name": name,
            "slug": slug,
            "mode": mode,
            "address": address,
            "distributor_id": distributor_id,
            "is_active": is_active,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return str(result.inserted_id)

    async def update_company_address(self, company_id: str, address: str) -> bool:
        r = await self.companies.update_one({"_id": _oid(company_id)}, {"$set": {"address": address}})
        return r.matched_count > 0

    async def get_company_by_id(self, company_id: str) -> Optional[dict]:
        try:
            doc = await self.companies.find_one({"_id": _oid(company_id)})
        except Exception:
            return None
        if doc:
            doc["id"] = str(doc["_id"])
            if doc.get("distributor_id"):
                doc["distributor_id"] = str(doc["distributor_id"])
        return doc

    async def get_company_by_slug(self, slug: str) -> Optional[dict]:
        doc = await self.companies.find_one({"slug": slug})
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def get_all_companies(self) -> list[dict]:
        result = []
        async for doc in self.companies.find({}, sort=[("name", 1)]):
            doc["id"] = str(doc["_id"])
            if doc.get("distributor_id"):
                doc["distributor_id"] = str(doc["distributor_id"])
            result.append(doc)
        return result

    async def get_active_companies(self, mode: Optional[str] = None) -> list[dict]:
        query: dict = {"is_active": True}
        if mode:
            query["mode"] = mode
        result = []
        async for doc in self.companies.find(query, sort=[("name", 1)]):
            doc["id"] = str(doc["_id"])
            if doc.get("distributor_id"):
                doc["distributor_id"] = str(doc["distributor_id"])
            result.append(doc)
        return result

    async def update_company(self, company_id: str, name: str) -> bool:
        r = await self.companies.update_one({"_id": _oid(company_id)}, {"$set": {"name": name}})
        return r.matched_count > 0

    async def set_company_active(self, company_id: str, is_active: bool) -> bool:
        r = await self.companies.update_one({"_id": _oid(company_id)}, {"$set": {"is_active": is_active}})
        return r.matched_count > 0

    async def set_company_distributor(self, company_id: str, distributor_id: str) -> bool:
        r = await self.companies.update_one(
            {"_id": _oid(company_id)}, {"$set": {"distributor_id": distributor_id}},
        )
        return r.matched_count > 0

    async def set_company_mode(self, company_id: str, mode: str) -> bool:
        r = await self.companies.update_one({"_id": _oid(company_id)}, {"$set": {"mode": mode}})
        return r.matched_count > 0

    # ── Distributor Products & Pricing ───────────────────────────────────────────

    async def get_distributor_products(self, company_id: str, include_inactive: bool = False) -> list[dict]:
        query: dict = {"company_id": company_id}
        if not include_inactive:
            query["is_active"] = True
        result = []
        async for doc in self.distributor_products.find(query, sort=[("sort_order", 1), ("name", 1)]):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def get_distributor_product_by_id(self, product_id: str) -> Optional[dict]:
        try:
            doc = await self.distributor_products.find_one({"_id": _oid(product_id)})
        except Exception:
            return None
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def add_distributor_product(self, company_id: str, name: str, emoji: str,
                                       price: float, max_qty: int,
                                       changed_by_user_id: Optional[int] = None) -> tuple[str, bool]:
        existing = await self.distributor_products.find_one({"company_id": company_id, "name": name})
        if existing:
            if not existing.get("is_active"):
                await self.distributor_products.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"is_active": True, "emoji": emoji, "max_qty": max_qty}},
                )
                return str(existing["_id"]), True
            return str(existing["_id"]), False
        last = await self.distributor_products.find_one({"company_id": company_id}, sort=[("sort_order", -1)])
        sort_order = (last["sort_order"] + 1) if last else 0
        result = await self.distributor_products.insert_one({
            "company_id": company_id,
            "name": name,
            "emoji": emoji,
            "current_price": price,
            "max_qty": max_qty,
            "is_active": True,
            "sort_order": sort_order,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        product_id = str(result.inserted_id)
        await self.product_price_history.insert_one({
            "distributor_product_id": product_id,
            "price": price,
            "changed_by_user_id": changed_by_user_id,
            "effective_at": datetime.now(timezone.utc).isoformat(),
        })
        return product_id, True

    async def update_distributor_product(self, product_id: str, name: str, emoji: str, max_qty: int) -> bool:
        r = await self.distributor_products.update_one(
            {"_id": _oid(product_id)},
            {"$set": {"name": name, "emoji": emoji, "max_qty": max_qty}},
        )
        return r.matched_count > 0

    async def update_distributor_product_price(self, product_id: str, new_price: float,
                                                 changed_by_user_id: Optional[int] = None) -> bool:
        r = await self.distributor_products.update_one(
            {"_id": _oid(product_id)}, {"$set": {"current_price": new_price}},
        )
        if r.matched_count == 0:
            return False
        await self.product_price_history.insert_one({
            "distributor_product_id": product_id,
            "price": new_price,
            "changed_by_user_id": changed_by_user_id,
            "effective_at": datetime.now(timezone.utc).isoformat(),
        })
        return True

    async def get_price_history(self, product_id: str) -> list[dict]:
        result = []
        async for doc in self.product_price_history.find(
            {"distributor_product_id": product_id}, sort=[("effective_at", -1)],
        ):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def set_distributor_product_active(self, product_id: str, is_active: bool) -> bool:
        r = await self.distributor_products.update_one({"_id": _oid(product_id)}, {"$set": {"is_active": is_active}})
        return r.matched_count > 0

    async def seed_distributor_products(self, company_id: str, products: list[dict],
                                         changed_by_user_id: Optional[int] = None):
        for i, p in enumerate(products):
            existing = await self.distributor_products.find_one({"company_id": company_id, "name": p["name"]})
            if existing:
                continue
            result = await self.distributor_products.insert_one({
                "company_id": company_id,
                "name": p["name"],
                "emoji": p["emoji"],
                "current_price": p["price"],
                "max_qty": p["max_qty"],
                "is_active": True,
                "sort_order": i,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            await self.product_price_history.insert_one({
                "distributor_product_id": str(result.inserted_id),
                "price": p["price"],
                "changed_by_user_id": changed_by_user_id,
                "effective_at": datetime.now(timezone.utc).isoformat(),
            })

    # ── Company Product Enablement ───────────────────────────────────────────────

    async def get_company_products(self, company_id: str, enabled_only: bool = False) -> list[dict]:
        """Distributor catalog joined with this buyer company's enable/max-qty override."""
        company = await self.get_company_by_id(company_id)
        if not company or not company.get("distributor_id"):
            return []
        catalog = await self.get_distributor_products(company["distributor_id"])
        enabled_rows = {
            doc["distributor_product_id"]: doc
            async for doc in self.company_products.find({"company_id": company_id})
        }
        result = []
        for p in catalog:
            row = enabled_rows.get(p["id"])
            is_enabled = bool(row and row.get("is_enabled"))
            if enabled_only and not is_enabled:
                continue
            result.append({
                "distributor_product_id": p["id"],
                "name": p["name"],
                "emoji": p["emoji"],
                "price": p.get("current_price", 0),
                "max_qty": (row or {}).get("max_qty_override") or p["max_qty"],
                "is_enabled": is_enabled,
            })
        return result

    async def get_company_product(self, company_id: str, distributor_product_id: str) -> Optional[dict]:
        rows = await self.get_company_products(company_id)
        return next((r for r in rows if r["distributor_product_id"] == distributor_product_id), None)

    async def enable_company_product(self, company_id: str, distributor_product_id: str,
                                      max_qty_override: Optional[int] = None) -> bool:
        await self.company_products.update_one(
            {"company_id": company_id, "distributor_product_id": distributor_product_id},
            {"$set": {"is_enabled": True, "max_qty_override": max_qty_override},
             "$setOnInsert": {"added_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        return True

    async def disable_company_product(self, company_id: str, distributor_product_id: str) -> bool:
        r = await self.company_products.update_one(
            {"company_id": company_id, "distributor_product_id": distributor_product_id},
            {"$set": {"is_enabled": False}},
        )
        return r.matched_count > 0

    async def set_company_product_max_qty(self, company_id: str, distributor_product_id: str,
                                           max_qty: Optional[int]) -> bool:
        r = await self.company_products.update_one(
            {"company_id": company_id, "distributor_product_id": distributor_product_id},
            {"$set": {"max_qty_override": max_qty}},
        )
        return r.matched_count > 0

    # ── Users ──────────────────────────────────────────────────────────────────

    async def _next_user_id(self) -> int:
        last = await self.users.find_one(sort=[("_id", -1)])
        return (last["_id"] + 1) if last else 1

    async def add_company_member(self, name: str, company_id: str, role: str) -> bool:
        if await self.users.find_one({"name": name}):
            return False
        next_id = await self._next_user_id()
        await self.users.insert_one({
            "_id": next_id,
            "name": name,
            "company_id": company_id,
            "role": role,
            "is_active": 1,
            "is_disabled": 0,
            "session_token": None,
            "last_login_at": None,
        })
        return True

    async def add_company_members(self, names: list[str], company_id: str, role: str) -> int:
        added = 0
        for name in names:
            if await self.add_company_member(name, company_id, role):
                added += 1
        return added

    async def get_user_by_name(self, name: str) -> Optional[dict]:
        user = await self.users.find_one({"name": name})
        if user:
            user["id"] = user["_id"]
        return user

    async def get_user_by_nickname(self, nickname: str) -> Optional[dict]:
        user = await self.users.find_one({"nickname": {"$regex": f"^{nickname}$", "$options": "i"}})
        if user:
            user["id"] = user["_id"]
        return user

    async def get_user_by_token(self, token: str) -> Optional[dict]:
        if not token:
            return None
        user = await self.users.find_one({"session_token": token})
        if not user:
            return None
        expires_at = user.get("token_expires_at")
        if not expires_at:
            return None
        if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
            return None
        user["id"] = user["_id"]
        return user

    async def get_users_for_company(self, company_id: str) -> list[dict]:
        result = []
        async for u in self.users.find({"company_id": company_id}, sort=[("name", 1)]):
            u["id"] = u["_id"]
            result.append(u)
        return result

    async def get_all_users(self) -> list[dict]:
        result = []
        async for u in self.users.find({}, sort=[("name", 1)]):
            u["id"] = u["_id"]
            result.append(u)
        return result

    async def set_user_role(self, user_id: int, role: str) -> bool:
        r = await self.users.update_one({"_id": user_id}, {"$set": {"role": role}})
        return r.matched_count > 0

    async def set_nickname(self, user_id: int, nickname: Optional[str]) -> bool:
        r = await self.users.update_one({"_id": user_id}, {"$set": {"nickname": nickname}})
        return r.matched_count > 0

    async def set_user_disabled(self, user_id: int, disabled: bool):
        await self.users.update_one({"_id": user_id}, {"$set": {"is_disabled": 1 if disabled else 0}})

    async def set_password_hash(self, user_id: int, password_hash: str):
        await self.users.update_one({"_id": user_id}, {"$set": {"password_hash": password_hash}})

    async def update_user_token(self, user_id: int, token: Optional[str], last_login_at: Optional[str] = None):
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(days=7)).isoformat() if token else None
        )
        update: dict = {"session_token": token or None, "token_expires_at": expires_at}
        if last_login_at:
            update["last_login_at"] = last_login_at
        await self.users.update_one({"_id": user_id}, {"$set": update})

    async def clear_all_tokens(self, company_id: Optional[str] = None) -> int:
        query: dict = {"session_token": {"$ne": None}}
        if company_id:
            query["company_id"] = company_id
        r = await self.users.update_many(query, {"$set": {"session_token": None}})
        return r.modified_count

    async def get_users_without_password(self, company_id: Optional[str] = None) -> list[str]:
        query: dict = {"$or": [{"password_hash": {"$exists": False}}, {"password_hash": None}]}
        if company_id:
            query["company_id"] = company_id
        return [doc["name"] async for doc in self.users.find(query, {"name": 1})]

    async def update_user_name(self, old_name: str, new_name: str) -> bool:
        r = await self.users.update_one({"name": old_name}, {"$set": {"name": new_name}})
        return r.matched_count > 0

    async def get_all_user_names(self, company_id: Optional[str] = None) -> list[str]:
        query: dict = {"is_disabled": {"$ne": 1}}
        if company_id:
            query["company_id"] = company_id
        return sorted([doc["name"] async for doc in self.users.find(query, {"name": 1})])

    async def remove_company_member(self, user_id: int) -> bool:
        r = await self.users.delete_one({"_id": user_id})
        return r.deleted_count > 0

    # ── Votes / Orders ────────────────────────────────────────────────────────────

    async def get_user_vote_for_date(self, user_id: int, date_str: str, status: Optional[str] = "pending") -> Optional[dict]:
        query: dict = {"user_id": user_id, "date": date_str}
        if status:
            query["status"] = status
        return await self.votes.find_one(query)

    async def has_user_pending_vote(self, user_id: int, date_str: str) -> bool:
        return await self.votes.count_documents({"user_id": user_id, "date": date_str, "status": "pending"}) > 0

    async def insert_vote(self, user_id: int, company_id: str, distributor_product_id: str,
                           product_name: str, product_emoji: str, qty: int,
                           price_at_order: float = 0, date_str: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        await self.votes.insert_one({
            "user_id": user_id,
            "company_id": company_id,
            "date": date_str or self._today(),
            "distributor_product_id": distributor_product_id,
            "product_name": product_name,
            "product_emoji": product_emoji,
            "qty": qty,
            "price_at_order": price_at_order,
            "status": "pending",
            "delivered_at": None,
            "delivered_by_user_id": None,
            "created_at": now,
            "updated_at": now,
        })

    async def update_vote(self, user_id: int, date_str: str, distributor_product_id: str,
                           product_name: str, product_emoji: str, qty: int, price_at_order: float = 0) -> bool:
        r = await self.votes.update_one(
            {"user_id": user_id, "date": date_str, "status": "pending"},
            {"$set": {
                "distributor_product_id": distributor_product_id,
                "product_name": product_name,
                "product_emoji": product_emoji,
                "qty": qty,
                "price_at_order": price_at_order,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return r.matched_count > 0

    async def delete_user_vote_for_date(self, user_id: int, date_str: str) -> bool:
        r = await self.votes.delete_one({"user_id": user_id, "date": date_str, "status": "pending"})
        return r.deleted_count > 0

    async def delete_user_today_vote(self, user_id: int) -> bool:
        return await self.delete_user_vote_for_date(user_id, self._today())

    async def get_user_today_vote(self, user_id: int) -> Optional[dict]:
        return await self.get_user_vote_for_date(user_id, self._today(), status="pending")

    async def has_user_voted_today(self, user_id: int) -> bool:
        return await self.has_user_pending_vote(user_id, self._today())

    async def get_user_orders_from_date(self, user_id: int, from_date: str) -> list[dict]:
        result = []
        async for doc in self.votes.find(
            {"user_id": user_id, "date": {"$gte": from_date}}, sort=[("date", 1)],
        ):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def get_vote_by_id(self, vote_id: str) -> Optional[dict]:
        try:
            doc = await self.votes.find_one({"_id": _oid(vote_id)})
        except Exception:
            return None
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def mark_order_delivered(self, vote_id: str, delivered_by_user_id: int,
                                    distributor_company_id: Optional[str] = None) -> bool:
        if distributor_company_id:
            vote = await self.get_vote_by_id(vote_id)
            if not vote:
                return False
            buyer = await self.get_company_by_id(vote["company_id"])
            if not buyer or buyer.get("distributor_id") != distributor_company_id:
                return False
        r = await self.votes.update_one(
            {"_id": _oid(vote_id), "status": "pending"},
            {"$set": {
                "status": "delivered",
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "delivered_by_user_id": delivered_by_user_id,
            }},
        )
        return r.matched_count > 0

    async def get_pending_orders_for_distributor(self, distributor_company_id: str,
                                                  company_id: Optional[str] = None) -> list[dict]:
        buyer_query: dict = {"distributor_id": distributor_company_id, "mode": "company"}
        if company_id:
            buyer_query["_id"] = _oid(company_id)
        buyers = {
            str(c["_id"]): _branch_label(c)
            async for c in self.companies.find(buyer_query, {"_id": 1, "name": 1, "address": 1})
        }
        if not buyers:
            return []
        pipeline = [
            {"$match": {"company_id": {"$in": list(buyers)}, "status": "pending"}},
            {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$project": {"_id": {"$toString": "$_id"}, "user_name": "$user.name",
                          "company_id": 1, "product_name": 1, "product_emoji": 1, "qty": 1, "date": 1}},
        ]
        rows = [doc async for doc in self.votes.aggregate(pipeline)]
        for r in rows:
            r["company_name"] = buyers.get(r["company_id"], "")
        rows.sort(key=lambda r: (r["company_name"], r["user_name"]))
        return rows

    async def delete_all_votes(self, company_id: Optional[str] = None):
        query = {}
        if company_id:
            query["company_id"] = company_id
        await self.votes.delete_many(query)

    # ── Today Board (all statuses — live/operational view) ──────────────────────

    async def get_today_totals(self, company_id: Optional[str] = None) -> dict:
        query: dict = {"date": self._today()}
        if company_id:
            query["company_id"] = company_id
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$product_name",
                "total": {"$sum": "$qty"},
                "emoji": {"$first": "$product_emoji"},
            }},
        ]
        result = {}
        async for doc in self.votes.aggregate(pipeline):
            result[doc["_id"]] = {"total": doc["total"], "emoji": doc.get("emoji", "")}
        return result

    async def get_today_order_count(self, company_id: Optional[str] = None) -> int:
        query: dict = {"date": self._today()}
        if company_id:
            query["company_id"] = company_id
        return await self.votes.count_documents(query)

    async def get_today_breakdown(self, company_id: Optional[str] = None) -> list[dict]:
        query: dict = {"date": self._today()}
        if company_id:
            query["company_id"] = company_id
        pipeline = [
            {"$match": query},
            {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$project": {"_id": 0, "name": "$user.name", "product_name": 1, "product_emoji": 1, "qty": 1, "status": 1}},
            {"$sort": {"name": 1}},
        ]
        return [doc async for doc in self.votes.aggregate(pipeline)]

    # ── Stats (historical — delivered only) ──────────────────────────────────────

    async def get_daily_totals_range(self, start_date: str, end_date: str, company_id: Optional[str] = None) -> list[dict]:
        match: dict = {"date": {"$gte": start_date, "$lte": end_date}, "status": "delivered"}
        if company_id:
            match["company_id"] = company_id
        pipeline = [
            {"$match": match},
            {"$group": {"_id": {"date": "$date", "product": "$product_name"}, "total": {"$sum": "$qty"}}},
            {"$sort": {"_id.date": 1}},
        ]
        by_date: dict = {}
        async for doc in self.votes.aggregate(pipeline):
            d = doc["_id"]["date"]
            prod = doc["_id"]["product"]
            if d not in by_date:
                by_date[d] = {"date": d, "products": {}, "tea": 0, "coffee": 0}
            by_date[d]["products"][prod] = doc["total"]
            if prod == "Tea":
                by_date[d]["tea"] = doc["total"]
            if prod == "Coffee":
                by_date[d]["coffee"] = doc["total"]
        return [by_date[d] for d in sorted(by_date)]

    async def get_user_orders_for_date(self, date_str: str, company_id: Optional[str] = None) -> list[dict]:
        match: dict = {"date": date_str, "status": "delivered"}
        if company_id:
            match["company_id"] = company_id
        pipeline = [
            {"$match": match},
            {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$project": {"_id": 0, "name": "$user.name", "product_name": 1, "product_emoji": 1, "qty": 1,
                          "tea": {"$cond": [{"$eq": ["$product_name", "Tea"]}, "$qty", 0]},
                          "coffee": {"$cond": [{"$eq": ["$product_name", "Coffee"]}, "$qty", 0]}}},
            {"$sort": {"name": 1}},
        ]
        return [doc async for doc in self.votes.aggregate(pipeline)]

    async def get_user_stats_range(self, name: str, start_date: str, end_date: str, company_id: Optional[str] = None) -> list[dict]:
        match: dict = {"date": {"$gte": start_date, "$lte": end_date}, "status": "delivered"}
        if company_id:
            match["company_id"] = company_id
        pipeline = [
            {"$match": match},
            {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$match": {"user.name": name}},
            {"$project": {"_id": 0, "date": 1, "product_name": 1, "product_emoji": 1, "qty": 1,
                          "tea": {"$cond": [{"$eq": ["$product_name", "Tea"]}, "$qty", 0]},
                          "coffee": {"$cond": [{"$eq": ["$product_name", "Coffee"]}, "$qty", 0]}}},
            {"$sort": {"date": 1}},
        ]
        return [doc async for doc in self.votes.aggregate(pipeline)]

    # ── Distributor Order Summary (delivered vs pending split) ──────────────────

    async def get_distributor_order_summary(self, distributor_company_id: str, date_str: Optional[str] = None) -> dict:
        date_str = date_str or self._today()
        buyers = {str(c["_id"]): _branch_label(c) async for c in self.companies.find(
            {"distributor_id": distributor_company_id, "mode": "company"}, {"_id": 1, "name": 1, "address": 1},
        )}
        if not buyers:
            return {"by_product": [], "by_company": [], "by_user": []}

        base_match = {"date": date_str, "company_id": {"$in": list(buyers)}}

        async def _agg(group_id_expr, name_key):
            pipeline = [
                {"$match": base_match},
                {"$group": {
                    "_id": group_id_expr,
                    "delivered_qty": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, "$qty", 0]}},
                    "delivered_count": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]}},
                    "pending_qty": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, "$qty", 0]}},
                    "pending_count": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                }},
                {"$sort": {"_id": 1}},
            ]
            rows = []
            async for doc in self.votes.aggregate(pipeline):
                rows.append({
                    name_key: doc["_id"], "delivered_qty": doc["delivered_qty"], "delivered_count": doc["delivered_count"],
                    "pending_qty": doc["pending_qty"], "pending_count": doc["pending_count"],
                })
            return rows

        by_product = await _agg("$product_name", "product_name")

        by_company_pipeline = [
            {"$match": base_match},
            {"$group": {
                "_id": "$company_id",
                "delivered_qty": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, "$qty", 0]}},
                "delivered_count": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]}},
                "pending_qty": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, "$qty", 0]}},
                "pending_count": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
            }},
        ]
        by_company = [
            {"company_name": buyers.get(doc["_id"], ""), "delivered_qty": doc["delivered_qty"], "delivered_count": doc["delivered_count"],
             "pending_qty": doc["pending_qty"], "pending_count": doc["pending_count"]}
            async for doc in self.votes.aggregate(by_company_pipeline)
        ]
        by_company.sort(key=lambda r: r["company_name"])

        by_user_pipeline = [
            {"$match": base_match},
            {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$group": {
                "_id": "$user.name",
                "delivered_qty": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, "$qty", 0]}},
                "delivered_count": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]}},
                "pending_qty": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, "$qty", 0]}},
                "pending_count": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]
        by_user = [
            {"user_name": doc["_id"], "delivered_qty": doc["delivered_qty"], "delivered_count": doc["delivered_count"],
             "pending_qty": doc["pending_qty"], "pending_count": doc["pending_count"]}
            async for doc in self.votes.aggregate(by_user_pipeline)
        ]

        return {"by_product": by_product, "by_company": by_company, "by_user": by_user}


db = MongoDatabase()
