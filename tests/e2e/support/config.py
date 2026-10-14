"""Runtime settings for the end-to-end test suites.

Values are read from environment variables, with defaults matching the standard deployment. Override them locally or in the CI workflow as needed.
"""
import os
from dataclasses import dataclass, field


def _env(name: str, default: str):
    return field(default_factory=lambda: os.getenv(name, default))


def _env_int(name: str, default: int):
    return field(default_factory=lambda: int(os.getenv(name, str(default))))


@dataclass(frozen=True)
class Settings:
    namespace: str = _env("K8S_NAMESPACE", "default")
    api_deployment: str = _env("API_DEPLOYMENT", "motorsport-api")
    api_service: str = _env("API_SERVICE", "motorsport-api")
    anomaly_deployment: str = _env("ANOMALY_DEPLOYMENT", "motorsport-anomaly")
    postgres_deployment: str = _env("POSTGRES_DEPLOYMENT", "postgres")
    postgres_secret: str = _env("POSTGRES_SECRET", "postgres-secret")
    postgres_secret_key: str = _env("POSTGRES_SECRET_KEY", "DB_PASSWORD")
    db_name: str = _env("DB_NAME", "motorsport")
    db_user: str = _env("DB_USER", "pitwall")
    db_probe_path: str = _env("DB_PROBE_PATH", "/cars/1/latest")
    canary_car_id: int = _env_int("CANARY_CAR_ID", 1)
    anomaly_poll_seconds: int = _env_int("ANOMALY_POLL_SECONDS", 30)
    api_url: str = _env("API_URL", "")  