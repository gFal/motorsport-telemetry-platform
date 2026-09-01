import os
import asyncpg


_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the shared database connection pool."""
    global _pool

    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "motorsport"),
            user=os.getenv("DB_USER", "pitwall"),
            password=os.getenv("DB_PASSWORD", "pitwall"),
            min_size=2,
            max_size=10,
        )

    return _pool


async def close_pool() -> None:
    """Close and clear the shared database connection pool."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None