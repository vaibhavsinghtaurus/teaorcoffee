from src.teaorcoffee.core.database import db
from src.teaorcoffee.core.config import settings


async def initialize_database():
    """Create tables and seed initial data"""
    async with db.get_connection() as conn:
        # Create allowed_users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS allowed_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                ip_address TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_login_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)

        # Create user_votes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tea INTEGER NOT NULL DEFAULT 0,
                coffee INTEGER NOT NULL DEFAULT 0,
                voted_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES allowed_users(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_allowed_users_name ON allowed_users(name)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_allowed_users_ip ON allowed_users(ip_address)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_votes_user_id ON user_votes(user_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_votes_user_date ON user_votes(user_id, voted_at)"
        )

        # Seed allowed users
        for name in settings.allowed_names:
            await conn.execute(
                "INSERT OR IGNORE INTO allowed_users (name, is_active) VALUES (?, 1)",
                (name,),
            )

        await conn.commit()
