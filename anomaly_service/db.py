"""
Async PostgreSQL connection pool and queries for the anomaly service.
Separate from the FastAPI db layer — this is an independent process with its own pool, its own connection lifecycle, and its own failure mode.
"""

import asyncpg
import config

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool

    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            min_size=config.DB_POOL_MIN_SIZE,
            max_size=config.DB_POOL_MAX_SIZE,
        )

    return _pool


async def close_pool() -> None:
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None


# DISTINCT ON (s.id) guarantees one row per sensor — the most recent.
# LEFT JOIN means sensors that have never reported come back with NULL value/recorded_at, which the SILENT check catches.
LATEST_READINGS_QUERY = """
    SELECT DISTINCT ON (s.id)
        s.id AS sensor_id,
        s.car_id AS car_id,
        s.channel_name AS channel_name,
        t.value AS value,
        t.recorded_at AS recorded_at
    FROM sensors s
    LEFT JOIN telemetry t ON t.sensor_id = s.id
    ORDER BY s.id, t.recorded_at DESC NULLS LAST;
"""


async def fetch_latest_readings(
    pool: asyncpg.Pool,
) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(LATEST_READINGS_QUERY)


INSERT_ALERT_QUERY = """
    INSERT INTO alerts
        (
            sensor_id,
            car_id,
            channel_name,
            alert_type,
            message,
            value,
            detected_at
        )
    VALUES ($1, $2, $3, $4, $5, $6, NOW())
    RETURNING id, detected_at;
"""


async def insert_alert(
    pool: asyncpg.Pool,
    sensor_id: int,
    car_id: int,
    channel_name: str,
    alert_type: str,
    message: str,
    value: float | None,
) -> asyncpg.Record:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            INSERT_ALERT_QUERY,
            sensor_id,
            car_id,
            channel_name,
            alert_type,
            message,
            value,
        )