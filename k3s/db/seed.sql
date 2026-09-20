-- Cars
INSERT INTO cars (car_number, driver_name, team) VALUES
  (16, 'Charles Leclerc', 'Ferrari'),
  (44, 'Lewis Hamilton', 'Ferrari');

-- Sensors for car 1
INSERT INTO sensors (car_id, channel_name) VALUES
  (1, 'engine_temp'),
  (1, 'fuel_load'),
  (1, 'tyre_pressure_fl'),
  (1, 'tyre_pressure_fr'),
  (1, 'tyre_pressure_rl'),
  (1, 'tyre_pressure_rr'),
  (1, 'brake_temp_fl'),
  (1, 'brake_temp_fr'),
  (1, 'brake_temp_rl'),
  (1, 'brake_temp_rr');

-- Sensors for car 2
INSERT INTO sensors (car_id, channel_name) VALUES
  (2, 'engine_temp'),
  (2, 'fuel_load'),
  (2, 'tyre_pressure_fl'),
  (2, 'tyre_pressure_fr'),
  (2, 'tyre_pressure_rl'),
  (2, 'tyre_pressure_rr'),
  (2, 'brake_temp_fl'),
  (2, 'brake_temp_fr'),
  (2, 'brake_temp_rl'),
  (2, 'brake_temp_rr');
