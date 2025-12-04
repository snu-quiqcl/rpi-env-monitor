# Server

The `server` component runs on a central machine (often a Raspberry Pi) and is responsible for:

- Subscribing to MQTT topics for all sensors.
- Writing incoming measurements into a PostgreSQL database.
- Providing data to Grafana dashboards and alerts.

Client Raspberry Pis publish sensor data over MQTT; the server ingests and stores it.

---

## Directory layout

```text
server/
├─ .env.example                     # Template for server environment variables
├─ requirements.txt                 # Python dependencies
├─ sql/
│  └─ schema.sql                    # Database schema (devices, sensors, sensor_data)
├─ src/
│  ├─ db.py                         # PostgreSQL connection & insert helpers
│  └─ mqtt_subscriber.py            # MQTT subscriber that writes to the DB
└─ systemd/
   └─ rpi-env-subscriber.service.example  # Example systemd unit
```

---

## Prerequisites

### System packages (Debian/Raspberry Pi OS)

Install PostgreSQL, Mosquitto (MQTT broker), and basic build dependencies:

```bash
sudo apt update
sudo apt install -y \
    postgresql postgresql-contrib \
    mosquitto mosquitto-clients \
    build-essential libpq-dev
```

### Python

Any recent Python 3 is fine. Using **pyenv** (or pyenv + pyenv-virtualenv) is recommended:

```bash
# Inside the server directory:
cd /path/to/rpi-env-monitor/server

# (Optional) create a dedicated virtualenv via pyenv
pyenv virtualenv <python_version> rpi-env-monitor-server
pyenv local rpi-env-monitor-server
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Database setup

This project uses PostgreSQL to store all sensor data.  
Below is a minimal example of how to set up the database on a Debian/Raspberry Pi OS system.

### 1. Make sure PostgreSQL is running

After installing PostgreSQL (for example via `sudo apt install postgresql postgresql-contrib`):

```bash
# Enable PostgreSQL at boot and start it now
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Check status
sudo systemctl status postgresql
```

You should see `active (running)`.

### 2. Create a user and database

Connect to PostgreSQL as the default `postgres` superuser:

```bash
sudo -u postgres psql
```

In the psql shell, create a user and a database.
Use any names you like; here we use `env_db` and `pi` as an example:

```sql
-- Create an application user (choose a strong password)
CREATE USER pi WITH PASSWORD 'change_me';

-- Create the database
CREATE DATABASE env_db OWNER pi;

-- (Optional) make sure the user has full privileges on this database
GRANT ALL PRIVILEGES ON DATABASE env_db TO pi;

\q
```

Remember these values; you will put them into `.env` as:

* `DB_NAME=env_db`
* `DB_USER=pi`
* `DB_PASSWORD=change_me`

### 3. Create tables using `schema.sql`

From the `server/` directory, apply the schema to the database you just created:

```bash
cd /path/to/rpi-env-monitor/server

# Replace values in angle brackets with your actual settings
psql -h localhost -U pi -d env_db -f sql/schema.sql
```

If authentication is required, psql will prompt for the password you set in step 2.

The `schema.sql` file will create (if not already present):

* `devices` — list of Raspberry Pi devices
* `sensors` — list of sensors attached to each device
* `sensor_data` — time-series table for all measurements
* indexes on `sensor_data.ts` and `(device_name, sensor_name)` for faster queries

---

## Environment configuration

Copy the example environment file and edit it:

```bash
cd /path/to/rpi-env-monitor/server
cp .env.example .env
```

In `.env` you typically configure:

* **Database**

  * `DB_HOST`, `DB_PORT`
  * `DB_NAME`, `DB_USER`, `DB_PASSWORD`
* **MQTT**

  * `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`
  * `MQTT_TOPIC` (e.g. `lab/env/`)
  * `MQTT_CLIENT_ID` (optional, unique client name for the subscriber)

Make sure these values match your PostgreSQL and MQTT broker settings.

---

## Running the subscriber (manual)

To test the subscriber without systemd:

```bash
cd /path/to/rpi-env-monitor/server/src

# Activate your Python environment if needed:
# pyenv local rpi-env-monitor-server
# or: source ../.venv/bin/activate

python mqtt_subscriber.py
```

If everything is configured correctly, you should see log output such as:

* successful connection to the MQTT broker
* successful connection to the database
* inserted rows when clients publish sensor data

Use `Ctrl+C` to stop.

---

## Running as a systemd service

Once the subscriber works manually, you can run it as a system service.

1. Copy the example unit file:

   ```bash
   cd /path/to/rpi-env-monitor/server
   sudo cp systemd/rpi-env-subscriber.service.example \
       /etc/systemd/system/rpi-env-subscriber.service
   ```

2. Edit the unit file to match your paths and user:

   ```bash
   sudo nano /etc/systemd/system/rpi-env-subscriber.service
   ```

   Adjust at least:

   * `User` / `Group` – the account that owns the project (e.g. `pi`)

   * `WorkingDirectory` – the **src** directory of the server, for example:

     ```ini
     WorkingDirectory=/home/pi/Documents/rpi-env-monitor/server/src
     ```

   * `EnvironmentFile` – path to the `.env` file, for example:

     ```ini
     EnvironmentFile=/home/pi/Documents/rpi-env-monitor/server/.env
     ```

   If you use pyenv, the example unit shows how to set `PYENV_ROOT` and `PATH` so that `/usr/bin/env python` resolves to the correct interpreter.

3. Reload systemd and enable the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable rpi-env-subscriber.service
   sudo systemctl start rpi-env-subscriber.service
   ```

4. Check status:

   ```bash
   sudo systemctl status rpi-env-subscriber.service
   ```

   You should see `active (running)` if everything is OK.

---

## Logs

The example systemd unit routes both stdout and stderr to the system journal:

```ini
StandardOutput=journal
StandardError=journal
```

To view logs:

```bash
# Show recent logs
sudo journalctl -u rpi-env-subscriber.service -n 100

# Follow logs in real time
sudo journalctl -u rpi-env-subscriber.service -f
```

This is the primary place to look when debugging MQTT or database connection issues.

---

## Notes

* Keep the `.env` file out of version control (it contains credentials).
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
