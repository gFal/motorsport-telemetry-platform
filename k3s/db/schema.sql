CREATE TABLE cars (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    car_number      INTEGER NOT NULL UNIQUE,
    driver_name     TEXT NOT NULL,
    team            TEXT NOT NULL
);

CREATE TABLE sensors (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    car_id          INTEGER NOT NULL
                    REFERENCES cars(id)
                    ON DELETE CASCADE,
    channel_name    TEXT NOT NULL,
    UNIQUE(car_id, channel_name)
);

CREATE TABLE telemetry (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor_id       INTEGER NOT NULL
                    REFERENCES sensors(id)
                    ON DELETE CASCADE,
    value           DOUBLE PRECISION NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE alerts (
    id              BIGSERIAL PRIMARY KEY,
    sensor_id       INTEGER REFERENCES sensors(id),
    car_id          INTEGER,
    channel_name    TEXT NOT NULL,
    alert_type      TEXT NOT NULL CHECK (alert_type IN ('SILENT', 'OUT_OF_RANGE')),
    message         TEXT NOT NULL,
    value           DOUBLE PRECISION,   -- NULL for SILENT alerts
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sensor_car
ON sensors(car_id);

CREATE INDEX idx_telemetry_sensor_time
ON telemetry(sensor_id, recorded_at DESC);

CREATE INDEX idx_telemetry_time
ON telemetry(recorded_at DESC);

-- De-duplication and query index
CREATE INDEX idx_alerts_sensor_type_time
    ON alerts (sensor_id, alert_type, detected_at DESC);
