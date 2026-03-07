# HelioCore OS — Prerequisites & Setup Guide

## Hardware Requirements

### Per Node
| Component | Master-Pi | Farm-Pi |
|-----------|-----------|---------|
| Raspberry Pi 3B+/4 | ✅ | ✅ |
| MicroSD card (16GB+) | ✅ | ✅ |
| USB-C 5V/3A power supply | ✅ | ✅ |
| Ethernet cable or WiFi | ✅ | ✅ |

### Farm-Pi Only
| Component | Qty | GPIO Pins |
|-----------|-----|-----------|
| LDR modules (LM393 comparator) | 6 | 17, 27, 22, 23, 24, 25 |
| Rain sensors (digital output) | 2 | 5, 6 |
| NEMA 23 stepper motors | 3 | — |
| DRV8825 stepper drivers | 3 | STEP/DIR: 12/16, 20/21, 13/19 |
| 12–24V power supply (motors) | 1 | — |
| GPIO training board | 1 | — |

---

## Software Requirements

### Raspberry Pi OS
- **Version:** Raspberry Pi OS Lite (Bookworm) or Desktop
- **Download:** https://www.raspberrypi.com/software/
- Flash with Raspberry Pi Imager, enable SSH and set hostname during flashing

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

### Sensor Connections (Farm-Pi GPIO Training Board)
Each sensor has 3 pins: **VCC → 5V**, **OUT → GPIO**, **GND → GND**

| Sensor | Function | GPIO Pin |
|--------|----------|----------|
| LDR 1 | Left-Top | 17 |
| LDR 2 | Top-Center | 27 |
| LDR 3 | Right-Top | 22 |
| LDR 4 | Left-Bottom | 23 |
| LDR 5 | Bottom-Center | 24 |
| LDR 6 | Right-Bottom | 25 |
| Rain 1 | Primary | 5 |
| Rain 2 | Secondary | 6 |

### Motor Connections (DRV8825 Drivers)
| Motor | Function | STEP Pin | DIR Pin |
|-------|----------|----------|---------|
| Motor 1 | Petal open/close | 12 | 16 |
| Motor 2 | Tilt (0°–90°) | 20 | 21 |
| Motor 3 | Base (±160°) | 13 | 19 |

**DRV8825 wiring per driver:**
- `STEP` → GPIO STEP pin
- `DIR` → GPIO DIR pin
- `GND` → Pi GND + Power Supply GND (common ground)
- `VMOT` → 12–24V power supply +
- `ENABLE` → GND (always enabled)
- `A1, A2, B1, B2` → Motor coil wires

---

## Installation

### 1. Clone the repository on BOTH Pis
```bash
cd ~
git clone <your-repo-url> heliocoreos
cd heliocoreos
```

### 2. Run setup script

**On Master-Pi:**
```bash
chmod +x install/master-pi.sh
sudo bash install/master-pi.sh
```

**On Farm-Pi:**
```bash
# First edit the Master-Pi IP address
nano farm-node/config.json   # Change "master_ip" to your Master-Pi IP

chmod +x install/farm-pi.sh
sudo bash install/farm-pi.sh
```

### 3. Start the system

**On Master-Pi** (auto-starts on boot, or manually):
```bash
sudo systemctl start heliocore-telemetry
sudo systemctl start heliocore-registry
python3 master-node/heliocore_os.py   # Optional: CLI dashboard
```

**On Farm-Pi** (auto-starts on boot, or manually):
```bash
sudo python3 core/init.py
```

### 4. Access dashboards
- **CLI Dashboard:** runs in terminal on Master-Pi
- **Grafana:** http://master-pi:3000 (login: `admin` / `admin`)
- **Telemetry API:** http://master-pi:5000/status
- **Node Registry:** http://master-pi:5001/node/list

---

## Verification

```bash
# On Master-Pi — run integration test
cd ~/heliocoreos
python3 test/integration_test.py

# On Farm-Pi — test sensors
python3 farm-node/sensor_manager.py

# On Farm-Pi — test motors
sudo python3 farm-node/motor_controller.py
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: RPi.GPIO` | Run `sudo pip3 install RPi.GPIO` (Farm-Pi only) |
| Farm-Pi can't reach Master-Pi | Check `ping master-pi` and verify `config.json` IP |
| Motors don't move | Check 12–24V power supply and DRV8825 wiring |
| Sensors stuck at 0 | Verify VCC=5V on GPIO training board |
| Grafana shows no data | Ensure telemetry server is running: `systemctl status heliocore-telemetry` |
| Permission denied on GPIO | Run with `sudo` or add user to `gpio` group |
