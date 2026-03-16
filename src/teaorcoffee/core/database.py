import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator


class Database:
    """Singleton database connection manager"""

    _instance = None
    _db_path: str = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, db_path: str):
        """Set database path"""
        self._db_path = db_path

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get database connection with context manager"""
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn


# Global database instance
db = Database()
