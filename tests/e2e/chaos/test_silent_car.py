"""Chaos test: a car stops transmitting telemetry.

Verifies that a SILENT alert is raised within the configured threshold. Skipped until the telemetry simulator exposes a remote stop and start interface.
"""
import pytest


@pytest.mark.needs_simulator
@pytest.mark.skip(reason="simulator control hook not implemented yet")
def test_silent_car_raises_silent_alert_within_60s():
    ...