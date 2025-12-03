import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import psycopg2
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "env_db")
DB_USER = os.getenv("DB_USER", "pi")
DB_PASSWORD = os.getenv("DB_PASSWORD", "change_me")


def get_connection():
    """
    Create and return a new PostgreSQL connection.
    Using a separate connection per operation is fine for low-traffic RPI usage.
    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def insert_sensor_data(
    device_name: str,
    sensor_name: str,
    value: float,
    ts: datetime,
    sensor_type: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None,
):
    query = """
        INSERT INTO sensor_data (device_name, sensor_name, sensor_type, value, ts, raw_payload)
        VALUES (%s, %s, %s, %s, %s, %s);
    """

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            query,
            (
                device_name,
                sensor_name,
                sensor_type,
                value,
                ts,
                json.dumps(raw_payload) if raw_payload is not None else None,
            ),
        )
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"[DB ERROR] Failed to insert sensor data: {e}")
    finally:
        if conn:
            conn.close()
