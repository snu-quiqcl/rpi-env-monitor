import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from models import Measurement


# Load environment variables from .env file
load_dotenv()

# Device and MQTT configuration
DEVICE_NAME = os.getenv("DEVICE_NAME", "rpi_env_unknown")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_BASE = os.getenv("MQTT_TOPIC_BASE", "lab/env")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "10.0"))


def build_payload(meas: Measurement, ts: datetime) -> Dict[str, Any]:
    """
    Build a JSON-serializable payload from a Measurement.

    Args:
        meas: Measurement object containing sensor_name, sensor_type, and value.
        ts: Timestamp of the measurement (timezone-aware UTC datetime).

    Returns:
        Dict that can be serialized to JSON and published via MQTT.
    """
    return {
        "device_name": DEVICE_NAME,
        "sensor_name": meas.sensor_name,
        "sensor_type": meas.sensor_type,
        "value": float(meas.value),
        "ts": ts.isoformat(),
    }


def on_connect(client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
    """
    MQTT on_connect callback for the publisher.

    For a simple publisher, we only log the connection result.
    """
    if rc == 0:
        print(f"[MQTT] Connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    else:
        print(f"[MQTT] Connection failed with code {rc}")


def run_publisher(read_all_sensors: Callable[[], List[Measurement]]) -> None:
    """
    Run the generic MQTT publisher loop.

    Args:
        read_all_sensors:
            A callable that returns a list of Measurement objects for the current time.
            This is where device-specific sensor reading logic lives.
    """
    print("[INIT] Starting MQTT publisher core...")
    print(f"[INIT] Device name: {DEVICE_NAME}")
    print(f"[INIT] MQTT broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print(f"[INIT] Publish interval: {PUBLISH_INTERVAL} s")

    client = mqtt.Client(client_id=f"{DEVICE_NAME}_publisher")
    client.on_connect = on_connect

    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    client.loop_start()

    topic_prefix = f"{MQTT_TOPIC_BASE}/{DEVICE_NAME}"

    try:
        while True:
            ts = datetime.now(timezone.utc)
            measurements = read_all_sensors()

            if not measurements:
                print("[WARN] No measurements returned by read_all_sensors().")
            else:
                for meas in measurements:
                    payload = build_payload(meas, ts)
                    payload_str = json.dumps(payload)

                    topic = f"{topic_prefix}/{meas.sensor_name}"
                    print(f"[PUB] Topic: {topic!r}")
                    print(f"[PUB] Payload: {payload_str}")

                    client.publish(topic, payload_str, qos=0, retain=False)

            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("\n[EXIT] Stopping publisher...")
    finally:
        client.loop_stop()
        client.disconnect()
