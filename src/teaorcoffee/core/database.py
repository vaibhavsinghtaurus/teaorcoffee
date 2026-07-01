from datetime import date, datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        return ObjectId()


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
    def allowed_names(self):
        return self._db["allowed_names"]

    @property
    def offices(self):
        return self._db["offices"]

    @property
    def products(self):
        return self._db["products"]

    @property
    def distributor_companies(self):
        return self._db["distributor_companies"]

    @property
    def positions(self):
        return self._db["positions"]

    @property
    def office_requests(self):
        return self._db["office_requests"]

    def _today(self) -> str:
        return date.today().isoformat()

    # ── Setup / Main Admin ─────────────────────────────────────────────────────

    async def has_main_admin(self) -> bool:
        return await self.users.count_documents({"role": "main_admin"}) > 0

    async def get_main_admin(self) -> Optional[dict]:
        user = await self.users.find_one({"role": "main_admin"})
        if user:
            user["id"] = user["_id"]
        return user

    # ── Offices ────────────────────────────────────────────────────────────────

    async def create_office(self, name: str, slug: str) -> str:
        existing = await self.offices.find_one({"slug": slug})
        if existing:
            return str(existing["_id"])
        result = await self.offices.insert_one({
            "name": name,
            "slug": slug,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return str(result.inserted_id)

    async def get_all_offices(self) -> list[dict]:
        result = []
        async for doc in self.offices.find({}, sort=[("name", 1)]):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def get_active_offices(self) -> list[dict]:
        result = []
        async for doc in self.offices.find({"is_active": True}, sort=[("name", 1)]):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def get_office_by_id(self, office_id: str) -> Optional[dict]:
        try:
            doc = await self.offices.find_one({"_id": _oid(office_id)})
        except Exception:
            return None
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def get_office_by_slug(self, slug: str) -> Optional[dict]:
        doc = await self.offices.find_one({"slug": slug})
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def update_office(self, office_id: str, name: str) -> bool:
        r = await self.offices.update_one({"_id": _oid(office_id)}, {"$set": {"name": name}})
        return r.matched_count > 0

    async def set_office_active(self, office_id: str, is_active: bool) -> bool:
        r = await self.offices.update_one({"_id": _oid(office_id)}, {"$set": {"is_active": is_active}})
        return r.matched_count > 0

    # ── Products ───────────────────────────────────────────────────────────────

    async def get_products(self, office_id: str, include_inactive: bool = False) -> list[dict]:
        query: dict = {"office_id": office_id}
        if not include_inactive:
            query["is_active"] = True
        result = []
        async for doc in self.products.find(query, sort=[("sort_order", 1), ("name", 1)]):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def get_product_by_id(self, product_id: str) -> Optional[dict]:
        try:
            doc = await self.products.find_one({"_id": _oid(product_id)})
        except Exception:
            return None
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def add_product(self, office_id: str, name: str, emoji: str, max_qty: int) -> tuple[str, bool]:
        existing = await self.products.find_one({"office_id": office_id, "name": name})
        if existing:
            if not existing.get("is_active"):
                await self.products.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"is_active": True, "emoji": emoji, "max_qty": max_qty}},
                )
                return str(existing["_id"]), True
            return str(existing["_id"]), False
        last = await self.products.find_one({"office_id": office_id}, sort=[("sort_order", -1)])
        sort_order = (last["sort_order"] + 1) if last else 0
        result = await self.products.insert_one({
            "office_id": office_id,
            "name": name,
            "emoji": emoji,
            "max_qty": max_qty,
            "is_active": True,
            "sort_order": sort_order,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return str(result.inserted_id), True

    async def update_product(self, product_id: str, name: str, emoji: str, max_qty: int) -> bool:
        r = await self.products.update_one(
            {"_id": _oid(product_id)},
            {"$set": {"name": name, "emoji": emoji, "max_qty": max_qty}},
        )
        return r.matched_count > 0

    async def set_product_active(self, product_id: str, is_active: bool) -> bool:
        r = await self.products.update_one({"_id": _oid(product_id)}, {"$set": {"is_active": is_active}})
        return r.matched_count > 0

    async def seed_products(self, office_id: str, products: list[dict]):
        for i, p in enumerate(products):
            if not await self.products.find_one({"office_id": office_id, "name": p["name"]}):
                await self.products.insert_one({
                    "office_id": office_id,
                    "name": p["name"],
                    "emoji": p["emoji"],
                    "max_qty": p["max_qty"],
                    "is_active": True,
                    "sort_order": i,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

    # ── Allowed Names ──────────────────────────────────────────────────────────

    async def get_allowed_names(self, office_id: Optional[str] = None) -> list[str]:
        query: dict = {}
        if office_id:
            query["office_id"] = office_id
        return [doc["name"] async for doc in self.allowed_names.find(query, {"name": 1})]

    async def add_allowed_name(self, name: str, office_id: str) -> bool:
        if await self.allowed_names.find_one({"name": name}):
            return False
        last = await self.allowed_names.find_one(sort=[("_id", -1)])
        next_id = (last["_id"] + 1) if last else 1
        await self.allowed_names.insert_one({
            "_id": next_id,
            "name": name,
            "office_id": office_id,
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
        await self.seed_users([name], office_id)
        return True

    async def remove_allowed_name(self, name: str) -> bool:
        r = await self.allowed_names.delete_one({"name": name})
        return r.deleted_count > 0

    async def seed_allowed_names(self, names: list[str], office_id: str):
        existing = {doc["name"] async for doc in self.allowed_names.find({}, {"name": 1})}
        last = await self.allowed_names.find_one(sort=[("_id", -1)])
        next_id = (last["_id"] + 1) if last else 1
        new_docs = []
        for name in names:
            if name not in existing:
                new_docs.append({
                    "_id": next_id,
                    "name": name,
                    "office_id": office_id,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                })
                next_id += 1
        if new_docs:
            await self.allowed_names.insert_many(new_docs)

    # ── Users ──────────────────────────────────────────────────────────────────

    async def seed_users(self, names: list[str], office_id: str, role: str = "user"):
        existing = {u["name"] async for u in self.users.find({}, {"name": 1})}
        last = await self.users.find_one(sort=[("_id", -1)])
        next_id = (last["_id"] + 1) if last else 1
        new_users = []
        for name in names:
            if name not in existing:
                new_users.append({
                    "_id": next_id,
                    "name": name,
                    "office_id": office_id,
                    "role": role,
                    "is_active": 1,
                    "is_disabled": 0,
                    "session_token": None,
                    "last_login_at": None,
                })
                next_id += 1
        if new_users:
            await self.users.insert_many(new_users)

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

    async def get_users_for_office(self, office_id: str) -> list[dict]:
        result = []
        async for u in self.users.find({"office_id": office_id}, sort=[("name", 1)]):
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

    async def clear_all_tokens(self, office_id: Optional[str] = None) -> int:
        query: dict = {"session_token": {"$ne": None}}
        if office_id:
            query["office_id"] = office_id
        r = await self.users.update_many(query, {"$set": {"session_token": None}})
        return r.modified_count

    async def get_users_without_password(self, office_id: Optional[str] = None) -> list[str]:
        query: dict = {"$or": [{"password_hash": {"$exists": False}}, {"password_hash": None}]}
        if office_id:
            query["office_id"] = office_id
        return [doc["name"] async for doc in self.users.find(query, {"name": 1})]

    async def update_user_name(self, old_name: str, new_name: str) -> bool:
        r = await self.users.update_one({"name": old_name}, {"$set": {"name": new_name}})
        return r.matched_count > 0

    async def get_all_user_names(self, office_id: Optional[str] = None) -> list[str]:
        query: dict = {"is_disabled": {"$ne": 1}, "role": {"$nin": ["company_admin", "distributor_staff"]}}
        if office_id:
            query["office_id"] = office_id
        return sorted([doc["name"] async for doc in self.users.find(query, {"name": 1})])

    # ── Votes ──────────────────────────────────────────────────────────────────

    async def get_today_totals(self, office_id: Optional[str] = None) -> dict:
        query: dict = {"date": self._today()}
        if office_id:
            query["office_id"] = office_id
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

    async def get_today_order_count(self, office_id: Optional[str] = None) -> int:
        query: dict = {"date": self._today()}
        if office_id:
            query["office_id"] = office_id
        return await self.votes.count_documents(query)

    async def get_user_today_vote(self, user_id: int) -> Optional[dict]:
        return await self.votes.find_one({"user_id": user_id, "date": self._today()})

    async def has_user_voted_today(self, user_id: int) -> bool:
        return await self.votes.count_documents({"user_id": user_id, "date": self._today()}) > 0

    async def insert_vote(self, user_id: int, office_id: str, product_id: str, product_name: str, product_emoji: str, qty: int):
        await self.votes.insert_one({
            "user_id": user_id,
            "office_id": office_id,
            "date": self._today(),
            "product_id": product_id,
            "product_name": product_name,
            "product_emoji": product_emoji,
            "qty": qty,
        })

    async def delete_all_votes(self, office_id: Optional[str] = None):
        query = {}
        if office_id:
            query["office_id"] = office_id
        await self.votes.delete_many(query)

    async def delete_user_today_vote(self, user_id: int) -> bool:
        r = await self.votes.delete_one({"user_id": user_id, "date": self._today()})
        return r.deleted_count > 0

    async def get_today_breakdown(self, office_id: Optional[str] = None) -> list[dict]:
        query: dict = {"date": self._today()}
        if office_id:
            query["office_id"] = office_id
        pipeline = [
            {"$match": query},
            {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$project": {"_id": 0, "name": "$user.name", "product_name": 1, "product_emoji": 1, "qty": 1}},
            {"$sort": {"name": 1}},
        ]
        result = []
        async for doc in self.votes.aggregate(pipeline):
            result.append(doc)
        return result

    # ── Stats ──────────────────────────────────────────────────────────────────

    async def get_daily_totals_range(self, start_date: str, end_date: str, office_id: Optional[str] = None) -> list[dict]:
        match: dict = {"date": {"$gte": start_date, "$lte": end_date}}
        if office_id:
            match["office_id"] = office_id
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

    async def get_user_orders_for_date(self, date_str: str, office_id: Optional[str] = None) -> list[dict]:
        match: dict = {"date": date_str}
        if office_id:
            match["office_id"] = office_id
        pipeline = [
            {"$match": match},
            {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$project": {"_id": 0, "name": "$user.name", "product_name": 1, "product_emoji": 1, "qty": 1,
                          "tea": {"$cond": [{"$eq": ["$product_name", "Tea"]}, "$qty", 0]},
                          "coffee": {"$cond": [{"$eq": ["$product_name", "Coffee"]}, "$qty", 0]}}},
            {"$sort": {"name": 1}},
        ]
        result = []
        async for doc in self.votes.aggregate(pipeline):
            result.append(doc)
        return result

    async def get_user_stats_range(self, name: str, start_date: str, end_date: str, office_id: Optional[str] = None) -> list[dict]:
        match: dict = {"date": {"$gte": start_date, "$lte": end_date}}
        if office_id:
            match["office_id"] = office_id
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
        result = []
        async for doc in self.votes.aggregate(pipeline):
            result.append(doc)
        return result

    # ── Distributor Companies ──────────────────────────────────────────────────

    async def create_distributor_company(self, name: str, office_id: str) -> tuple[str, bool]:
        existing = await self.distributor_companies.find_one({"name": name, "office_id": office_id})
        if existing:
            return str(existing["_id"]), False
        result = await self.distributor_companies.insert_one({
            "name": name,
            "office_id": office_id,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return str(result.inserted_id), True

    async def get_distributor_companies(self, office_id: Optional[str] = None) -> list[dict]:
        query: dict = {}
        if office_id:
            query["office_id"] = office_id
        result = []
        async for doc in self.distributor_companies.find(query, sort=[("name", 1)]):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def get_distributor_company_by_id(self, company_id: str) -> Optional[dict]:
        try:
            doc = await self.distributor_companies.find_one({"_id": _oid(company_id)})
        except Exception:
            return None
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def set_company_active(self, company_id: str, is_active: bool) -> bool:
        r = await self.distributor_companies.update_one({"_id": _oid(company_id)}, {"$set": {"is_active": is_active}})
        return r.matched_count > 0

    # ── Positions ──────────────────────────────────────────────────────────────

    async def get_positions(self, company_id: str) -> list[dict]:
        result = []
        async for doc in self.positions.find({"company_id": company_id, "is_active": True}, sort=[("level", 1)]):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def add_position(self, company_id: str, name: str, level: int) -> tuple[str, bool]:
        existing = await self.positions.find_one({"company_id": company_id, "name": name})
        if existing:
            return str(existing["_id"]), False
        result = await self.positions.insert_one({
            "company_id": company_id,
            "name": name,
            "level": level,
            "is_active": True,
        })
        return str(result.inserted_id), True

    async def remove_position(self, position_id: str) -> bool:
        r = await self.positions.update_one({"_id": _oid(position_id)}, {"$set": {"is_active": False}})
        return r.matched_count > 0

    # ── Distributor Staff ──────────────────────────────────────────────────────

    async def get_distributor_staff(self, company_id: str) -> list[dict]:
        result = []
        async for u in self.users.find({"company_id": company_id}, sort=[("name", 1)]):
            u["id"] = u["_id"]
            result.append(u)
        return result

    async def add_distributor_staff(self, name: str, company_id: str, role: str, position: str) -> bool:
        if await self.users.find_one({"name": name}):
            return False
        last = await self.users.find_one(sort=[("_id", -1)])
        next_id = (last["_id"] + 1) if last else 1
        await self.users.insert_one({
            "_id": next_id,
            "name": name,
            "company_id": company_id,
            "office_id": None,
            "role": role,
            "position": position,
            "is_active": 1,
            "is_disabled": 0,
            "session_token": None,
            "last_login_at": None,
        })
        return True

    async def remove_distributor_staff(self, user_id: int) -> bool:
        r = await self.users.delete_one({"_id": user_id})
        return r.deleted_count > 0

    # ── Office Requests ────────────────────────────────────────────────────────

    async def create_office_request(self, office_name: str, requester_name: str, contact_info: str) -> str:
        result = await self.office_requests.insert_one({
            "office_name": office_name,
            "requester_name": requester_name,
            "contact_info": contact_info,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return str(result.inserted_id)

    async def get_office_requests(self, status: Optional[str] = None) -> list[dict]:
        query: dict = {}
        if status:
            query["status"] = status
        result = []
        async for doc in self.office_requests.find(query, sort=[("created_at", -1)]):
            doc["id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def update_office_request_status(self, request_id: str, status: str) -> bool:
        r = await self.office_requests.update_one(
            {"_id": _oid(request_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return r.matched_count > 0

    async def get_office_request_by_id(self, request_id: str) -> Optional[dict]:
        try:
            doc = await self.office_requests.find_one({"_id": _oid(request_id)})
        except Exception:
            return None
        if doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def count_pending_office_requests(self) -> int:
        return await self.office_requests.count_documents({"status": "pending"})

    # ── Full-office seeding ────────────────────────────────────────────────────

    async def create_full_office(
        self,
        name: str,
        slug: str,
        employee_names: list[str],
        admin_names: list[str],
        hr_names: list[str],
    ) -> dict:
        office_id = await self.create_office(name, slug)
        await self.seed_products(office_id, [
            {"name": "Tea", "emoji": "🍵", "max_qty": 2},
            {"name": "Coffee", "emoji": "☕", "max_qty": 1},
        ])
        all_names = list(dict.fromkeys(employee_names + admin_names + hr_names))
        await self.seed_allowed_names(all_names, office_id)
        await self.seed_users(all_names, office_id, role="user")
        admin_set = set(admin_names)
        hr_set = set(hr_names)
        for uname in all_names:
            user = await self.get_user_by_name(uname)
            if not user:
                continue
            if uname in admin_set:
                await self.set_user_role(int(user["id"]), "office_admin")
            elif uname in hr_set:
                await self.set_user_role(int(user["id"]), "office_hr")
        return {"office_id": office_id, "name": name}


db = MongoDatabase()
