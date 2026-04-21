from datetime import date, datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient


class MongoDatabase:
    """MongoDB database layer using motor (async)"""

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

    def _today(self) -> str:
        return date.today().isoformat()

    # ---- Setup ----

    async def seed_users(self, names: list[str]):
        existing = {u["name"] async for u in self.users.find({}, {"name": 1})}
        last = await self.users.find_one(sort=[("_id", -1)])
        next_id = (last["_id"] + 1) if last else 1

        new_users = []
        for name in names:
            if name not in existing:
                new_users.append({
                    "_id": next_id,
                    "name": name,
                    "is_active": 1,
                    "is_disabled": 0,
                    "session_token": None,
                    "last_login_at": None,
                })
                next_id += 1

        if new_users:
            await self.users.insert_many(new_users)

        # Patch existing users that predate the is_disabled field
        await self.users.update_many(
            {"is_disabled": {"$exists": False}},
            {"$set": {"is_disabled": 0}},
        )

    # ---- Users ----

    async def get_user_by_name(self, name: str) -> Optional[dict]:
        user = await self.users.find_one({"name": name})
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

    async def set_user_disabled(self, user_id: int, disabled: bool):
        await self.users.update_one({"_id": user_id}, {"$set": {"is_disabled": 1 if disabled else 0}})

    async def set_password_hash(self, user_id: int, password_hash: str):
        await self.users.update_one({"_id": user_id}, {"$set": {"password_hash": password_hash}})

    async def update_user_token(self, user_id: int, token: Optional[str], last_login_at: Optional[str] = None):
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            if token else None
        )
        update: dict = {"session_token": token or None, "token_expires_at": expires_at}
        if last_login_at:
            update["last_login_at"] = last_login_at
        await self.users.update_one({"_id": user_id}, {"$set": update})

    async def clear_all_tokens(self) -> int:
        result = await self.users.update_many(
            {"session_token": {"$ne": None}},
            {"$set": {"session_token": None}},
        )
        return result.modified_count

    async def get_users_without_password(self) -> list[str]:
        cursor = self.users.find(
            {"$or": [{"password_hash": {"$exists": False}}, {"password_hash": None}]},
            {"name": 1},
        )
        return [doc["name"] async for doc in cursor]

    async def update_user_name(self, old_name: str, new_name: str) -> bool:
        result = await self.users.update_one({"name": old_name}, {"$set": {"name": new_name}})
        return result.matched_count > 0

    # ---- Votes ----

    async def get_today_totals(self) -> dict:
        pipeline = [
            {"$match": {"date": self._today()}},
            {"$group": {"_id": None, "tea": {"$sum": "$tea"}, "coffee": {"$sum": "$coffee"}}},
        ]
        async for doc in self.votes.aggregate(pipeline):
            return {"tea": doc["tea"], "coffee": doc["coffee"]}
        return {"tea": 0, "coffee": 0}

    async def get_user_today_vote(self, user_id: int) -> Optional[dict]:
        return await self.votes.find_one({"user_id": user_id, "date": self._today()})

    async def has_user_voted_today(self, user_id: int) -> bool:
        count = await self.votes.count_documents({"user_id": user_id, "date": self._today()})
        return count > 0

    async def count_today_votes(self) -> int:
        return await self.votes.count_documents({"date": self._today()})

    async def insert_vote(self, user_id: int, tea: int, coffee: int):
        await self.votes.insert_one({
            "user_id": user_id,
            "tea": tea,
            "coffee": coffee,
            "date": self._today(),
        })

    async def delete_all_votes(self):
        await self.votes.delete_many({})

    async def delete_user_today_vote(self, user_id: int) -> bool:
        result = await self.votes.delete_one({"user_id": user_id, "date": self._today()})
        return result.deleted_count > 0

    async def get_today_breakdown(self) -> list[dict]:
        pipeline = [
            {"$match": {"date": self._today()}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user",
            }},
            {"$unwind": "$user"},
            {"$project": {"_id": 0, "name": "$user.name", "tea": 1, "coffee": 1}},
        ]
        result = []
        async for doc in self.votes.aggregate(pipeline):
            result.append(doc)
        return result


# Global database instance
db = MongoDatabase()
