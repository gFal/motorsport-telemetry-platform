""" Unit tests for the telemetry payload model. """
import math
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models import TelemetryPacket


def make_payload(**overrides):
    payload = {"sensor_id": 1, "value": 95.0, "recorded_at": datetime.now(timezone.utc)}
    payload.update(overrides)
    return payload


def test_valid_reading_is_accepted():
    packet = TelemetryPacket(**make_payload())
    assert packet.sensor_id == 1
    assert packet.value == 95.0


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_values_are_rejected(value):
    with pytest.raises(ValidationError):
        TelemetryPacket(**make_payload(value=value))


@pytest.mark.parametrize("field", ["sensor_id", "value"])  # ADAPT: add "recorded_at" if it has no default
def test_missing_required_field_is_rejected(field):
    payload = make_payload()
    del payload[field]
    with pytest.raises(ValidationError):
        TelemetryPacket(**payload)


def test_non_numeric_value_is_rejected():
    with pytest.raises(ValidationError):
        TelemetryPacket(**make_payload(value="hot"))