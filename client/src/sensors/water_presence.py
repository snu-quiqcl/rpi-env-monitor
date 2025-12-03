from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List

import RPi.GPIO as GPIO

from models import Measurement


# Internal flag to ensure GPIO mode is configured only once
_GPIO_INITIALIZED = False


def _ensure_gpio_initialized() -> None:
    """
    Ensure that GPIO is initialized in BCM mode exactly once.
    """
    global _GPIO_INITIALIZED
    if not _GPIO_INITIALIZED:
        GPIO.setmode(GPIO.BCM)
        _GPIO_INITIALIZED = True


@dataclass
class WaterPresenceConfig:
    """
    Configuration for a digital water presence sensor.

    Fields:
        pin: BCM GPIO pin number used as digital input.
        name_prefix: Base name for the sensor_name.
        samples: Number of digital samples to take per measurement.
        sample_delay: Delay in seconds between samples.
    """
    pin: int
    name_prefix: str = "water"
    samples: int = 5
    sample_delay: float = 0.05


class WaterPresenceSensor:
    """
    Digital water presence sensor using a GPIO input.

    This class assumes:
      - The sensor is powered from 3.3 V.
      - The sensor output is connected to a BCM GPIO pin.
      - The sensor output never exceeds 3.3 V at the GPIO pin.

    The sensor is treated as a simple digital input:
      - 0: "dry" / no water
      - 1: "wet" / water present

    To reduce glitches, the sensor is read 'samples' times and a majority
    vote is used to decide the final state.
    """

    def __init__(self, config: WaterPresenceConfig) -> None:
        """
        Initialize the water presence sensor.

        Args:
            config: WaterPresenceConfig object containing pin and timing params.
        """
        self.config = config

        _ensure_gpio_initialized()

        # Configure the pin as a digital input with an internal pull-down.
        # NOTE: If your sensor behaves inversely, you may switch to PUD_UP
        # and invert the logic in read().
        GPIO.setup(self.config.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def read(self) -> List[Measurement]:
        """
        Read the water presence state with simple majority voting.

        Returns:
            A list containing a single Measurement:
              - <name_prefix>_present: 0.0 or 1.0
                sensor_type='water_presence'

            If all GPIO reads fail, returns an empty list.
        """
        samples = max(1, self.config.samples)
        high_count = 0
        valid_reads = 0

        for _ in range(samples):
            try:
                value = GPIO.input(self.config.pin)
            except Exception as e:
                print(f"[WaterPresence] GPIO read failed on pin {self.config.pin}: {e}")
                time.sleep(self.config.sample_delay)
                continue

            valid_reads += 1
            if value:  # 1 = water present (assuming active-high)
                high_count += 1

            time.sleep(self.config.sample_delay)

        if valid_reads == 0:
            print(f"[WaterPresence] No valid GPIO reads on pin {self.config.pin}.")
            return []

        # Majority vote: if at least half of the valid samples were HIGH, treat as 1
        threshold = valid_reads / 2.0
        present = 1.0 if high_count >= threshold else 0.0

        sensor_name = f"{self.config.name_prefix}_water"

        return [
            Measurement(
                sensor_name=sensor_name,
                sensor_type="water_presence",
                value=present,
            )
        ]
