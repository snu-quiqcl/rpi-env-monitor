-- devices table: stores information about each Raspberry Pi device
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,                  -- unique internal ID
    device_name TEXT UNIQUE NOT NULL,       -- device name, e.g., 'rpi_3'
    description TEXT,                       -- location or other info
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() -- registration time
);

-- sensors table: stores information about each sensor connected to a device
CREATE TABLE IF NOT EXISTS sensors (
    id SERIAL PRIMARY KEY,                  -- unique sensor ID
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE, -- linked device
    sensor_name TEXT NOT NULL,              -- sensor name, e.g., 'DHT22-1'
    sensor_type TEXT,                       -- sensor type, e.g., temperature, humidity
    unit TEXT,                              -- measurement unit, e.g., °C, %, cm
    description TEXT,                       -- sensor model or extra info
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), -- registration time
    UNIQUE(device_id, sensor_name)          -- prevent duplicate sensor names per device
);

-- sensor_data table: stores actual measurements from sensors
CREATE TABLE IF NOT EXISTS sensor_data (
    id BIGSERIAL PRIMARY KEY,               -- unique data ID
    device_name TEXT NOT NULL,              -- device that sent the data
    sensor_name TEXT NOT NULL,              -- sensor that sent the data
    sensor_type TEXT,                       -- type of sensor
    value DOUBLE PRECISION,                 -- measured value
    ts TIMESTAMP WITH TIME ZONE NOT NULL,   -- measurement timestamp
    raw_payload JSONB,                      -- store full MQTT payload (optional)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() -- DB insert time
);

-- indexes to speed up time-series queries
CREATE INDEX IF NOT EXISTS idx_sensor_data_ts ON sensor_data (ts);
CREATE INDEX IF NOT EXISTS idx_sensor_data_device_sensor ON sensor_data (device_name, sensor_name);
