import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

from db import insert_sensor_data


# Load environment variables from .env file
load_dotenv()

# MQTT configuration
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "lab/env/#")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "rpi-env-subscriber")


def parse_timestamp(value: Any) -> datetime:
    """
    Parse various timestamp formats into a timezone-aware UTC datetime.

    Supported formats:
        - None: returns current UTC time
        - int/float: treated as Unix epoch seconds
        - str: ISO 8601, e.g. "2025-12-03T12:34:56Z" or "2025-12-03T12:34:56+00:00"
    """
    if value is None:
        return datetime.now(timezone.utc)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    if isinstance(value, str):
        s = value.strip()
        # Replace trailing 'Z' with '+00:00' for fromisoformat compatibility
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            # If no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            print(f"[WARN] Failed to parse timestamp string: {value!r}, using current time.")

    # Fallback: current UTC
    return datetime.now(timezone.utc)


def on_connect(client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
    """
    MQTT on_connect callback.

    Subscribes to the configured topic when the connection is established.
    """
    if rc == 0:
        print(f"[MQTT] Connected successfully to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Subscribed to topic: {MQTT_TOPIC!r}")
    else:
        print(f"[MQTT] Connection failed with result code {rc}")


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    """
    MQTT on_message callback.

    Expects the payload to be a JSON object with at least:
        - device_name (str)
        - sensor_name (str)
        - value (number)

    Optional fields:
        - sensor_type (str)
        - ts (ISO 8601 string or epoch seconds)

    The full payload is stored into sensor_data.raw_payload as JSONB.
    """
    try:
        payload_str = msg.payload.decode("utf-8")
    except UnicodeDecodeError:
        print(f"[MQTT] Failed to decode payload on topic {msg.topic!r}")
        return

    print(f"[MQTT] Message received on {msg.topic!r}: {payload_str}")

    try:
        data = json.loads(payload_str)
        if not isinstance(data, dict):
            raise ValueError("Payload JSON must be an object")
    except Exception as e:
        print(f"[MQTT] Failed to parse JSON payload: {e}")
        return

    # Extract required fields
    device_name = data.get("device_name")
    sensor_name = data.get("sensor_name")
    value = data.get("value")

    if device_name is None or sensor_name is None or value is None:
        print("[MQTT] Missing required fields (device_name, sensor_name, value). Skipping.")
        return

    # Optional fields
    sensor_type: Optional[str] = data.get("sensor_type")
    ts_raw: Any = data.get("ts")
    ts = parse_timestamp(ts_raw)

    # Insert into the database, storing the full payload as raw_payload
    insert_sensor_data(
        device_name=device_name,
        sensor_name=sensor_name,
        value=float(value),
        ts=ts,
        sensor_type=sensor_type,
        raw_payload=data,
    )

    print(
        f"[DB] Inserted data: device={device_name!r}, sensor={sensor_name!r}, "
        f"value={value}, ts={ts.isoformat()}"
    )


def main() -> None:
    """Main entrypoint for the MQTT subscriber."""
    print("[INIT] Starting MQTT subscriber...")
    print(f"[INIT] MQTT broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print(f"[INIT] MQTT topic:  {MQTT_TOPIC!r}")

    client = mqtt.Client(client_id=MQTT_CLIENT_ID)

    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect and block forever in the network loop
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
