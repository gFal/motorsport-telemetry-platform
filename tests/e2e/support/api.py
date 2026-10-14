"""HTTP client for the telemetry API."""
from datetime import datetime, timezone

import requests


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def status(self, path: str) -> int:
        return self.session.get(f"{self.base_url}{path}", timeout=3).status_code

    def is_healthy(self) -> bool:
        return self.status("/health") == 200

    def post_reading(self, sensor_id: int, value: float) -> None:
        payload = {"sensor_id": sensor_id, "value": value,
                   "recorded_at": datetime.now(timezone.utc).isoformat()}
        response = self.session.post(f"{self.base_url}/telemetry", json=payload, timeout=5)
        assert response.status_code in (200, 201, 202), (
            f"POST /telemetry -> {response.status_code}: {response.text[:200]}")