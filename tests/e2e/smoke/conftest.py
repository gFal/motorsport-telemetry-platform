import pytest


@pytest.fixture(scope="session")
def canary_sensor_id(db, settings) -> int:
    """The sensor the smoke tests write to: engine_temp of the canary car."""
    value = db.scalar(
        f"SELECT id FROM sensors WHERE car_id = {settings.canary_car_id} "
        "AND channel_name = 'engine_temp'")
    assert value, f"no engine_temp sensor for car {settings.canary_car_id}"
    return int(value)