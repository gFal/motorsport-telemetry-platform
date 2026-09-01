"""
Polls every POLL_INTERVAL_SECONDS, writes new alerts to the DB and log file.

This is a standalone process — separate from FastAPI, with its own DB pool.
That separation means: different failure domain, different restart policy, independently scalable when this moves to Kubernetes.
"""

import asyncio
from datetime import datetime, timezone
import config
import db
from alerts_log import log_alert
from rules import AnomalyState, evaluate_row


async def poll_once(
    pool,
    state: AnomalyState,
) -> None:
    now = datetime.now(timezone.utc)
    rows = await db.fetch_latest_readings(pool)

    new_count = 0

    for row in rows:
        for alert in evaluate_row(row, now, state):
            db_row = await db.insert_alert(
                pool,
                alert["sensor_id"],
                alert["car_id"],
                alert["channel_name"],
                alert["alert_type"],
                alert["message"],
                alert["value"],
            )

            log_alert(
                alert,
                db_row["detected_at"],
            )

            print(
                f"[ALERT] {alert['alert_type']} | {alert['message']}"
            )

            new_count += 1

    if new_count == 0:
        print(
            f"[{now.isoformat()}] Poll OK — "
            f"{len(rows)} sensors checked, no new alerts."
        )


async def main() -> None:
    print("Anomaly detection service starting...")
    print(
        f"   DB:             "
        f"{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )
    print(
        f"   Poll interval:  "
        f"{config.POLL_INTERVAL_SECONDS}s"
    )
    print(
        f"   Silent after:   "
        f"{config.SILENT_THRESHOLD_SECONDS}s"
    )
    print(
        f"   Engine temp max:"
        f"{config.ENGINE_TEMP_MAX_C}C"
    )
    print(
        f"   Tyre PSI min:   "
        f"{config.TYRE_PRESSURE_MIN_PSI}"
    )
    print(
        f"   Log:            "
        f"{config.ALERTS_LOG_PATH}"
    )
    print()

    pool = await db.get_pool()
    state = AnomalyState()

    try:
        while True:
            try:
                await poll_once(pool, state)

            except Exception as e:
                print(f"[ERROR] Poll failed: {exc}")

            await asyncio.sleep(
                config.POLL_INTERVAL_SECONDS
            )

    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())