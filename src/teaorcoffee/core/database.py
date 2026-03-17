import httpx
from typing import Optional


class SheetsDatabase:
    """Calls a Google Apps Script web app as the database layer"""

    _instance = None
    _url: str = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, url: str):
        self._url = url

    async def _get(self, params: dict) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(self._url, params=params, follow_redirects=True)
            r.raise_for_status()
            return r.json()

    async def _post(self, body: dict) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(self._url, json=body, follow_redirects=True)
            r.raise_for_status()
            return r.json()

    # ---- Setup ----

    async def seed_users(self, names: list[str]):
        await self._post({"action": "seed_users", "names": names})

    # ---- Users ----

    async def get_user_by_name(self, name: str) -> Optional[dict]:
        result = await self._get({"action": "get_user_by_name", "name": name})
        return result.get("data")

    async def get_user_by_token(self, token: str) -> Optional[dict]:
        result = await self._get({"action": "get_user_by_token", "token": token})
        return result.get("data")

    async def update_user_token(self, user_id: int, token: Optional[str], last_login_at: Optional[str] = None):
        await self._post({
            "action": "update_user_token",
            "user_id": user_id,
            "token": token or "",
            "last_login_at": last_login_at or "",
        })

    async def clear_all_tokens(self) -> int:
        result = await self._post({"action": "clear_all_tokens"})
        return result.get("data", {}).get("count", 0)

    # ---- Votes ----

    async def get_today_totals(self) -> dict:
        result = await self._get({"action": "get_today_totals"})
        return result.get("data", {"tea": 0, "coffee": 0})

    async def get_user_today_vote(self, user_id: int) -> Optional[dict]:
        result = await self._get({"action": "get_user_today_vote", "user_id": user_id})
        return result.get("data")

    async def has_user_voted_today(self, user_id: int) -> bool:
        result = await self._get({"action": "has_user_voted_today", "user_id": user_id})
        return bool(result.get("data", False))

    async def count_today_votes(self) -> int:
        result = await self._get({"action": "count_today_votes"})
        return int(result.get("data", 0))

    async def insert_vote(self, user_id: int, tea: int, coffee: int):
        await self._post({"action": "insert_vote", "user_id": user_id, "tea": tea, "coffee": coffee})

    async def delete_all_votes(self):
        await self._post({"action": "delete_all_votes"})

    async def delete_user_today_vote(self, user_id: int) -> bool:
        result = await self._post({"action": "delete_user_today_vote", "user_id": user_id})
        return bool(result.get("data", {}).get("deleted", False))

    async def get_today_breakdown(self) -> list[dict]:
        result = await self._get({"action": "get_today_breakdown"})
        return result.get("data", [])


# Global database instance
db = SheetsDatabase()
