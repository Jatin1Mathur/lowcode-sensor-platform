"""Catalog of the 17 sensors handled by the platform.

The sensor set follows a hydraulic test rig (pressure, power, flow,
temperature, vibration and virtual efficiency sensors). Each entry
defines the unit and the physically plausible value range used for
validation before data is forwarded to Oracle APEX.
"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Sensor:
    code: str
    name: str
    unit: str
    min_value: float
    max_value: float

    def to_dict(self) -> dict:
        return asdict(self)


SENSORS: dict[str, Sensor] = {
    s.code: s
    for s in [
        Sensor("PS1", "Pressure 1", "bar", 0, 200),
        Sensor("PS2", "Pressure 2", "bar", 0, 200),
        Sensor("PS3", "Pressure 3", "bar", 0, 200),
        Sensor("PS4", "Pressure 4", "bar", 0, 200),
        Sensor("PS5", "Pressure 5", "bar", 0, 200),
        Sensor("PS6", "Pressure 6", "bar", 0, 200),
        Sensor("EPS1", "Motor power", "W", 0, 3500),
        Sensor("FS1", "Volume flow 1", "l/min", 0, 30),
        Sensor("FS2", "Volume flow 2", "l/min", 0, 30),
        Sensor("TS1", "Temperature 1", "°C", -20, 100),
        Sensor("TS2", "Temperature 2", "°C", -20, 100),
        Sensor("TS3", "Temperature 3", "°C", -20, 100),
        Sensor("TS4", "Temperature 4", "°C", -20, 100),
        Sensor("VS1", "Vibration", "mm/s", 0, 5),
        Sensor("CE", "Cooling efficiency (virtual)", "%", 0, 100),
        Sensor("CP", "Cooling power (virtual)", "kW", 0, 10),
        Sensor("SE", "System efficiency (virtual)", "%", 0, 100),
    ]
}
