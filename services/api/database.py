"""Database access for the telemetry API.

A single asyncpg connection pool is shared by all requests in the process. It is created once at application start-up  
so that a pod which cannot reach PostgreSQL - wrong credentials, database down - fails immediately and never becomes Ready.

All database waits are bounded by timeouts. While PostgreSQL is unavailable, 
requests fail within a few seconds instead of hanging - the API turns these failures into HTTP 503 responses.
"""
import os

import asyncpg

# Upper bound, in seconds, for any single wait on the database: opening a connection, acquiring one from the pool, or running a query.
DB_TIMEOUT_SECONDS = float(os.getenv("DB_TIMEOUT_SECONDS", "5"))

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the shared connection pool, creating it on first use.
    
    Raises the underlying asyncpg or OS error if PostgreSQL cannot be reached within DB_TIMEOUT_SECONDS, so a failed start-up is visible immediately.
    """
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
            # Fail fast instead of hanging while PostgreSQL is unreachable.
            timeout=DB_TIMEOUT_SECONDS,          # opening a new connection
            command_timeout=DB_TIMEOUT_SECONDS,  # any single query
        )

    return _pool


async def close_pool() -> None:
    """Close and clear the shared database connection pool."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None