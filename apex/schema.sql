-- Oracle schema for the Low-Code Sensor Platform
-- Run in SQL Workshop > SQL Scripts of your APEX workspace.

CREATE TABLE sensor (
    sensor_code  VARCHAR2(10)  PRIMARY KEY,
    name         VARCHAR2(100) NOT NULL,
    unit         VARCHAR2(20)  NOT NULL,
    min_value    NUMBER        NOT NULL,
    max_value    NUMBER        NOT NULL
);

CREATE TABLE sensor_cycle (
    id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id    VARCHAR2(64)  NOT NULL,
    cycle_no     NUMBER(10)    NOT NULL,
    recorded_at  TIMESTAMP     NOT NULL,
    received_at  TIMESTAMP     DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT sensor_cycle_uk UNIQUE (device_id, cycle_no)
);

CREATE TABLE sensor_reading (
    cycle_id     NUMBER        NOT NULL REFERENCES sensor_cycle (id) ON DELETE CASCADE,
    sensor_code  VARCHAR2(10)  NOT NULL REFERENCES sensor (sensor_code),
    value        NUMBER        NOT NULL,
    CONSTRAINT sensor_reading_pk PRIMARY KEY (cycle_id, sensor_code)
);

CREATE INDEX sensor_reading_sensor_ix ON sensor_reading (sensor_code);

-- Flat view used by APEX reports and charts
CREATE OR REPLACE VIEW sensor_reading_v AS
SELECT c.device_id,
       c.cycle_no,
       c.recorded_at,
       r.sensor_code,
       s.name AS sensor_name,
       s.unit,
       r.value
  FROM sensor_cycle   c
  JOIN sensor_reading r ON r.cycle_id = c.id
  JOIN sensor         s ON s.sensor_code = r.sensor_code;

-- The 17 sensors (same catalog as app/sensors.py)
INSERT INTO sensor VALUES ('PS1',  'Pressure 1',                   'bar',   0,   200);
INSERT INTO sensor VALUES ('PS2',  'Pressure 2',                   'bar',   0,   200);
INSERT INTO sensor VALUES ('PS3',  'Pressure 3',                   'bar',   0,   200);
INSERT INTO sensor VALUES ('PS4',  'Pressure 4',                   'bar',   0,   200);
INSERT INTO sensor VALUES ('PS5',  'Pressure 5',                   'bar',   0,   200);
INSERT INTO sensor VALUES ('PS6',  'Pressure 6',                   'bar',   0,   200);
INSERT INTO sensor VALUES ('EPS1', 'Motor power',                  'W',     0,  3500);
INSERT INTO sensor VALUES ('FS1',  'Volume flow 1',                'l/min', 0,    30);
INSERT INTO sensor VALUES ('FS2',  'Volume flow 2',                'l/min', 0,    30);
INSERT INTO sensor VALUES ('TS1',  'Temperature 1',                '°C',  -20,   100);
INSERT INTO sensor VALUES ('TS2',  'Temperature 2',                '°C',  -20,   100);
INSERT INTO sensor VALUES ('TS3',  'Temperature 3',                '°C',  -20,   100);
INSERT INTO sensor VALUES ('TS4',  'Temperature 4',                '°C',  -20,   100);
INSERT INTO sensor VALUES ('VS1',  'Vibration',                    'mm/s',  0,     5);
INSERT INTO sensor VALUES ('CE',   'Cooling efficiency (virtual)', '%',     0,   100);
INSERT INTO sensor VALUES ('CP',   'Cooling power (virtual)',      'kW',    0,    10);
INSERT INTO sensor VALUES ('SE',   'System efficiency (virtual)',  '%',     0,   100);
COMMIT;
