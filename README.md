# Lab Environment Monitor

This repository collects and visualizes lab environmental data (temperature, humidity, water presence, etc.) using multiple Raspberry Pis, MQTT, PostgreSQL, and Grafana.

- Sensor Raspberry Pis run the **client** code and publish measurements over MQTT.
- A central machine runs the **server** code, subscribes to MQTT topics, writes data into PostgreSQL, and exposes it to Grafana dashboards and alerts.

Detailed setup and usage instructions are provided in `client/README.md` and `server/README.md`.

---

## Repository layout

```text
.
├─ client/    # MQTT publishers running on sensor Raspberry Pis
├─ server/    # MQTT subscriber + PostgreSQL integration + systemd units
└─ README.md  # Project overview (this file)
```
