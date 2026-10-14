"""A reading sent to the API is stored in the database."""
import random

from support.waiting import wait_until


def test_posted_reading_is_persisted(api, db, canary_sensor_id):
    value = round(random.uniform(90.0, 99.0), 3)  # in range: must not trigger an alert
    since = db.now()

    api.post_reading(canary_sensor_id, value)

    wait_until(
        lambda: int(db.scalar(
            "SELECT count(*) FROM telemetry "
            f"WHERE sensor_id = {canary_sensor_id} AND value = {value} "
            f"AND recorded_at > '{since}'::timestamptz - interval '5 seconds'")) == 1,
        timeout=15, desc="reading persisted in telemetry table")