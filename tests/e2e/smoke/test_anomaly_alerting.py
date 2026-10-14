"""An out-of-range reading produces an OUT_OF_RANGE alert (API → DB → detector → alerts)."""
import time

from support.waiting import wait_until


def test_out_of_range_reading_raises_alert(api, db, settings, canary_sensor_id):
    # The detector only alerts on a normal → anomalous TRANSITION.
    api.post_reading(canary_sensor_id, 95.0)
    time.sleep(settings.anomaly_poll_seconds + 5)
    since = db.now()

    try:
        api.post_reading(canary_sensor_id, 125.0)
        wait_until(
            lambda: int(db.scalar(
                "SELECT count(*) FROM alerts "
                f"WHERE sensor_id = {canary_sensor_id} AND alert_type = 'OUT_OF_RANGE' "
                f"AND detected_at > '{since}'::timestamptz")) > 0,
            timeout=2 * settings.anomaly_poll_seconds + 15, interval=3,
            desc="OUT_OF_RANGE alert row")
    finally:
        api.post_reading(canary_sensor_id, 95.0)  