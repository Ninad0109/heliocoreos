# HelioCore OS — Prerequisites & Setup Guide

## System Architecture

```
┌─────────────────────────┐        ┌─────────────────────────┐
│       MASTER-PI         │        │        FARM-PI          │
│                         │        │                         │
│  ┌─────────────────┐    │  HTTP  │  ┌─────────────────┐    │
│  │ Grafana :3000   │◄───┼────────┤  │ Sensors/Motors  │    │
│  └────────┬────────┘    │        │  └────────┬────────┘    │
│           │ query       │        │           │             │
│  ┌────────▼────────┐    │        │  ┌────────▼────────┐    │
│  │ Prometheus:9090 │    │  POST  │  │ Farm Node       │    │
│  └────────┬────────┘    │◄───────┤  │ (telemetry TX)  │    │
│           │ scrape      │        │  └─────────────────┘    │
│  ┌────────▼────────┐    │        │                         │
│  │ Telemetry :5000 │    │        │  ┌─────────────────┐    │
│  │ Node Reg  :5001 │    │        │  │ HelioCore OS    │    │
│  └─────────────────┘    │        │  │ CLI Terminal    │    │
│                         │        │  └─────────────────┘    │
│  Shows: Grafana         │        │  Shows: OS + Logs       │
│  Dashboard               │        │  Terminal                │
└─────────────────────────┘        └─────────────────────────┘
```

## Hardware Requirements

### Per Node
| Component | Master-Pi | Farm-Pi |
|-----------|-----------|---------|
| Raspberry Pi 3B+/4/5 | ✅ | ✅ |
| MicroSD card (16GB+) | ✅ | ✅ |
| USB-C 5V/3A power supply | ✅ | ✅ |
| Ethernet or WiFi | ✅ | ✅ |
| Monitor/display (optional) | Dashboard view | OS terminal |

### Farm-Pi Only
| Component | Qty | GPIO Pins |
|-----------|-----|-----------|
| LDR modules (LM393 comparator) | 6 | 17, 27, 22, 23, 24, 25 |
| Rain sensors (digital output) | 2 | 5, 6 |
| NEMA 23 stepper motors | 3 | — |
| DRV8825 stepper drivers | 3 | STEP/DIR: 12/16, 20/21, 13/19 |
| 12–24V power supply (motors) | 1 | — |

---

## Software Requirements

### Raspberry Pi OS
- **Version:** Raspberry Pi OS Lite (Bookworm) or Desktop
- **Download:** https://www.raspberrypi.com/software/
- Enable SSH and set hostname during flashing

### Python Packages
| Package | Master-Pi | Farm-Pi | Purpose |
|---------|-----------|---------|---------|
| flask 2.3.0 | ✅ | — | Telemetry server |
| werkzeug 2.3.0 | ✅ | — | Flask dependency |
| requests 2.31.0 | ✅ | ✅ | HTTP client |
| psutil 5.9.0 | ✅ | ✅ | CPU/memory metrics |
| prompt-toolkit 3.0.36 | — | ✅ | Interactive CLI shell |
| RPi.GPIO 0.7.1 | — | ✅ | GPIO hardware control |

### Services Installed
| Service | Master-Pi | Farm-Pi | Port |
|---------|-----------|---------|------|
| Grafana OSS | ✅ (via apt) | — | :3000 |
| Prometheus | ✅ (binary) | — | :9090 |
| Telemetry server | ✅ (systemd) | — | :5000 |
| Node registry | ✅ (systemd) | — | :5001 |
| Farm node | — | ✅ (systemd) | — |
| Node agent | — | ✅ (systemd) | — |

### Recommended Hostnames
| Node | Hostname | Suggested Static IP |
|------|----------|---------------------|
| Master | `master-pi` | `192.168.1.100` |
| Farm | `farm-pi` | `192.168.1.101` |

---

## Network Setup

### Option A: Static IP (Recommended)
Edit `/etc/dhcpcd.conf` on each Pi:
```
interface eth0
static ip_address=192.168.1.100/24    # .100 for Master, .101 for Farm
static routers=192.168.1.1
static domain_name_servers=8.8.8.8
```
Then `sudo systemctl restart dhcpcd`.

### Option B: mDNS (Zero-Config)
Both Pis auto-resolve via `hostname.local` (e.g., `master-pi.local`).
Update `farm-node/config.json` → `"master_ip": "master-pi.local"`.

---

## Wiring Guide

### Sensor Connections (GPIO)
Each sensor: **VCC → 5V**, **OUT → GPIO**, **GND → GND**

| Sensor | Function | GPIO Pin |
|--------|----------|----------|
| LDR 1 | Left-Bottom | 6 |
| LDR 2 | Left-Top | 26 |
| LDR 3 | Right-Top | 17 |
| LDR 4 | Right-Bottom | 5 |
| Rain | Rain Sensor | 15 |

### Motor Connections (DRV8825)
| Motor | Function | STEP Pin | DIR Pin |
|-------|----------|----------|---------|
| Base | Rotation (±160°) | 12 | 4 |
| Tilt | Elevation (0°–90°) | 13 | 19 |
| Petal | Open/Close | 27 | 18 |

---

## Installation (Plug & Play)

### Step 1: Clone on BOTH Pis
```bash
cd ~
git clone <your-repo-url> heliocoreos
cd heliocoreos
```

### Step 2: Setup Master-Pi
```bash
chmod +x install/master-pi.sh
sudo bash install/master-pi.sh
```
This installs Grafana, Prometheus, telemetry server, and node registry.
All services auto-start on boot.

### Step 3: Configure Farm-Pi
```bash
# Set the Master-Pi IP address
nano farm-node/config.json
# Change "master_ip" to your Master-Pi IP (e.g., "192.168.1.100")

# Run setup
chmod +x install/farm-pi.sh
sudo bash install/farm-pi.sh
```
This installs sensors, motors, and the HelioCore OS CLI shell.
On boot, the Farm-Pi auto-logs in and shows the HelioCore OS terminal.

### Step 4: Reboot & Verify
```bash
# On both Pis
sudo reboot
```

After reboot:
- **Master-Pi** → Open browser → http://master-pi:3000 → Grafana dashboard
- **Farm-Pi** → Monitor shows HelioCore OS terminal with live status

---

## Demo Mode (Without Hardware)

To test the full pipeline without Raspberry Pi hardware:

```bash
# Terminal 1: Start Master-Pi demo (downloads Grafana + Prometheus)
bash demo/demo-master-pi.sh

# Terminal 2: Start Farm-Pi simulator (interactive CLI)
bash demo/demo-farm-pi.sh [master-ip]
```

### Demo Features
| Feature | Master-Pi Terminal | Farm-Pi Terminal |
|---------|-------------------|-----------------|
| Output | Grafana dashboard at :3000 | HelioCore OS CLI shell |
| Metrics | 21 Prometheus metrics | Live logs + status |
| Commands | Tail logs | status, logs, metrics, health, top |
| Stop | `bash demo/demo-master-pi.sh stop` | Type `exit` |

### Metrics Exposed (21 total)
| Category | Metrics |
|----------|---------|
| Sensors | `ldr_left`, `ldr_right`, `ldr_top`, `ldr_bottom`, `rain_sensor` |
| Motors | `motor_state`, `motor_base_state`, `motor_tilt_state`, `motor_temperature` |
| Panel | `base_angle`, `tilt_angle`, `petal_state` |
| Tracking | `tracking_active`, `tracking_direction`, `alignment_error` |
| System | `cpu_usage`, `memory_usage`, `heliocore_service_health` |
| Node | `farm_online`, `farm_node_latency`, `light_intensity_avg` |

---

## Verification

```bash
# On Master-Pi — check services
systemctl status heliocore-telemetry
systemctl status heliocore-registry
systemctl status prometheus
systemctl status grafana-server

# On Farm-Pi — check services
systemctl status heliocore-farm
systemctl status heliocore-agent

# Test sensors
python3 farm-node/sensor_manager.py

# Test motors
sudo python3 farm-node/motor_controller.py
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: RPi.GPIO` | `sudo pip3 install RPi.GPIO` (Farm-Pi only) |
| Farm-Pi can't reach Master-Pi | Check `ping master-pi` and `config.json` IP |
| Motors don't move | Check 12–24V power and DRV8825 wiring |
| Sensors stuck at 0 | Verify VCC=5V on GPIO board |
| Grafana shows no data | `systemctl status heliocore-telemetry` + `systemctl status prometheus` |
| Permission denied on GPIO | Run with `sudo` or add user to `gpio` group |
| Dashboard panels empty | Run `python3 dashboards/import_dashboard.py` |
| Prometheus not scraping | Check `http://master-pi:9090/targets` |
