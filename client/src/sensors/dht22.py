import time
from dataclasses import dataclass
from typing import List, Optional

import adafruit_dht
import board

from models import Measurement


@dataclass
class DHT22Config:
    """
    Configuration for a single DHT22 sensor.

    Fields:
        pin_number: BCM pin number (e.g., 17 for GPIO17).
        name_prefix: Base name for this sensor (e.g., 'dht22' or 'lab_dht1').
        samples: Number of single measurements to average.
        sample_delay: Delay in seconds between single measurements.
    """
    pin_number: int
    name_prefix: str = "dht22"
    samples: int = 5
    sample_delay: float = 2.0


class DHT22Sensor:
    """
    DHT22 sensor wrapper that returns averaged temperature and humidity as Measurements.

    The measurement strategy is similar to your previous implementation:
    - Perform multiple single measurements.
    - Average the successful readings.
    """

    def __init__(self, config: DHT22Config) -> None:
        """
        Initialize the DHT22 sensor.

        Args:
            config: DHT22Config object with pin_number, name_prefix,
                    samples, and sample_delay.
        """
        try:
            # board.D17, board.D27, ... based on the pin_number
            self.pin = getattr(board, f"D{config.pin_number}")
        except AttributeError as exc:
            raise ValueError(f"Invalid pin number for DHT22: {config.pin_number}") from exc

        self.name_prefix = config.name_prefix
        self.samples = max(1, config.samples)
        self.sample_delay = config.sample_delay

    def _measure_single(self) -> Optional[tuple[float, float]]:
        """
        Perform a single DHT22 measurement.

        Returns:
            (temperature, humidity) if successful, otherwise None.
        """
        device = None
        try:
            device = adafruit_dht.DHT22(self.pin)
            temperature = device.temperature
            humidity = device.humidity
            if temperature is None or humidity is None:
                return None
            return float(temperature), float(humidity)
        except Exception as e:
            print(f"[DHT22] Single measurement failed on pin {self.pin}: {e}")
            return None
        finally:
            if device is not None:
                try:
                    device.exit()
                except Exception:
                    pass

    def read(self) -> List[Measurement]:
        """
        Read the DHT22 multiple times and return averaged Measurements.

        Returns:
            A list of two Measurement objects (temperature, humidity),
            or an empty list if all attempts failed.
        """
        total_temp = 0.0
        total_hum = 0.0
        count = 0

        for _ in range(self.samples):
            result = self._measure_single()
            if result is None:
                time.sleep(self.sample_delay)
                continue

            temperature, humidity = result
            total_temp += temperature
            total_hum += humidity
            count += 1

            time.sleep(self.sample_delay)

        if count == 0:
            print("[DHT22] Failed to obtain any valid readings.")
            return []

        avg_temp = total_temp / count
        avg_hum = total_hum / count

        temp_name = f"{self.name_prefix}_temp"
        hum_name = f"{self.name_prefix}_hum"

        return [
            Measurement(sensor_name=temp_name, sensor_type="temperature", value=avg_temp),
            Measurement(sensor_name=hum_name, sensor_type="humidity", value=avg_hum),
        ]
