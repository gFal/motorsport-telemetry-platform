""" Unit tests for the HTTP contract of POST /telemetry. """
import pytest
from fastapi.testclient import TestClient

from application import app

client = TestClient(app)

VALID = {"sensor_id": 1, "value": 95.0, "recorded_at": "2026-10-11T12:00:00Z"}


@pytest.mark.parametrize(
    "payload",
    [
        {k: v for k, v in VALID.items() if k != "value"},    
        {**VALID, "value": "hot"},                           
        {**VALID, "sensor_id": "abc"},                       
        {**VALID, "recorded_at": "not-a-date"},              
    ],
    ids=["missing-value", "value-not-numeric", "sensor-id-not-int", "bad-timestamp"],
)
def test_invalid_payload_is_rejected_with_422(payload):
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 422