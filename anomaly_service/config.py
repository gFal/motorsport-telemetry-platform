"""
All configuration via environment variables with local-dev defaults.
When this moves to Kubernetes, only the env vars in the Deployment manifest change — no code changes needed.
"""

import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "motorsport")
DB_USER = os.environ.get("DB_USER", "pitwall")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "pitwall")

DB_POOL_MIN_SIZE = int(os.environ.get("DB_POOL_MIN_SIZE", "1"))
DB_POOL_MAX_SIZE = int(os.environ.get("DB_POOL_MAX_SIZE", "5"))

# Polling
POLL_INTERVAL_SECONDS = float(
    os.environ.get("POLL_INTERVAL_SECONDS", "30")
)

# Alert thresholds 
SILENT_THRESHOLD_SECONDS = float(
    os.environ.get("SILENT_THRESHOLD_SECONDS", "60")
)
ENGINE_TEMP_MAX_C = float(
    os.environ.get("ENGINE_TEMP_MAX_C", "120.0")
)
TYRE_PRESSURE_MIN_PSI = float(
    os.environ.get("TYRE_PRESSURE_MIN_PSI", "19.0")
)
FUEL_LOAD_MIN_LITERS = float(
    os.environ.get("FUEL_LOAD_MIN_LITERS", "0.0")
)

# Log file path
ALERTS_LOG_PATH = os.environ.get("ALERTS_LOG_PATH", "alerts.log")