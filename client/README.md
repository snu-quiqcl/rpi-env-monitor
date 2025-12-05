# Client

The `client` component runs on each sensor Raspberry Pi and is responsible for:

- Reading values from locally attached sensors (e.g., DHT22, water presence).
- Converting readings into a common JSON format.
- Publishing measurements periodically to a central MQTT broker.

Each Raspberry Pi has its own `.env` and `sensors.json` so you can configure sensors and identity per device.

---

## Directory layout

```text
client/
├─ .env.example                     # Template for client environment variables
├─ sensors.example.json             # Example sensor configuration for this Pi
├─ requirements.txt                 # Python dependencies
├─ src/
│  ├─ models.py                     # Shared dataclasses (Measurement, etc.)
│  ├─ sensors/
│  │  ├─ dht22_sensor.py               # DHT22 sensor driver
│  │  └─ water_presence_sensor.py      # Digital water presence sensor driver
│  ├─ publisher_core.py             # Generic MQTT publishing loop
│  └─ mqtt_publisher.py             # Entry point for this Raspberry Pi
└─ systemd/
   └─ rpi-env-publisher.service.example  # Example systemd unit for the client
```

---

## Prerequisites

### System packages (Raspberry Pi OS / Debian)

Install Python and basic GPIO dependencies:

```bash
sudo apt update
sudo apt install -y \
    python3 python3-venv python3-pip \
    libgpiod2
```

> `libgpiod2` is required by the Adafruit DHT22 library on newer Raspberry Pi OS images.

### Python

Any recent Python 3 is fine. Using **pyenv** (or pyenv + pyenv-virtualenv) is recommended:

```bash
cd /path/to/rpi-env-monitor/client

# Optional: create and select a dedicated virtualenv via pyenv
pyenv virtualenv <python_version> rpi-env-monitor-client
pyenv local rpi-env-monitor-client
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment configuration (`.env`)

Each client Raspberry Pi has its own `.env` file that controls how it connects to the MQTT broker and how it identifies itself.

Copy the example and edit it:

```bash
cd /path/to/rpi-env-monitor/client
cp .env.example .env
```

Typical variables:

* `DEVICE_NAME` – unique name for this Raspberry Pi (e.g., `rpi_blade_1`)
* `MQTT_BROKER_HOST` – hostname or IP of the MQTT broker (e.g., `192.168.0.10`)
* `MQTT_BROKER_PORT` – broker port (default `1883`)
* `MQTT_TOPIC_BASE` – base topic (e.g., `lab/env`)
* `PUBLISH_INTERVAL` – publish interval in seconds (e.g., `60`)

The `.env` file is loaded by `publisher_core.py` at startup.

---

## Sensor configuration (`sensors.json`)

Sensors attached to each Raspberry Pi are described by `sensors.json` in the `client/` directory.
Use `sensors.example.json` as a starting point:

```bash
cd /path/to/rpi-env-monitor/client
cp sensors.example.json sensors.json
```

Example:

```json
{
  "sensors": [
    {
      "type": "dht22",
      "pin": 17,
      "name_prefix": "env1",
      "samples": 5,
      "sample_delay": 2.0
    },
    {
      "type": "water_presence",
      "pin": 27,
      "name_prefix": "env2",
      "samples": 5,
      "sample_delay": 0.05
    }
  ]
}
```

Each entry has:

* `type`

  * `"dht22"` – temperature/humidity sensor
  * `"water_presence"` – digital water presence sensor
* `pin` – BCM GPIO number (e.g., `17` → GPIO17)
* `name_prefix` – base name for this sensor (e.g., `env1`, `env2`); this becomes part of `sensor_name`
* `samples` – number of readings to take and average
* `sample_delay` – delay in seconds between samples

The publisher will read all configured sensors, produce `Measurement` objects, and publish JSON payloads that include:

* `device_name`
* `sensor_name`
* `sensor_type`
* `value`
* `ts` (UTC timestamp)

---

## Running the publisher (manual)

To test the publisher without systemd:

```bash
cd /path/to/rpi-env-monitor/client/src

# Activate your Python environment if needed:
# pyenv local rpi-env-monitor-client
# or: source ../.venv/bin/activate

python mqtt_publisher.py
```

By default, `mqtt_publisher.py` will:

* Load environment variables from `../.env`
* Load sensor definitions from `../sensors.json`
* Connect to the MQTT broker
* Enter a loop that:

  * reads all sensors
  * publishes one MQTT message per measurement
  * sleeps for `PUBLISH_INTERVAL`

If everything is configured correctly, you should see logs like:

* Sensor readings (temperature, humidity, water presence)
* Successful MQTT connection / publish messages

Use `Ctrl+C` to stop.

---

## Running as a systemd service

Once the publisher works manually, you can run it as a system service so that it starts on boot.

1. Copy the example unit file:

   ```bash
   cd /path/to/rpi-env-monitor/client
   sudo cp systemd/rpi-env-publisher.service.example \
       /etc/systemd/system/rpi-env-publisher.service
   ```

2. Edit the unit file to match your paths and user:

   ```bash
   sudo nano /etc/systemd/system/rpi-env-publisher.service
   ```

   Adjust at least:

   * `User` / `Group` – the account that owns the project (e.g., `pi`)

   * `WorkingDirectory` – the **src** directory of the client, for example:

     ```ini
     WorkingDirectory=/home/pi/Documents/rpi-env-monitor/client/src
     ```

   * `EnvironmentFile` – path to the `.env` file, for example:

     ```ini
     EnvironmentFile=/home/pi/Documents/rpi-env-monitor/client/.env
     ```

   If you use pyenv, the example unit shows how to set `PYENV_ROOT` and `PATH` so that `/usr/bin/env python` resolves to the correct interpreter.

3. Reload systemd and enable the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable rpi-env-publisher.service
   sudo systemctl start rpi-env-publisher.service
   ```

4. Check status:

   ```bash
   sudo systemctl status rpi-env-publisher.service
   ```

   You should see `active (running)` if everything is OK.

---

## Logs

The example systemd unit routes stdout and stderr to the system journal:

```ini
StandardOutput=journal
StandardError=journal
```

To view logs:

```bash
# Show recent logs
sudo journalctl -u rpi-env-publisher.service -n 100

# Follow logs in real time
sudo journalctl -u rpi-env-publisher.service -f
```

This is the primary place to look when debugging sensor or MQTT issues on each client Raspberry Pi.

---

## Notes

* Keep `.env` and `sensors.json` out of version control (they are device-specific and may contain credentials).
* If you change the systemd unit file, always run:

  ```bash
  sudo systemctl daemon-reload
  ```

  before restarting the service.
* When upgrading dependencies, re-run:

  ```bash
  pip install -r requirements.txt
  ```

  in the same Python environment.
