# client/src/mqtt_publisher.py

import json
import os
from pathlib import Path
from typing import Any, List

from dotenv import load_dotenv

from models import Measurement
from publisher_core import run_publisher
from sensors.dht22 import DHT22Config, DHT22Sensor
from sensors.water_presence import WaterPresenceConfig, WaterPresenceSensor


# Load environment variables (for DEVICE_NAME, MQTT, config path, etc.)
load_dotenv()

# Base directory of the client project (one level above src/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Default config path: <client>/sensors.json
_default_cfg = BASE_DIR / "sensors.json"

# Optional override from environment variable.
# If it is a relative path, treat it as relative to BASE_DIR.
cfg_env = os.getenv("SENSORS_CONFIG_PATH")
if cfg_env:
    cfg_path = Path(cfg_env)
    if not cfg_path.is_absolute():
        cfg_path = BASE_DIR / cfg_path
else:
    cfg_path = _default_cfg

SENSORS_CONFIG_PATH = cfg_path


def build_sensors_from_config() -> List[Any]:
    """
    Build a list of sensor objects based on the JSON configuration file.

    The config file should look like:

    {
      "sensors": [
        {"type": "dht22", "pin": 17, "name_prefix": "env1", "samples": 5, "sample_delay": 2.0},
        {"type": "water_presence", "pin": 27, "name_prefix": "water", "samples": 5, "sample_delay": 0.05},
      ]
    }
    """
    sensors: List[Any] = []

    try:
        with open(SENSORS_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print(f"[INIT] Sensor config file not found: {SENSORS_CONFIG_PATH!r}")
        return sensors
    except json.JSONDecodeError as e:
        print(f"[INIT] Failed to parse JSON config {SENSORS_CONFIG_PATH!r}: {e}")
        return sensors

    sensor_items = cfg.get("sensors", [])
    if not isinstance(sensor_items, list):
        print("[INIT] 'sensors' key in config must be a list.")
        return sensors

    for idx, s_cfg in enumerate(sensor_items):
        if not isinstance(s_cfg, dict):
            print(f"[INIT] Invalid sensor entry at index {idx}: not an object")
            continue

        s_type = s_cfg.get("type")
        pin = s_cfg.get("pin")
        name_prefix = s_cfg.get("name_prefix")

        if s_type is None or pin is None:
            print(f"[INIT] Missing 'type' or 'pin' in sensor entry at index {idx}. Skipping.")
            continue

        try:
            pin_int = int(pin)
        except ValueError:
            print(f"[INIT] Invalid pin value at index {idx}: {pin!r}. Skipping.")
            continue

        if s_type == "dht22":
            if not name_prefix:
                name_prefix = f"dht22_{idx + 1}"

            samples = s_cfg.get("samples")
            sample_delay = s_cfg.get("sample_delay")

            cfg_kwargs = {}
            if samples is not None:
                cfg_kwargs["samples"] = samples
            if sample_delay is not None:
                cfg_kwargs["sample_delay"] = sample_delay

            cfg_obj = DHT22Config(
                pin_number=pin_int,
                name_prefix=name_prefix,
                **cfg_kwargs
            )
            sensor = DHT22Sensor(config=cfg_obj)
            sensors.append(sensor)
            print(f"[INIT] Added DHT22 sensor on pin {pin_int} with prefix {name_prefix!r}")

        elif s_type == "water_presence":
            if not name_prefix:
                name_prefix = f"water_presence_{idx + 1}"

            samples = s_cfg.get("samples")
            sample_delay = s_cfg.get("sample_delay")

            cfg_kwargs = {}
            if samples is not None:
                cfg_kwargs["samples"] = samples
            if sample_delay is not None:
                cfg_kwargs["sample_delay"] = sample_delay

            cfg_obj = WaterPresenceConfig(
                pin=pin_int,
                name_prefix=name_prefix,
                **cfg_kwargs
            )
            sensor = WaterPresenceSensor(config=cfg_obj)
            sensors.append(sensor)
            print(f"[INIT] Added WaterPresence sensor on pin {pin_int} with prefix {name_prefix!r}")

        else:
            print(f"[INIT] Unknown sensor type {s_type!r} at index {idx}. Skipping.")

    if not sensors:
        print("[INIT] No valid sensors configured.")
    else:
        print(f"[INIT] Total sensors configured: {len(sensors)}")

    return sensors


# Build sensors once at startup
SENSORS = build_sensors_from_config()


def read_all_sensors() -> List[Measurement]:
    """
    Read all configured sensors and aggregate their measurements.

    Returns:
        A flat list of Measurement objects from all sensors.
    """
    measurements: List[Measurement] = []

    for sensor in SENSORS:
        try:
            # Each sensor has a .read() method returning List[Measurement]
            m_list = sensor.read()
            measurements.extend(m_list)
        except Exception as e:
            print(f"[SENSOR] Error while reading sensor {sensor}: {e}")

    return measurements


if __name__ == "__main__":
    run_publisher(read_all_sensors)
