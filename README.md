# HelioCore OS

Distributed solar tracking control system for mechanical solar flower prototype.

## Hardware Requirements
- 2x Raspberry Pi (3B+ or 4)
- 3x NEMA 23 stepper motors with DRV8825 drivers
- 6x LDR modules (LM393 comparator)
- 2x Rain sensors (digital output)
- Raspberry Pi GPIO training board

## Quick Start

### 1. Network Configuration
Assign static IPs to both Raspberry Pis or use mDNS:
- Master-Pi: 192.168.1.100 (or master-pi.local)
- Farm-Pi: 192.168.1.101 (or farm-pi.local)

### 2. Master-Pi Setup
```bash
git clone <repository>
cd heliocoreos
sudo bash install/setup_master.sh
```

### 3. Farm-Pi Setup
```bash
git clone <repository>
cd heliocoreos
nano farm-node/config.json  # Update master_ip
sudo bash install/setup_farm.sh
```

### 4. Hardware Connections
Connect to Farm-Pi GPIO training board:
- LDR sensors: GPIO 17,27,22,23,24,25
- Rain sensors: GPIO 5,6
- Motor 1 (Petal): STEP=12, DIR=16
- Motor 2 (Tilt): STEP=20, DIR=21
- Motor 3 (Base): STEP=13, DIR=19

### 5. Start Services

**Master-Pi:**
```bash
sudo systemctl start heliocore-master
python3 master-node/heliocore_os.py
```

**Farm-Pi:**
```bash
sudo systemctl start heliocore-farm
```

### 6. Access Dashboards
- CLI: Terminal on Master-Pi
- Grafana: http://master-pi:3000 (admin/admin)
- Metrics: http://master-pi:5000/metrics

## Integration Test
```bash
cd test
python3 integration_test.py
```

## Troubleshooting

**Farm-Pi not connecting:**
- Check network connectivity: `ping master-pi`
- Verify config.json has correct IP
- Check telemetry server: `curl http://master-pi:5000/status`

**Motors not moving:**
- Verify GPIO connections
- Check DRV8825 power supply (12-24V)
- Run motor test: `sudo python3 farm-node/motor_controller.py`

**Sensors not reading:**
- Check 5V power to sensors
- Verify GPIO pin numbers in config.json
- Run sensor test: `python3 farm-node/sensor_manager.py`

## System Architecture
```
┌─────────────────┐         ┌─────────────────┐
│   Master-Pi     │         │    Farm-Pi       │
│                 │         │                  │
│  Telemetry      │◄────────│  Sensor Mgr      │
│  Server :5000   │  HTTP   │  Motor Ctrl      │
│                 │         │  Tracking Algo   │
│  Metrics :5000  │         │  Rain Protect    │
│  Grafana :3000  │         │                  │
│  CLI Interface  │         │  Control Loop    │
└─────────────────┘         └──────────────────┘
```

## Hackathon Demo Checklist
- [ ] Both Pis powered and connected to network
- [ ] All sensors connected and reading
- [ ] All motors connected and calibrated
- [ ] Telemetry server running on Master-Pi
- [ ] Farm node running on Farm-Pi
- [ ] Grafana dashboard accessible
- [ ] CLI showing live data
- [ ] Sun tracking responding to light
- [ ] Rain protection tested and working
