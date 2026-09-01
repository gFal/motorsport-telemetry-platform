"""
Structured JSON-lines logging. One JSON object per line, one line per alert.
JSON-lines is directly machine-parseable and compatible with log aggregators when this moves to Kubernetes.
"""

import json
from datetime import datetime
import config


def log_alert(
    alert: dict,
    detected_at: datetime,
) -> None:
    record = {
        "detected_at": detected_at.isoformat(),
        "alert_type": alert["alert_type"],
        "car_id": alert["car_id"],
        "sensor_id": alert["sensor_id"],
        "channel_name": alert["channel_name"],
        "value": alert["value"],
        "message": alert["message"],
    }

    with open(config.ALERTS_LOG_PATH, "a") as file:
        file.write(json.dumps(record) + "\n")