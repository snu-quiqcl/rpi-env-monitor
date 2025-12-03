from dataclasses import dataclass


@dataclass
class Measurement:
    """
    Container for a single sensor measurement.

    Fields:
        sensor_name: Logical sensor name (e.g., 'dht22_temp', 'water_level_1').
        sensor_type: Type/category of the measurement (e.g., 'temperature', 'humidity', 'water_level').
        value: Numeric value of the measurement.
    """
    sensor_name: str
    sensor_type: str
    value: float
