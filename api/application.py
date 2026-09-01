from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from database import close_pool, get_pool
from models import LatestReading, TelemetryPacket, TelemetryResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and close the database connection pool."""
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Motorsport Telemetry API",
    description="Race car sensor ingestion and query service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Return the service health status."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc),
    }


@app.post("/telemetry", response_model=TelemetryResponse, status_code=201)
async def ingest_telemetry(packet: TelemetryPacket):
    """Ingest a sensor reading and return the stored record."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        sensor = await conn.fetchrow(
            "SELECT id FROM sensors WHERE id = $1",
            packet.sensor_id,
        )

        if sensor is None:
            detail = f"Sensor {packet.sensor_id} not found"
            raise HTTPException(status_code=404, detail=detail)

        row = await conn.fetchrow(
            """
            INSERT INTO telemetry (sensor_id, value, recorded_at)
            VALUES ($1, $2, $3)
            RETURNING id, sensor_id, value, recorded_at
            """,
            packet.sensor_id,
            packet.value,
            packet.recorded_at,
        )

    return TelemetryResponse(**dict(row))


@app.get("/cars/{car_id}/latest", response_model=list[LatestReading])
async def latest_readings(car_id: int):
    """Return the latest reading for every sensor channel on a car."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        car = await conn.fetchrow(
            "SELECT id FROM cars WHERE id = $1",
            car_id,
        )

        if car is None:
            detail = f"Car {car_id} not found"
            raise HTTPException(status_code=404, detail=detail)

        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (s.channel_name)
                s.channel_name,
                t.value,
                t.recorded_at
            FROM telemetry t
            JOIN sensors s ON s.id = t.sensor_id
            WHERE s.car_id = $1
            ORDER BY s.channel_name, t.recorded_at DESC
            """,
            car_id,
        )

    return [LatestReading(**dict(row)) for row in rows]


@app.get("/telemetry/history", response_model=list[TelemetryResponse])
async def telemetry_history(sensor_id: int, minutes: int = 5):
    """Return recent readings for a sensor."""
    if not 1 <= minutes <= 60:
        raise HTTPException(
            status_code=400,
            detail="minutes must be between 1 and 60",
        )

    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, sensor_id, value, recorded_at
            FROM telemetry
            WHERE sensor_id = $1
              AND recorded_at >= NOW() - ($2 * INTERVAL '1 minute')
            ORDER BY recorded_at DESC
            """,
            sensor_id,
            minutes,
        )

    return [TelemetryResponse(**dict(row)) for row in rows]