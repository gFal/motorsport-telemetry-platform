"""Motorsport Telemetry API.

HTTP service that ingests race-car sensor readings and serves queries over them. Readings are stored in PostgreSQL through a shared asyncpg pool.

Failure behaviour, by design:
- Start-up connects to the database and fails if it cannot. A pod with a wrong password or no database never becomes Ready, so a bad rollout cannot replace working pods.
- /health is a liveness check only and never touches the database. A database outage must not make Kubernetes restart healthy API processes.
- Every database wait is bounded (database.DB_TIMEOUT_SECONDS). 
  While PostgreSQL is unavailable, data endpoints answer 503 within seconds instead of hanging, and recover on their own once the database is back.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from database import DB_TIMEOUT_SECONDS, close_pool, get_pool
from models import LatestReading, TelemetryPacket, TelemetryResponse

logger = logging.getLogger("uvicorn.error")

# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database pool at start-up and close it on shutdown.

    If PostgreSQL is unreachable or rejects the credentials, get_pool() raises and the process exits: 
    Kubernetes keeps the pod out of service instead of routing traffic to an API that cannot work.
    """
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Motorsport Telemetry API",
    description="Race car sensor ingestion and query service",
    version="1.0.0",
    lifespan=lifespan,
)


@asynccontextmanager
async def db_connection():
    """Borrow a connection from the shared pool for the duration of a block.

    Waiting for a free connection is bounded by DB_TIMEOUT_SECONDS, so a pool exhausted by a slow or unavailable database fails fast (TimeoutError → 503).
    """
    pool = await get_pool()
    async with pool.acquire(timeout=DB_TIMEOUT_SECONDS) as conn:
        yield conn


# Error handling
@app.exception_handler(asyncpg.PostgresError)   # errors reported by PostgreSQL, incl. "starting up"
@app.exception_handler(asyncpg.InterfaceError)  # connection lost or closed mid-request
@app.exception_handler(OSError)                 # connection refused/reset while PostgreSQL is down
@app.exception_handler(TimeoutError)            # connect, acquire or query exceeded the timeout
async def database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    """Report database failures as 503 Service Unavailable.

    503 tells clients and monitoring that the failure is temporary and on the server side.
    Retry-After suggests when to try again. The API holds no files or sockets other than its database connections, so OSError here means a database connection problem.
    """
    logger.warning("Database unavailable on %s %s: %r", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "database unavailable"},
        headers={"Retry-After": "5"},
    )


# Endpoints
@app.get("/health")
async def health():
    """Liveness check: the process is running and serving HTTP.

    Deliberately does not query the database. 
    If it did, a database outage would fail the liveness probe and Kubernetes would restart every API pod, turning a database incident into a full API outage.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc),
    }


@app.post("/telemetry", response_model=TelemetryResponse, status_code=201)
async def ingest_telemetry(packet: TelemetryPacket):
    """"Store one sensor reading and return the stored record.

    Returns 404 if the sensor does not exist, 422 for an invalid payload (validated by TelemetryPacket) and 503 if the database is unavailable.
    """
    async with db_connection() as conn:
        sensor = await conn.fetchrow(
            "SELECT id FROM sensors WHERE id = $1",
            packet.sensor_id,
        )

        if sensor is None:
            raise HTTPException(status_code=404, detail=f"Sensor {packet.sensor_id} not found")


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
    """Return the latest reading for every sensor channel on a car.
    
    Returns 404 if the car doesn't exist and 503 if the database is unavailable.
    """
    async with db_connection() as conn:
        car = await conn.fetchrow(
            "SELECT id FROM cars WHERE id = $1",
            car_id,
        )

        if car is None:
            raise HTTPException(status_code=404, detail=f"Car {car_id} not found")

        # DISTINCT ON keeps the first row per channel 
        # ordering by recorded_at DESC makes that first row the latest reading.
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
    """Return recent readings for a sensor.
    
    Returns 400 if `minutes` is outside 1-60 and 503 if the database is unavailable.
    """
    if not 1 <= minutes <= 60:
        raise HTTPException(status_code=400, detail="minutes must be between 1 and 60")
 
    async with db_connection() as conn:
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