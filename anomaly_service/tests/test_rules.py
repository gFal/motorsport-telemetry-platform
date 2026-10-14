""" Unit tests for anomaly_service/rules.py: thresholds, silence detection and alert de-duplication. """
from datetime import datetime, timedelta, timezone

import pytest

import config
from rules import AnomalyState, check_out_of_range, check_silent, evaluate_row

NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)


def make_row(channel="engine_temp", value=95.0, age_seconds=1.0, sensor_id=1, car_id=1):
    recorded_at = None if age_seconds is None else NOW - timedelta(seconds=age_seconds)
    return {
        "sensor_id": sensor_id,
        "car_id": car_id,
        "channel_name": channel,
        "value": value,
        "recorded_at": recorded_at,
    }


@pytest.mark.parametrize(
    "channel, value, expected_alert",
    [
        ("engine_temp", config.ENGINE_TEMP_MAX_C, False),
        ("engine_temp", config.ENGINE_TEMP_MAX_C + 0.1, True),
        ("tyre_pressure_fl", config.TYRE_PRESSURE_MIN_PSI, False),
        ("tyre_pressure_fl", config.TYRE_PRESSURE_MIN_PSI - 0.1, True),
        ("tyre_pressure_rr", config.TYRE_PRESSURE_MIN_PSI - 0.1, True),
        ("fuel_load", config.FUEL_LOAD_MIN_LITERS, False),
        ("fuel_load", config.FUEL_LOAD_MIN_LITERS - 0.1, True),
        ("speed", 10_000.0, False),
    ],
)
def test_out_of_range_thresholds(channel, value, expected_alert):
    result = check_out_of_range(make_row(channel=channel, value=value))
    assert (result is not None) is expected_alert


def test_out_of_range_ignores_missing_value():
    assert check_out_of_range(make_row(value=None)) is None


@pytest.mark.parametrize(
    "age_seconds, expected_alert",
    [
        (1.0, False),
        (config.SILENT_THRESHOLD_SECONDS, False),
        (config.SILENT_THRESHOLD_SECONDS + 1, True),
        (None, True),
    ],
    ids=["fresh", "at-threshold", "past-threshold", "never-reported"],
)
def test_silent_detection(age_seconds, expected_alert):
    result = check_silent(make_row(age_seconds=age_seconds), NOW)
    assert (result is not None) is expected_alert


def test_anomaly_state_tracks_each_sensor_and_alert_type_independently():
    state = AnomalyState()
    assert state.is_active(1, "OUT_OF_RANGE") is False

    state.mark_active(1, "OUT_OF_RANGE")
    assert state.is_active(1, "OUT_OF_RANGE") is True
    assert state.is_active(1, "SILENT") is False
    assert state.is_active(2, "OUT_OF_RANGE") is False

    state.mark_resolved(1, "OUT_OF_RANGE")
    assert state.is_active(1, "OUT_OF_RANGE") is False


def test_out_of_range_alert_fires_once_per_episode():
    state = AnomalyState()
    normal = make_row(value=95.0)
    hot = make_row(value=config.ENGINE_TEMP_MAX_C + 5)

    assert evaluate_row(normal, NOW, state) == []
    assert len(evaluate_row(hot, NOW, state)) == 1
    assert evaluate_row(hot, NOW, state) == []
    assert evaluate_row(normal, NOW, state) == []
    assert len(evaluate_row(hot, NOW, state)) == 1


def test_silent_alert_fires_once_per_episode():
    state = AnomalyState()
    fresh = make_row(age_seconds=1.0)
    stale = make_row(age_seconds=config.SILENT_THRESHOLD_SECONDS + 10)

    assert len(evaluate_row(stale, NOW, state)) == 1
    assert evaluate_row(stale, NOW, state) == []
    assert evaluate_row(fresh, NOW, state) == []
    assert len(evaluate_row(stale, NOW, state)) == 1


def test_out_of_range_alert_payload():
    row = make_row(sensor_id=7, car_id=3, value=config.ENGINE_TEMP_MAX_C + 5)

    [alert] = evaluate_row(row, NOW, AnomalyState())

    assert alert["alert_type"] == "OUT_OF_RANGE"
    assert alert["sensor_id"] == 7
    assert alert["car_id"] == 3
    assert alert["channel_name"] == "engine_temp"
    assert alert["value"] == row["value"]
    assert alert["message"]