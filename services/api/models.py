import math
from datetime import datetime
from pydantic import BaseModel, field_validator


class TelemetryPacket(BaseModel):
    sensor_id: int
    value: float
    recorded_at: datetime

    @field_validator("value")
    @classmethod
    def value_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be a finite number")
        
        return value


class TelemetryResponse(BaseModel):
    id: int
    sensor_id: int
    value: float
    recorded_at: datetime


class LatestReading(BaseModel):
    channel_name: str
    value: float
    recorded_at: datetime