"""
SILENT: no reading from a sensor in the last 60s.
OUT_OF_RANGE: engine temp > 120C, tyre pressure < 19 PSI, fuel load < 0L.
De-duplication: each alert fires once on transition INTO the bad state.
If the condition clears and re-triggers, that's a new alert.
"""

from datetime import datetime
import config


class AnomalyState:
    """Tracks which (sensor_id, alert_type) pairs are currently active."""

    def __init__(self) -> None:
        self._active: dict[tuple[int, str], bool] = {}

    def is_active(
        self,
        sensor_id: int,
        alert_type: str,
    ) -> bool:
        return self._active.get((sensor_id, alert_type), False)

    def mark_active(
        self,
        sensor_id: int,
        alert_type: str,
    ) -> None:
        self._active[(sensor_id, alert_type)] = True

    def mark_resolved(
        self,
        sensor_id: int,
        alert_type: str,
    ) -> None:
        self._active[(sensor_id, alert_type)] = False


def check_silent(row, now: datetime) -> str | None:
    if row["recorded_at"] is None:
        return (
            f"Sensor {row['channel_name']} (car {row['car_id']}) "
            "has never reported any data."
        )

    age_seconds = (now - row["recorded_at"]).total_seconds()

    if age_seconds > config.SILENT_THRESHOLD_SECONDS:
        return (
            f"Sensor {row['channel_name']} (car {row['car_id']}) has not "
            f"reported in {age_seconds:.0f}s "
            f"(threshold: {config.SILENT_THRESHOLD_SECONDS:.0f}s)."
        )

    return None


def check_out_of_range(row) -> str | None:
    if row["value"] is None:
        return None

    channel = row["channel_name"]
    value = row["value"]

    if channel == "engine_temp" and value > config.ENGINE_TEMP_MAX_C:
        return (
            f"Engine temp {value:.1f}C exceeds max "
            f"{config.ENGINE_TEMP_MAX_C:.1f}C "
            f"(car {row['car_id']})."
        )

    if (
        channel.startswith("tyre_pressure_")
        and value < config.TYRE_PRESSURE_MIN_PSI
    ):
        return (
            f"Tyre pressure {value:.2f} PSI below min "
            f"{config.TYRE_PRESSURE_MIN_PSI:.2f} PSI "
            f"on {channel} (car {row['car_id']})."
        )

    if channel == "fuel_load" and value < config.FUEL_LOAD_MIN_LITERS:
        return (
            f"Fuel load {value:.2f}L below min "
            f"{config.FUEL_LOAD_MIN_LITERS:.2f}L "
            f"(car {row['car_id']})."
        )

    return None


def evaluate_row(
    row,
    now: datetime,
    state: AnomalyState,
) -> list[dict]:
    """
    Runs both rules against one sensor's latest reading.
    Returns new alerts only (empty list if condition is ongoing or normal).
    """

    new_alerts = []

    silent_msg = check_silent(row, now)

    if silent_msg:
        if not state.is_active(row["sensor_id"], "SILENT"):
            state.mark_active(row["sensor_id"], "SILENT")

            new_alerts.append(
                {
                    "sensor_id": row["sensor_id"],
                    "car_id": row["car_id"],
                    "channel_name": row["channel_name"],
                    "alert_type": "SILENT",
                    "message": silent_msg,
                    "value": None,
                }
            )
    else:
        state.mark_resolved(row["sensor_id"], "SILENT")

    # If silent, skip OUT_OF_RANGE — there's no current value to evaluate
    if row["value"] is not None:
        oor_msg = check_out_of_range(row)

        if oor_msg:
            if not state.is_active(
                row["sensor_id"],
                "OUT_OF_RANGE",
            ):
                state.mark_active(
                    row["sensor_id"],
                    "OUT_OF_RANGE",
                )

                new_alerts.append(
                    {
                        "sensor_id": row["sensor_id"],
                        "car_id": row["car_id"],
                        "channel_name": row["channel_name"],
                        "alert_type": "OUT_OF_RANGE",
                        "message": oor_msg,
                        "value": row["value"],
                    }
                )
        else:
            state.mark_resolved(
                row["sensor_id"],
                "OUT_OF_RANGE",
            )

    return new_alerts