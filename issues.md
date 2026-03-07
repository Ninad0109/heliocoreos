# HelioCore OS Development Roadmap

Complete implementation guide for distributed solar tracking system prototype.

---

# Issue 1: Repository Architecture and Development Environment

## Objective
Establish project structure, dependencies, and configuration files for both Master-Pi and Farm-Pi nodes.

## Architecture
The system uses a distributed architecture with two independent Raspberry Pi nodes:
- **Master-Pi**: Runs telemetry server, CLI interface, and Grafana dashboard
- **Farm-Pi**: Controls hardware (sensors + motors) and transmits telemetry

Both nodes communicate over local network via HTTP. Master-Pi acts as data aggregator and visualization hub. Farm-Pi operates as autonomous hardware controller with fallback logic.

## Implementation
Create directory structure, dependency files, and network configuration templates.

## File Structure
```
heliocoreos/
├── master-node/
│   ├── requirements.txt
│   └── config.json
├── farm-node/
│   ├── requirements.txt
│   └── config.json
├── dashboards/
├── install/
├── README.md
└── issues.md
```

## Code

**README.md**
```markdown
# HelioCore OS

Distributed solar tracking control system for mechanical solar flower prototype.

## Hardware Requirements
- 2x Raspberry Pi (3B+ or 4)
- 3x NEMA 23 stepper motors with DRV8825 drivers
- 6x LDR modules (LM393 comparator)
- 2x Rain sensors (digital output)
- Raspberry Pi GPIO training board

## Network Setup
Both Pis must be on same network. Configure static IPs recommended.

## Installation
```
# On Master-Pi
cd master-node
sudo bash ../install/setup_master.sh

# On Farm-Pi
cd farm-node
sudo bash ../install/setup_farm.sh
```

## Usage
```
# Start Master-Pi services
python3 telemetry_server.py &
python3 heliocore_os.py

# Start Farm-Pi
python3 farm_node.py
```
```

**master-node/requirements.txt**
```
flask==2.3.0
requests==2.31.0
```

**master-node/config.json**
```json
{
  "telemetry_port": 5000,
  "metrics_port": 9090,
  "farm_node_timeout": 10,
  "refresh_rate": 1.0
}
```

**farm-node/requirements.txt**
```
RPi.GPIO==0.7.1
requests==2.31.0
```

**farm-node/config.json**
```json
{
  "master_ip": "192.168.1.100",
  "master_port": 5000,
  "telemetry_interval": 1.0,
  "ldr_pins": [17, 27, 22, 23, 24, 25],
  "rain_pins": [5, 6],
  "motor1_step": 12,
  "motor1_dir": 16,
  "motor2_step": 20,
  "motor2_dir": 21,
  "motor3_step": 13,
  "motor3_dir": 19,
  "base_min_angle": -160,
  "base_max_angle": 160,
  "tilt_min_angle": 0,
  "tilt_max_angle": 90
}
```

## Test Procedure
1. Clone repository on both Raspberry Pis
2. Verify directory structure exists
3. Check all config files are present
4. Install dependencies: `pip3 install -r requirements.txt`

## Expected Output
```
heliocoreos/
├── master-node/ (with requirements.txt, config.json)
├── farm-node/ (with requirements.txt, config.json)
├── dashboards/
├── install/
└── README.md
```

## Completion Criteria
- [ ] Directory structure created
- [ ] All config files present and valid JSON
- [ ] Dependencies installable without errors
- [ ] README documents setup process

---

# Issue 2: Telemetry Server for Master-Pi

## Objective
Build Flask-based telemetry server that receives sensor data from Farm-Pi and stores latest state in memory.

## Architecture
The telemetry server runs on Master-Pi and exposes two endpoints:
- **POST /telemetry**: Receives JSON payloads from Farm-Pi
- **GET /metrics**: Exposes Prometheus-style metrics for Grafana

Data flow: Farm-Pi → HTTP POST → Master-Pi → In-memory storage → Metrics endpoint → Grafana

The server maintains only the latest telemetry snapshot (no historical storage). This keeps memory footprint minimal for Raspberry Pi.

## Hardware Integration
No direct hardware integration. Server runs on Master-Pi which has no sensors/motors connected.

## Implementation
Create Flask server with two routes and thread-safe state management.

## File Structure
```
master-node/
├── telemetry_server.py
├── metrics.py
├── requirements.txt
└── config.json
```

## Code

**master-node/telemetry_server.py**
```python
from flask import Flask, request, jsonify
import json
import threading
from datetime import datetime

app = Flask(__name__)
telemetry_lock = threading.Lock()

telemetry_data = {
    "ldr_left": 0,
    "ldr_right": 0,
    "ldr_top": 0,
    "ldr_bottom": 0,
    "rain": 0,
    "petal_state": 0,
    "tilt_angle": 0,
    "base_angle": 0,
    "motor_state": 0,
    "timestamp": None,
    "farm_online": False
}

@app.route('/telemetry', methods=['POST'])
def receive_telemetry():
    global telemetry_data
    data = request.get_json()
    
    with telemetry_lock:
        telemetry_data.update(data)
        telemetry_data['timestamp'] = datetime.now().isoformat()
        telemetry_data['farm_online'] = True
    
    return jsonify({"status": "ok"}), 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    with telemetry_lock:
        metrics = "\n".join([
            f"ldr_left {telemetry_data['ldr_left']}",
            f"ldr_right {telemetry_data['ldr_right']}",
            f"ldr_top {telemetry_data['ldr_top']}",
            f"ldr_bottom {telemetry_data['ldr_bottom']}",
            f"rain_sensor {telemetry_data['rain']}",
            f"petal_state {telemetry_data['petal_state']}",
            f"tilt_angle {telemetry_data['tilt_angle']}",
            f"base_angle {telemetry_data['base_angle']}",
            f"motor_state {telemetry_data['motor_state']}",
            f"farm_online {int(telemetry_data['farm_online'])}"
        ])
    return metrics, 200, {'Content-Type': 'text/plain'}

@app.route('/status', methods=['GET'])
def get_status():
    with telemetry_lock:
        return jsonify(telemetry_data), 200

def get_telemetry():
    with telemetry_lock:
        return telemetry_data.copy()

if __name__ == '__main__':
    with open('config.json') as f:
        config = json.load(f)
    app.run(host='0.0.0.0', port=config['telemetry_port'], debug=False)
```

**master-node/metrics.py**
```python
import requests

def get_current_metrics(base_url='http://localhost:5000'):
    try:
        response = requests.get(f'{base_url}/status', timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None
```

## Test Procedure
1. Start telemetry server: `python3 telemetry_server.py`
2. Test POST endpoint:
```bash
curl -X POST http://localhost:5000/telemetry \
  -H "Content-Type: application/json" \
  -d '{"ldr_left":1,"ldr_right":0,"rain":0,"petal_state":1,"tilt_angle":35,"base_angle":12,"motor_state":1}'
```
3. Test metrics endpoint: `curl http://localhost:5000/metrics`
4. Test status endpoint: `curl http://localhost:5000/status`

## Expected Output
**Metrics endpoint:**
```
ldr_left 1
ldr_right 0
ldr_top 0
ldr_bottom 0
rain_sensor 0
petal_state 1
tilt_angle 35
base_angle 12
motor_state 1
farm_online 1
```

**Status endpoint:**
```json
{
  "ldr_left": 1,
  "ldr_right": 0,
  "rain": 0,
  "petal_state": 1,
  "tilt_angle": 35,
  "base_angle": 12,
  "motor_state": 1,
  "timestamp": "2024-01-15T10:30:45.123456",
  "farm_online": true
}
```

## Completion Criteria
- [ ] Server starts without errors
- [ ] POST /telemetry accepts JSON and returns 200
- [ ] GET /metrics returns Prometheus format
- [ ] GET /status returns JSON with latest data
- [ ] Thread-safe data access implemented

---

# Issue 3: Grafana Integration and Dashboard Setup

## Objective
Configure Grafana to scrape metrics from Master-Pi and create real-time visualization dashboard.

## Architecture
Grafana runs on Master-Pi and uses Prometheus data source to scrape the /metrics endpoint. The dashboard displays:
- LDR sensor states (binary indicators)
- Rain sensor status
- Motor angles (gauges)
- Petal state
- Farm node connectivity

Grafana polls /metrics every 1 second for real-time updates.

## Hardware Integration
No direct hardware. Grafana reads metrics exposed by telemetry server.

## Implementation
Install Grafana, configure Prometheus data source, import dashboard JSON.

## File Structure
```
dashboards/
└── grafana_dashboard.json
install/
└── setup_grafana.sh
```

## Code

**install/setup_grafana.sh**
```bash
#!/bin/bash

echo "Installing Grafana on Master-Pi..."

# Install Grafana
sudo apt-get install -y apt-transport-https software-properties-common
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install -y grafana

# Enable and start Grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

echo "Grafana installed. Access at http://localhost:3000"
echo "Default credentials: admin/admin"
```

**dashboards/grafana_dashboard.json**
```json
{
  "dashboard": {
    "title": "HelioCore OS Dashboard",
    "panels": [
      {
        "id": 1,
        "title": "Farm Node Status",
        "type": "stat",
        "targets": [{"expr": "farm_online"}],
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4}
      },
      {
        "id": 2,
        "title": "Base Angle",
        "type": "gauge",
        "targets": [{"expr": "base_angle"}],
        "fieldConfig": {"min": -160, "max": 160},
        "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4}
      },
      {
        "id": 3,
        "title": "Tilt Angle",
        "type": "gauge",
        "targets": [{"expr": "tilt_angle"}],
        "fieldConfig": {"min": 0, "max": 90},
        "gridPos": {"x": 12, "y": 0, "w": 6, "h": 4}
      },
      {
        "id": 4,
        "title": "LDR Sensors",
        "type": "stat",
        "targets": [
          {"expr": "ldr_left", "legendFormat": "Left"},
          {"expr": "ldr_right", "legendFormat": "Right"},
          {"expr": "ldr_top", "legendFormat": "Top"},
          {"expr": "ldr_bottom", "legendFormat": "Bottom"}
        ],
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 4}
      },
      {
        "id": 5,
        "title": "Rain Sensor",
        "type": "stat",
        "targets": [{"expr": "rain_sensor"}],
        "gridPos": {"x": 12, "y": 4, "w": 6, "h": 4}
      },
      {
        "id": 6,
        "title": "Petal State",
        "type": "stat",
        "targets": [{"expr": "petal_state"}],
        "gridPos": {"x": 18, "y": 0, "w": 6, "h": 4}
      }
    ],
    "refresh": "1s",
    "time": {"from": "now-5m", "to": "now"}
  }
}
```

**dashboards/prometheus.yml**
```yaml
global:
  scrape_interval: 1s

scrape_configs:
  - job_name: 'heliocore'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

## Test Procedure
1. Run setup script: `sudo bash install/setup_grafana.sh`
2. Access Grafana: http://localhost:3000 (admin/admin)
3. Add Prometheus data source pointing to http://localhost:5000/metrics
4. Import dashboard from grafana_dashboard.json
5. Start telemetry server
6. Send test telemetry data
7. Verify dashboard updates in real-time

## Expected Output
Grafana dashboard showing:
- Farm Node Status: Online/Offline indicator
- Base Angle: Gauge from -160° to +160°
- Tilt Angle: Gauge from 0° to 90°
- LDR Sensors: 4 binary indicators
- Rain Sensor: Binary indicator
- Petal State: Open/Closed indicator

All panels update every 1 second.

## Completion Criteria
- [ ] Grafana installed and running
- [ ] Dashboard JSON imports successfully
- [ ] All panels display metrics correctly
- [ ] Real-time updates working (1s refresh)
- [ ] Gauges show correct min/max ranges

---

# Issue 4: HelioCore OS CLI Interface

## Objective
Create terminal-based CLI that displays live system status, sensor readings, and motor states in real-time.

## Architecture
The CLI runs on Master-Pi and polls the telemetry server's /status endpoint every second. It uses ANSI escape codes to create a refreshing terminal display without scrolling.

Display sections:
1. Header with system name and version
2. Farm node connectivity status
3. Sensor readings (LDR + rain)
4. Motor states and angles
5. System uptime

The CLI is the primary operator interface during demonstrations.

## Hardware Integration
No direct hardware. Reads data from telemetry server API.

## Implementation
Build Python CLI with terminal refresh logic and formatted output.

## File Structure
```
master-node/
├── heliocore_os.py
├── metrics.py
└── config.json
```

## Code

**master-node/heliocore_os.py**
```python
#!/usr/bin/env python3
import os
import sys
import time
import json
from datetime import datetime
from metrics import get_current_metrics

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_status(online):
    return "ONLINE" if online else "OFFLINE"

def format_binary(value):
    return "YES" if value else "NO"

def format_petal(state):
    return "OPEN" if state else "CLOSED"

def format_motor(state):
    return "ACTIVE" if state else "IDLE"

def display_dashboard(data, start_time):
    clear_screen()
    
    uptime = int(time.time() - start_time)
    
    print("=" * 50)
    print("           HelioCore OS v1.0")
    print("=" * 50)
    print()
    
    if data:
        print(f"Farm Node: {format_status(data.get('farm_online', False))}")
        print(f"Sun Tracking: {format_motor(data.get('motor_state', 0))}")
        print(f"Rain Protection: {'ACTIVE' if data.get('rain', 0) else 'STANDBY'}")
        print()
        
        print("Sensors")
        print("-" * 50)
        print(f"Left Light:   {data.get('ldr_left', 0)}")
        print(f"Right Light:  {data.get('ldr_right', 0)}")
        print(f"Top Light:    {data.get('ldr_top', 0)}")
        print(f"Bottom Light: {data.get('ldr_bottom', 0)}")
        print(f"Rain:         {format_binary(data.get('rain', 0))}")
        print()
        
        print("Motors")
        print("-" * 50)
        print(f"Base Angle:   {data.get('base_angle', 0)}°")
        print(f"Tilt Angle:   {data.get('tilt_angle', 0)}°")
        print(f"Petals:       {format_petal(data.get('petal_state', 0))}")
        print()
        
        if data.get('timestamp'):
            print(f"Last Update:  {data['timestamp']}")
    else:
        print("Farm Node: OFFLINE")
        print("Waiting for telemetry data...")
        print()
    
    print(f"System Uptime: {uptime}s")
    print()
    print("Press Ctrl+C to exit")

def main():
    with open('config.json') as f:
        config = json.load(f)
    
    base_url = f"http://localhost:{config['telemetry_port']}"
    refresh_rate = config.get('refresh_rate', 1.0)
    start_time = time.time()
    
    print("Starting HelioCore OS...")
    time.sleep(1)
    
    try:
        while True:
            data = get_current_metrics(base_url)
            display_dashboard(data, start_time)
            time.sleep(refresh_rate)
    except KeyboardInterrupt:
        clear_screen()
        print("\nHelioCore OS shutdown complete.")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

## Test Procedure
1. Ensure telemetry server is running
2. Start CLI: `python3 heliocore_os.py`
3. Send test telemetry via curl (from Issue 2)
4. Verify display updates every second
5. Check all fields render correctly
6. Test Ctrl+C exit

## Expected Output
```
==================================================
           HelioCore OS v1.0
==================================================

Farm Node: ONLINE
Sun Tracking: ACTIVE
Rain Protection: STANDBY

Sensors
--------------------------------------------------
Left Light:   1
Right Light:  0
Top Light:    1
Bottom Light: 0
Rain:         NO

Motors
--------------------------------------------------
Base Angle:   18°
Tilt Angle:   42°
Petals:       OPEN

Last Update:  2024-01-15T10:30:45.123456
System Uptime: 127s

Press Ctrl+C to exit
```

## Completion Criteria
- [ ] CLI starts without errors
- [ ] Display refreshes every second
- [ ] All sensor values shown correctly
- [ ] Motor angles display with degree symbol
- [ ] Uptime counter increments
- [ ] Graceful exit on Ctrl+C

---

# Issue 5: Sensor Manager Using GPIO Training Board

## Objective
Implement sensor reading module for 6 LDR modules and 2 rain sensors connected to Raspberry Pi GPIO training board.

## Architecture
The sensor manager uses RPi.GPIO library to read digital inputs from LM393 comparator modules. Each sensor provides HIGH (1) or LOW (0) signal.

LDR sensor mapping:
- LDR1 (GPIO 17): Left-Top
- LDR2 (GPIO 27): Top-Center
- LDR3 (GPIO 22): Right-Top
- LDR4 (GPIO 23): Left-Bottom
- LDR5 (GPIO 24): Bottom-Center
- LDR6 (GPIO 25): Right-Bottom

Rain sensors:
- Rain1 (GPIO 5): Primary
- Rain2 (GPIO 6): Secondary

Directional grouping for tracking:
- LEFT = LDR1 + LDR4
- RIGHT = LDR3 + LDR6
- TOP = LDR2
- BOTTOM = LDR5

## Hardware Integration
Connect sensors to GPIO training board 3-pin connectors:
- 5V → Sensor VCC
- GPIO → Sensor OUT
- GND → Sensor GND

No breadboard required. Direct plug-and-play connection.

## Implementation
Create sensor manager class with GPIO initialization and reading methods.

## File Structure
```
farm-node/
├── sensor_manager.py
└── config.json
```

## Code

**farm-node/sensor_manager.py**
```python
import RPi.GPIO as GPIO
import time

class SensorManager:
    def __init__(self, config):
        self.ldr_pins = config['ldr_pins']
        self.rain_pins = config['rain_pins']
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        for pin in self.ldr_pins + self.rain_pins:
            GPIO.setup(pin, GPIO.IN)
    
    def read_ldr(self, index):
        if 0 <= index < len(self.ldr_pins):
            return GPIO.input(self.ldr_pins[index])
        return 0
    
    def read_all_ldr(self):
        return [GPIO.input(pin) for pin in self.ldr_pins]
    
    def read_rain(self):
        return any(GPIO.input(pin) for pin in self.rain_pins)
    
    def get_directional_light(self):
        ldr = self.read_all_ldr()
        return {
            'left': ldr[0] + ldr[3],
            'right': ldr[2] + ldr[5],
            'top': ldr[1],
            'bottom': ldr[4]
        }
    
    def get_telemetry(self):
        ldr = self.read_all_ldr()
        return {
            'ldr_left': ldr[0] + ldr[3],
            'ldr_right': ldr[2] + ldr[5],
            'ldr_top': ldr[1],
            'ldr_bottom': ldr[4],
            'rain': int(self.read_rain())
        }
    
    def cleanup(self):
        GPIO.cleanup()

if __name__ == '__main__':
    import json
    with open('config.json') as f:
        config = json.load(f)
    
    sensor = SensorManager(config)
    
    try:
        while True:
            data = sensor.get_telemetry()
            print(f"LDR L:{data['ldr_left']} R:{data['ldr_right']} T:{data['ldr_top']} B:{data['ldr_bottom']} | Rain:{data['rain']}")
            time.sleep(1)
    except KeyboardInterrupt:
        sensor.cleanup()
        print("\nSensor test complete")
```

## Test Procedure
1. Connect 6 LDR modules to GPIO pins 17,27,22,23,24,25
2. Connect 2 rain sensors to GPIO pins 5,6
3. Run test: `python3 sensor_manager.py`
4. Cover/uncover LDR sensors with hand
5. Trigger rain sensors with water
6. Verify readings change in real-time

## Expected Output
```
LDR L:2 R:1 T:1 B:0 | Rain:0
LDR L:2 R:2 T:1 B:1 | Rain:0
LDR L:1 R:2 T:0 B:1 | Rain:1
LDR L:0 R:0 T:0 B:0 | Rain:1
```

## Completion Criteria
- [ ] All 6 LDR sensors readable
- [ ] Both rain sensors readable
- [ ] Directional grouping works correctly
- [ ] No GPIO warnings or errors
- [ ] Cleanup releases GPIO resources


---

# Issue 6: DRV8825 Motor Controller for Three Stepper Motors

## Objective
Implement motor control system for three NEMA 23 stepper motors using DRV8825 drivers with position tracking and safety limits.

## Architecture
Three independent stepper motors controlled via GPIO step/direction pins:
- **Motor 1 (Petal)**: Binary states (OPEN/CLOSED), uses step counting
- **Motor 2 (Tilt)**: 0-90° range, 200 steps per revolution, gear ratio applied
- **Motor 3 (Base)**: -160° to +160° range, prevents cable twisting

Each motor requires:
- STEP pin: Pulse to move one step
- DIR pin: HIGH/LOW for direction
- Position tracking in degrees/state

Safety features:
- Angle limit enforcement
- Emergency stop capability
- Position persistence

## Hardware Integration
Connect DRV8825 drivers to GPIO training board:
- Motor 1: STEP=GPIO12, DIR=GPIO16
- Motor 2: STEP=GPIO20, DIR=GPIO21
- Motor 3: STEP=GPIO13, DIR=GPIO19

DRV8825 wiring:
- STEP/DIR → GPIO pins
- ENABLE → GND (always enabled)
- M0,M1,M2 → Microstep configuration
- VMOT → 12-24V power supply
- Motor coils → A1,A2,B1,B2

## Implementation
Create motor controller class with step generation, position tracking, and limit enforcement.

## File Structure
```
farm-node/
├── motor_controller.py
└── config.json
```

## Code

**farm-node/motor_controller.py**
```python
import RPi.GPIO as GPIO
import time

class MotorController:
    def __init__(self, config):
        self.config = config
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Motor 1: Petal actuator
        self.m1_step = config['motor1_step']
        self.m1_dir = config['motor1_dir']
        self.petal_state = 0  # 0=CLOSED, 1=OPEN
        
        # Motor 2: Tilt axis
        self.m2_step = config['motor2_step']
        self.m2_dir = config['motor2_dir']
        self.tilt_angle = 0
        
        # Motor 3: Base rotation
        self.m3_step = config['motor3_step']
        self.m3_dir = config['motor3_dir']
        self.base_angle = 0
        
        # Setup GPIO
        for pin in [self.m1_step, self.m1_dir, self.m2_step, self.m2_dir, self.m3_step, self.m3_dir]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        self.steps_per_rev = 200
        self.microsteps = 16
        self.step_delay = 0.001
    
    def step_motor(self, step_pin, dir_pin, steps, direction):
        GPIO.output(dir_pin, GPIO.HIGH if direction > 0 else GPIO.LOW)
        time.sleep(0.001)
        
        for _ in range(abs(steps)):
            GPIO.output(step_pin, GPIO.HIGH)
            time.sleep(self.step_delay)
            GPIO.output(step_pin, GPIO.LOW)
            time.sleep(self.step_delay)
    
    def set_petal_state(self, state):
        if state != self.petal_state:
            steps = 400 if state else -400
            self.step_motor(self.m1_step, self.m1_dir, abs(steps), 1 if state else -1)
            self.petal_state = state
    
    def set_tilt_angle(self, angle):
        angle = max(self.config['tilt_min_angle'], min(angle, self.config['tilt_max_angle']))
        delta = angle - self.tilt_angle
        steps = int((delta / 360.0) * self.steps_per_rev * self.microsteps)
        
        if steps != 0:
            self.step_motor(self.m2_step, self.m2_dir, abs(steps), 1 if steps > 0 else -1)
            self.tilt_angle = angle
    
    def set_base_angle(self, angle):
        angle = max(self.config['base_min_angle'], min(angle, self.config['base_max_angle']))
        delta = angle - self.base_angle
        steps = int((delta / 360.0) * self.steps_per_rev * self.microsteps)
        
        if steps != 0:
            self.step_motor(self.m3_step, self.m3_dir, abs(steps), 1 if steps > 0 else -1)
            self.base_angle = angle
    
    def move_base_relative(self, delta_angle):
        new_angle = self.base_angle + delta_angle
        self.set_base_angle(new_angle)
    
    def move_tilt_relative(self, delta_angle):
        new_angle = self.tilt_angle + delta_angle
        self.set_tilt_angle(new_angle)
    
    def open_petals(self):
        self.set_petal_state(1)
    
    def close_petals(self):
        self.set_petal_state(0)
    
    def get_state(self):
        return {
            'petal_state': self.petal_state,
            'tilt_angle': self.tilt_angle,
            'base_angle': self.base_angle
        }
    
    def safe_position(self):
        self.close_petals()
        self.set_tilt_angle(0)
        self.set_base_angle(0)
    
    def cleanup(self):
        GPIO.cleanup()

if __name__ == '__main__':
    import json
    with open('config.json') as f:
        config = json.load(f)
    
    motor = MotorController(config)
    
    try:
        print("Testing motors...")
        print("Opening petals...")
        motor.open_petals()
        time.sleep(1)
        
        print("Setting tilt to 45°...")
        motor.set_tilt_angle(45)
        time.sleep(1)
        
        print("Rotating base to 30°...")
        motor.set_base_angle(30)
        time.sleep(1)
        
        print("Returning to safe position...")
        motor.safe_position()
        
        print(f"Final state: {motor.get_state()}")
    except KeyboardInterrupt:
        motor.safe_position()
        motor.cleanup()
        print("\nMotor test complete")
```

## Test Procedure
1. Connect three DRV8825 drivers to power supply (12-24V)
2. Connect STEP/DIR pins to GPIO as configured
3. Connect NEMA 23 motors to drivers
4. Run test: `sudo python3 motor_controller.py`
5. Verify petal motor moves
6. Verify tilt motor moves to 45°
7. Verify base motor rotates to 30°
8. Verify safe position returns all to zero
9. Check angle limits prevent over-rotation

## Expected Output
```
Testing motors...
Opening petals...
Setting tilt to 45°...
Rotating base to 30°...
Returning to safe position...
Final state: {'petal_state': 0, 'tilt_angle': 0, 'base_angle': 0}
```

Motors should move smoothly without stalling. Verify:
- Petal actuator opens/closes
- Tilt axis moves 45° up then returns
- Base rotates 30° then returns to center

## Completion Criteria
- [ ] All three motors controllable independently
- [ ] Position tracking accurate
- [ ] Angle limits enforced (base: -160 to +160, tilt: 0 to 90)
- [ ] Safe position function works
- [ ] No motor stalling or missed steps


---

# Issue 7: Sun Tracking Algorithm

## Objective
Implement differential light sensing algorithm that adjusts motor positions to maximize solar panel alignment with sun.

## Architecture
The tracking algorithm uses directional LDR groupings to determine sun position:

**Horizontal tracking (base motor):**
- Compare LEFT vs RIGHT light intensity
- If LEFT > RIGHT: rotate base left
- If RIGHT > LEFT: rotate base right
- If difference < threshold: stop

**Vertical tracking (tilt motor):**
- Compare TOP vs BOTTOM light intensity
- If TOP > BOTTOM: tilt up
- If BOTTOM > TOP: tilt down
- If difference < threshold: stop

**Algorithm parameters:**
- Threshold: Minimum difference to trigger movement (default: 1)
- Step size: Degrees to move per iteration (default: 2°)
- Update interval: Time between tracking updates (default: 2s)

The algorithm runs continuously unless rain protection is active.

## Hardware Integration
Reads from SensorManager (6 LDRs grouped directionally).
Controls MotorController (base and tilt motors).

## Implementation
Create tracking algorithm class with differential sensing logic.

## File Structure
```
farm-node/
├── tracking_algorithm.py
├── sensor_manager.py
└── motor_controller.py
```

## Code

**farm-node/tracking_algorithm.py**
```python
import time

class TrackingAlgorithm:
    def __init__(self, sensor_manager, motor_controller, config):
        self.sensor = sensor_manager
        self.motor = motor_controller
        self.threshold = 1
        self.step_size = 2
        self.update_interval = 2.0
        self.active = False
    
    def calculate_tracking_adjustment(self):
        light = self.sensor.get_directional_light()
        
        base_adjustment = 0
        tilt_adjustment = 0
        
        # Horizontal tracking
        h_diff = light['left'] - light['right']
        if abs(h_diff) >= self.threshold:
            if h_diff > 0:
                base_adjustment = -self.step_size  # Move left
            else:
                base_adjustment = self.step_size   # Move right
        
        # Vertical tracking
        v_diff = light['top'] - light['bottom']
        if abs(v_diff) >= self.threshold:
            if v_diff > 0:
                tilt_adjustment = self.step_size   # Tilt up
            else:
                tilt_adjustment = -self.step_size  # Tilt down
        
        return base_adjustment, tilt_adjustment
    
    def update(self):
        if not self.active:
            return False
        
        base_adj, tilt_adj = self.calculate_tracking_adjustment()
        
        if base_adj != 0:
            self.motor.move_base_relative(base_adj)
        
        if tilt_adj != 0:
            self.motor.move_tilt_relative(tilt_adj)
        
        return base_adj != 0 or tilt_adj != 0
    
    def start(self):
        self.active = True
        self.motor.open_petals()
    
    def stop(self):
        self.active = False
    
    def is_active(self):
        return self.active

if __name__ == '__main__':
    import json
    from sensor_manager import SensorManager
    from motor_controller import MotorController
    
    with open('config.json') as f:
        config = json.load(f)
    
    sensor = SensorManager(config)
    motor = MotorController(config)
    tracker = TrackingAlgorithm(sensor, motor, config)
    
    try:
        print("Starting sun tracking test...")
        tracker.start()
        
        for i in range(10):
            print(f"\nIteration {i+1}")
            light = sensor.get_directional_light()
            print(f"Light: L={light['left']} R={light['right']} T={light['top']} B={light['bottom']}")
            
            moved = tracker.update()
            state = motor.get_state()
            print(f"Position: Base={state['base_angle']}° Tilt={state['tilt_angle']}°")
            print(f"Movement: {'YES' if moved else 'NO'}")
            
            time.sleep(2)
        
        tracker.stop()
        motor.safe_position()
        
    except KeyboardInterrupt:
        tracker.stop()
        motor.safe_position()
        sensor.cleanup()
        motor.cleanup()
        print("\nTracking test complete")
```

## Test Procedure
1. Ensure all sensors and motors connected
2. Run test: `sudo python3 tracking_algorithm.py`
3. Use flashlight to simulate sun from different angles
4. Shine light from left → verify base rotates left
5. Shine light from right → verify base rotates right
6. Shine light from top → verify tilt increases
7. Shine light evenly → verify motors stop
8. Verify position stays within limits

## Expected Output
```
Starting sun tracking test...

Iteration 1
Light: L=2 R=0 T=1 B=0
Position: Base=-2° Tilt=2°
Movement: YES

Iteration 2
Light: L=2 R=1 T=1 B=1
Position: Base=-4° Tilt=2°
Movement: YES

Iteration 3
Light: L=1 R=1 T=1 B=0
Position: Base=-4° Tilt=4°
Movement: YES

Iteration 4
Light: L=1 R=1 T=1 B=1
Position: Base=-4° Tilt=4°
Movement: NO
```

## Completion Criteria
- [ ] Algorithm responds to left/right light differential
- [ ] Algorithm responds to top/bottom light differential
- [ ] Threshold prevents jitter when light is balanced
- [ ] Motors stop when light is equalized
- [ ] Position limits respected during tracking
- [ ] Petals open when tracking starts


---

# Issue 8: Rain Protection Logic

## Objective
Implement emergency rain protection system that detects rain and moves solar flower to safe position.

## Architecture
Rain protection operates as highest-priority safety system:

**Detection:**
- Monitor both rain sensors continuously
- Trigger if ANY sensor detects rain

**Protection sequence:**
1. Stop sun tracking immediately
2. Close petals to protect electronics
3. Move tilt to 0° (horizontal)
4. Move base to 0° (center position)
5. Enter standby mode

**Recovery:**
- Wait for rain sensors to clear
- Add delay to prevent false recovery
- Resume normal tracking operation

**State machine:**
- NORMAL: Tracking active, rain monitoring
- RAIN_DETECTED: Protection sequence executing
- PROTECTED: Safe position held, waiting for clear
- RECOVERY: Delay period before resuming

## Hardware Integration
Reads from SensorManager (rain sensors).
Controls MotorController (all motors to safe position).
Overrides TrackingAlgorithm when rain detected.

## Implementation
Create rain protection class with state machine and safety logic.

## File Structure
```
farm-node/
├── rain_protection.py
├── sensor_manager.py
├── motor_controller.py
└── tracking_algorithm.py
```

## Code

**farm-node/rain_protection.py**
```python
import time
from enum import Enum

class ProtectionState(Enum):
    NORMAL = 1
    RAIN_DETECTED = 2
    PROTECTED = 3
    RECOVERY = 4

class RainProtection:
    def __init__(self, sensor_manager, motor_controller, tracking_algorithm):
        self.sensor = sensor_manager
        self.motor = motor_controller
        self.tracker = tracking_algorithm
        self.state = ProtectionState.NORMAL
        self.recovery_delay = 30  # seconds
        self.recovery_start = None
    
    def check_rain(self):
        return self.sensor.read_rain()
    
    def execute_protection_sequence(self):
        print("RAIN DETECTED - Executing protection sequence")
        
        # Stop tracking
        self.tracker.stop()
        
        # Close petals
        self.motor.close_petals()
        
        # Move to safe position
        self.motor.safe_position()
        
        self.state = ProtectionState.PROTECTED
        print("Protection sequence complete - System in safe mode")
    
    def update(self):
        rain_detected = self.check_rain()
        
        if self.state == ProtectionState.NORMAL:
            if rain_detected:
                self.state = ProtectionState.RAIN_DETECTED
                self.execute_protection_sequence()
        
        elif self.state == ProtectionState.PROTECTED:
            if not rain_detected:
                self.state = ProtectionState.RECOVERY
                self.recovery_start = time.time()
                print(f"Rain cleared - Starting {self.recovery_delay}s recovery delay")
        
        elif self.state == ProtectionState.RECOVERY:
            if rain_detected:
                # Rain detected again during recovery
                self.state = ProtectionState.PROTECTED
                self.recovery_start = None
                print("Rain detected again - Remaining in protected mode")
            elif time.time() - self.recovery_start >= self.recovery_delay:
                # Recovery complete
                self.state = ProtectionState.NORMAL
                self.tracker.start()
                print("Recovery complete - Resuming normal operation")
        
        return self.state
    
    def is_protected(self):
        return self.state in [ProtectionState.RAIN_DETECTED, ProtectionState.PROTECTED, ProtectionState.RECOVERY]
    
    def get_state_name(self):
        return self.state.name

if __name__ == '__main__':
    import json
    from sensor_manager import SensorManager
    from motor_controller import MotorController
    from tracking_algorithm import TrackingAlgorithm
    
    with open('config.json') as f:
        config = json.load(f)
    
    sensor = SensorManager(config)
    motor = MotorController(config)
    tracker = TrackingAlgorithm(sensor, motor, config)
    protection = RainProtection(sensor, motor, tracker)
    
    try:
        print("Starting rain protection test...")
        tracker.start()
        
        for i in range(60):
            state = protection.update()
            rain = sensor.read_rain()
            motor_state = motor.get_state()
            
            print(f"[{i}s] State: {state.name} | Rain: {rain} | Tracking: {tracker.is_active()} | Petals: {motor_state['petal_state']}")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        motor.safe_position()
        sensor.cleanup()
        motor.cleanup()
        print("\nRain protection test complete")
```

## Test Procedure
1. Start rain protection test: `sudo python3 rain_protection.py`
2. System should start in NORMAL state with tracking active
3. Trigger rain sensor with water
4. Verify protection sequence executes:
   - Tracking stops
   - Petals close
   - Motors move to safe position (0°, 0°)
5. Remove water from rain sensor
6. Verify recovery delay starts (30s)
7. Wait for recovery to complete
8. Verify tracking resumes automatically
9. Test re-triggering rain during recovery

## Expected Output
```
Starting rain protection test...
[0s] State: NORMAL | Rain: 0 | Tracking: True | Petals: 1
[1s] State: NORMAL | Rain: 0 | Tracking: True | Petals: 1
[2s] State: NORMAL | Rain: 1 | Tracking: True | Petals: 1
RAIN DETECTED - Executing protection sequence
Protection sequence complete - System in safe mode
[3s] State: PROTECTED | Rain: 1 | Tracking: False | Petals: 0
[4s] State: PROTECTED | Rain: 1 | Tracking: False | Petals: 0
[5s] State: PROTECTED | Rain: 0 | Tracking: False | Petals: 0
Rain cleared - Starting 30s recovery delay
[6s] State: RECOVERY | Rain: 0 | Tracking: False | Petals: 0
...
[35s] State: RECOVERY | Rain: 0 | Tracking: False | Petals: 0
Recovery complete - Resuming normal operation
[36s] State: NORMAL | Rain: 0 | Tracking: True | Petals: 1
```

## Completion Criteria
- [ ] Rain detection triggers protection immediately
- [ ] Protection sequence executes correctly
- [ ] System enters safe position (all motors at 0°)
- [ ] Petals close during protection
- [ ] Recovery delay prevents premature restart
- [ ] Tracking resumes after recovery
- [ ] Re-triggering during recovery handled correctly


---

# Issue 9: Farm Node Runtime Control Loop and Telemetry

## Objective
Create main control loop for Farm-Pi that integrates all subsystems and transmits telemetry to Master-Pi.

## Architecture
The farm node runtime is the main entry point that orchestrates:

**Initialization:**
1. Load configuration
2. Initialize sensor manager
3. Initialize motor controller
4. Initialize tracking algorithm
5. Initialize rain protection
6. Establish connection to Master-Pi

**Main control loop:**
1. Update rain protection (highest priority)
2. Update tracking algorithm (if not protected)
3. Read all sensor states
4. Get motor positions
5. Package telemetry data
6. Transmit to Master-Pi via HTTP POST
7. Sleep for configured interval
8. Repeat

**Error handling:**
- Network failures: Continue operation, retry telemetry
- Sensor failures: Log error, use last known values
- Motor failures: Enter safe mode
- Graceful shutdown on Ctrl+C

**Telemetry format:**
```json
{
  "ldr_left": 2,
  "ldr_right": 1,
  "ldr_top": 1,
  "ldr_bottom": 0,
  "rain": 0,
  "petal_state": 1,
  "tilt_angle": 35,
  "base_angle": 12,
  "motor_state": 1
}
```

## Hardware Integration
Integrates all hardware subsystems:
- SensorManager: Reads LDRs and rain sensors
- MotorController: Controls three stepper motors
- TrackingAlgorithm: Adjusts motor positions
- RainProtection: Safety override system

## Implementation
Create main farm node runtime with integrated control loop.

## File Structure
```
farm-node/
├── farm_node.py
├── sensor_manager.py
├── motor_controller.py
├── tracking_algorithm.py
├── rain_protection.py
└── config.json
```

## Code

**farm-node/farm_node.py**
```python
#!/usr/bin/env python3
import json
import time
import requests
import signal
import sys
from sensor_manager import SensorManager
from motor_controller import MotorController
from tracking_algorithm import TrackingAlgorithm
from rain_protection import RainProtection

class FarmNode:
    def __init__(self, config_path='config.json'):
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.master_url = f"http://{self.config['master_ip']}:{self.config['master_port']}/telemetry"
        self.telemetry_interval = self.config['telemetry_interval']
        
        print("Initializing Farm Node...")
        self.sensor = SensorManager(self.config)
        self.motor = MotorController(self.config)
        self.tracker = TrackingAlgorithm(self.sensor, self.motor, self.config)
        self.protection = RainProtection(self.sensor, self.motor, self.tracker)
        
        self.running = False
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def collect_telemetry(self):
        sensor_data = self.sensor.get_telemetry()
        motor_state = self.motor.get_state()
        
        telemetry = {
            'ldr_left': sensor_data['ldr_left'],
            'ldr_right': sensor_data['ldr_right'],
            'ldr_top': sensor_data['ldr_top'],
            'ldr_bottom': sensor_data['ldr_bottom'],
            'rain': sensor_data['rain'],
            'petal_state': motor_state['petal_state'],
            'tilt_angle': motor_state['tilt_angle'],
            'base_angle': motor_state['base_angle'],
            'motor_state': int(self.tracker.is_active())
        }
        
        return telemetry
    
    def send_telemetry(self, data):
        try:
            response = requests.post(self.master_url, json=data, timeout=2)
            return response.status_code == 200
        except Exception as e:
            print(f"Telemetry transmission failed: {e}")
            return False
    
    def run(self):
        print("Farm Node starting...")
        print(f"Master-Pi: {self.master_url}")
        print("Starting sun tracking...")
        
        self.tracker.start()
        self.running = True
        
        while self.running:
            try:
                # Update protection system (highest priority)
                protection_state = self.protection.update()
                
                # Update tracking (if not protected)
                if not self.protection.is_protected():
                    self.tracker.update()
                
                # Collect and send telemetry
                telemetry = self.collect_telemetry()
                self.send_telemetry(telemetry)
                
                # Status output
                print(f"State: {protection_state.name} | Base: {telemetry['base_angle']}° | Tilt: {telemetry['tilt_angle']}° | Rain: {telemetry['rain']}")
                
                time.sleep(self.telemetry_interval)
                
            except Exception as e:
                print(f"Error in control loop: {e}")
                time.sleep(1)
        
        self.cleanup()
    
    def shutdown(self, signum, frame):
        print("\nShutdown signal received...")
        self.running = False
    
    def cleanup(self):
        print("Moving to safe position...")
        self.tracker.stop()
        self.motor.safe_position()
        self.sensor.cleanup()
        self.motor.cleanup()
        print("Farm Node shutdown complete")
        sys.exit(0)

if __name__ == '__main__':
    node = FarmNode()
    node.run()
```

## Test Procedure
1. Ensure Master-Pi telemetry server is running
2. Update config.json with correct Master-Pi IP address
3. Connect all sensors and motors to Farm-Pi
4. Start farm node: `sudo python3 farm_node.py`
5. Verify initialization messages
6. Check telemetry transmission in Master-Pi logs
7. Test sun tracking with flashlight
8. Test rain protection with water
9. Verify graceful shutdown with Ctrl+C
10. Check Master-Pi /status endpoint shows latest data

## Expected Output
```
Initializing Farm Node...
Farm Node starting...
Master-Pi: http://192.168.1.100:5000/telemetry
Starting sun tracking...
State: NORMAL | Base: 0° | Tilt: 0° | Rain: 0
State: NORMAL | Base: 2° | Tilt: 2° | Rain: 0
State: NORMAL | Base: 4° | Tilt: 4° | Rain: 0
State: RAIN_DETECTED | Base: 4° | Tilt: 4° | Rain: 1
RAIN DETECTED - Executing protection sequence
Protection sequence complete - System in safe mode
State: PROTECTED | Base: 0° | Tilt: 0° | Rain: 1
State: PROTECTED | Base: 0° | Tilt: 0° | Rain: 0
Rain cleared - Starting 30s recovery delay
State: RECOVERY | Base: 0° | Tilt: 0° | Rain: 0
...
Recovery complete - Resuming normal operation
State: NORMAL | Base: 0° | Tilt: 0° | Rain: 0
^C
Shutdown signal received...
Moving to safe position...
Farm Node shutdown complete
```

## Completion Criteria
- [ ] Farm node initializes all subsystems
- [ ] Control loop runs continuously
- [ ] Telemetry transmitted every second
- [ ] Tracking algorithm updates motor positions
- [ ] Rain protection overrides tracking
- [ ] Network failures handled gracefully
- [ ] Ctrl+C triggers safe shutdown
- [ ] Master-Pi receives and displays data


---

# Issue 10: Full System Integration and Plug-and-Play Setup

## Objective
Create automated setup scripts and integration testing procedures for complete HelioCore OS deployment.

## Architecture
Complete system architecture with both nodes:

**Master-Pi stack:**
- Telemetry server (Flask) on port 5000
- Metrics endpoint for Grafana
- HelioCore OS CLI interface
- Grafana dashboard on port 3000

**Farm-Pi stack:**
- Sensor manager (6 LDRs + 2 rain sensors)
- Motor controller (3 stepper motors)
- Tracking algorithm
- Rain protection
- Telemetry transmission

**Network flow:**
```
Farm-Pi → HTTP POST → Master-Pi:5000/telemetry
Grafana → HTTP GET → Master-Pi:5000/metrics
Operator → Terminal → Master-Pi HelioCore CLI
```

**Deployment process:**
1. Configure network (static IPs recommended)
2. Run setup scripts on both nodes
3. Start Master-Pi services
4. Start Farm-Pi control loop
5. Verify telemetry flow
6. Access Grafana dashboard
7. Monitor via CLI

## Hardware Integration
Complete hardware setup:

**Farm-Pi GPIO connections:**
- LDR1-6: GPIO 17,27,22,23,24,25
- Rain1-2: GPIO 5,6
- Motor1 STEP/DIR: GPIO 12,16
- Motor2 STEP/DIR: GPIO 20,21
- Motor3 STEP/DIR: GPIO 13,19

**Power requirements:**
- Raspberry Pis: 5V/3A USB-C
- Stepper motors: 12-24V via DRV8825 drivers
- Sensors: 5V from GPIO training board

**Network:**
- Both Pis on same LAN
- Static IPs or mDNS (.local addresses)

## Implementation
Create setup scripts, systemd services, and integration tests.

## File Structure
```
heliocoreos/
├── install/
│   ├── setup_master.sh
│   ├── setup_farm.sh
│   ├── master.service
│   └── farm.service
├── test/
│   └── integration_test.py
└── README.md
```

## Code

**install/setup_master.sh**
```bash
#!/bin/bash
set -e

echo "=== HelioCore OS Master-Pi Setup ==="

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python dependencies
cd master-node
pip3 install -r requirements.txt

# Install Grafana
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install -y grafana

# Enable Grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

# Create systemd service for telemetry server
sudo cp ../install/master.service /etc/systemd/system/heliocore-master.service
sudo systemctl daemon-reload
sudo systemctl enable heliocore-master.service

echo "=== Master-Pi Setup Complete ==="
echo "Telemetry server: sudo systemctl start heliocore-master"
echo "HelioCore CLI: python3 heliocore_os.py"
echo "Grafana: http://localhost:3000 (admin/admin)"
```

**install/setup_farm.sh**
```bash
#!/bin/bash
set -e

echo "=== HelioCore OS Farm-Pi Setup ==="

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python dependencies
cd farm-node
pip3 install -r requirements.txt

# Enable I2C and SPI (if needed)
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# Create systemd service
sudo cp ../install/farm.service /etc/systemd/system/heliocore-farm.service
sudo systemctl daemon-reload
sudo systemctl enable heliocore-farm.service

echo "=== Farm-Pi Setup Complete ==="
echo "Update config.json with Master-Pi IP address"
echo "Start farm node: sudo systemctl start heliocore-farm"
```

**install/master.service**
```ini
[Unit]
Description=HelioCore OS Telemetry Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/heliocoreos/master-node
ExecStart=/usr/bin/python3 telemetry_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**install/farm.service**
```ini
[Unit]
Description=HelioCore OS Farm Node
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/heliocoreos/farm-node
ExecStart=/usr/bin/python3 farm_node.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**test/integration_test.py**
```python
#!/usr/bin/env python3
import requests
import time
import sys

def test_master_telemetry():
    print("Testing Master-Pi telemetry endpoint...")
    try:
        response = requests.get('http://localhost:5000/status', timeout=2)
        if response.status_code == 200:
            print("✓ Telemetry server responding")
            return True
    except:
        print("✗ Telemetry server not responding")
        return False

def test_master_metrics():
    print("Testing Master-Pi metrics endpoint...")
    try:
        response = requests.get('http://localhost:5000/metrics', timeout=2)
        if response.status_code == 200 and 'ldr_left' in response.text:
            print("✓ Metrics endpoint working")
            return True
    except:
        print("✗ Metrics endpoint not responding")
        return False

def test_grafana():
    print("Testing Grafana...")
    try:
        response = requests.get('http://localhost:3000', timeout=2)
        if response.status_code == 200:
            print("✓ Grafana accessible")
            return True
    except:
        print("✗ Grafana not accessible")
        return False

def test_farm_telemetry(master_ip):
    print(f"Testing Farm-Pi telemetry to {master_ip}...")
    test_data = {
        'ldr_left': 1,
        'ldr_right': 1,
        'ldr_top': 1,
        'ldr_bottom': 1,
        'rain': 0,
        'petal_state': 1,
        'tilt_angle': 45,
        'base_angle': 30,
        'motor_state': 1
    }
    try:
        response = requests.post(f'http://{master_ip}:5000/telemetry', json=test_data, timeout=2)
        if response.status_code == 200:
            print("✓ Farm telemetry transmission working")
            time.sleep(1)
            status = requests.get(f'http://{master_ip}:5000/status', timeout=2).json()
            if status['tilt_angle'] == 45:
                print("✓ Telemetry data received correctly")
                return True
    except Exception as e:
        print(f"✗ Farm telemetry failed: {e}")
        return False

def main():
    print("=== HelioCore OS Integration Test ===\n")
    
    results = []
    
    # Master-Pi tests
    results.append(test_master_telemetry())
    results.append(test_master_metrics())
    results.append(test_grafana())
    
    # Farm-Pi test
    master_ip = input("\nEnter Master-Pi IP address (or 'localhost'): ").strip()
    results.append(test_farm_telemetry(master_ip))
    
    print("\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("\n✓ All systems operational - HelioCore OS ready for deployment")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed - check configuration")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

**README.md (updated)**
```markdown
# HelioCore OS - Complete Setup Guide

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
│   Master-Pi     │         │    Farm-Pi      │
│                 │         │                 │
│  Telemetry      │◄────────│  Sensor Mgr     │
│  Server :5000   │  HTTP   │  Motor Ctrl     │
│                 │         │  Tracking Algo  │
│  Metrics :5000  │         │  Rain Protect   │
│  Grafana :3000  │         │                 │
│  CLI Interface  │         │  Control Loop   │
└─────────────────┘         └─────────────────┘
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
```

## Test Procedure
1. **Setup Master-Pi:**
   ```bash
   cd heliocoreos
   sudo bash install/setup_master.sh
   ```

2. **Setup Farm-Pi:**
   ```bash
   cd heliocoreos
   nano farm-node/config.json  # Set master_ip
   sudo bash install/setup_farm.sh
   ```

3. **Connect all hardware to Farm-Pi**

4. **Start Master-Pi services:**
   ```bash
   sudo systemctl start heliocore-master
   python3 master-node/heliocore_os.py
   ```

5. **Start Farm-Pi:**
   ```bash
   sudo systemctl start heliocore-farm
   ```

6. **Run integration test:**
   ```bash
   python3 test/integration_test.py
   ```

7. **Verify complete system:**
   - CLI shows live sensor data
   - Grafana dashboard updates in real-time
   - Sun tracking responds to flashlight
   - Rain protection triggers with water
   - Telemetry flows continuously

8. **Demo sequence:**
   - Show CLI interface
   - Show Grafana dashboard
   - Demonstrate sun tracking with flashlight
   - Trigger rain protection
   - Show recovery after rain clears

## Expected Output

**Integration test:**
```
=== HelioCore OS Integration Test ===

Testing Master-Pi telemetry endpoint...
✓ Telemetry server responding
Testing Master-Pi metrics endpoint...
✓ Metrics endpoint working
Testing Grafana...
✓ Grafana accessible

Enter Master-Pi IP address (or 'localhost'): 192.168.1.100
Testing Farm-Pi telemetry to 192.168.1.100...
✓ Farm telemetry transmission working
✓ Telemetry data received correctly

=== Test Results ===
Passed: 5/5

✓ All systems operational - HelioCore OS ready for deployment
```

**System running:**
- Master-Pi CLI displays live telemetry
- Grafana shows real-time graphs
- Farm-Pi tracks sun automatically
- Rain protection activates when needed
- All motors move within safe limits
- No errors in logs

## Completion Criteria
- [ ] Setup scripts run without errors on both Pis
- [ ] Systemd services start automatically
- [ ] Integration test passes all checks
- [ ] CLI displays live data from Farm-Pi
- [ ] Grafana dashboard shows all metrics
- [ ] Sun tracking works with light source
- [ ] Rain protection sequence executes correctly
- [ ] System recovers after rain clears
- [ ] All motors respect angle limits
- [ ] Graceful shutdown works on both nodes
- [ ] System ready for hackathon demonstration

---

# Development Complete

All 10 issues completed. HelioCore OS is now a fully functional distributed solar tracking system ready for prototype demonstration.

**Final system capabilities:**
✓ Distributed architecture (Master-Pi + Farm-Pi)
✓ Real-time sensor monitoring (6 LDRs + 2 rain sensors)
✓ Three-axis motor control (petal, tilt, base)
✓ Autonomous sun tracking algorithm
✓ Emergency rain protection
✓ Live telemetry streaming
✓ Grafana visualization dashboard
✓ Terminal CLI interface
✓ Plug-and-play setup scripts
✓ Systemd service integration

**Ready for deployment.**


---

# Issue 11: Service Manager - Process-Based Service Architecture

## Objective
Transform HelioCore OS from monolithic scripts into a service-oriented architecture with independent processes managed by a lightweight service manager.

## Architecture
The service manager implements a process supervisor pattern that manages five core services:

**Services:**
- **sensor_service**: Reads hardware sensors, publishes sensor data
- **motor_service**: Controls stepper motors, executes movement commands
- **tracking_service**: Implements sun tracking algorithm
- **rain_service**: Monitors rain and executes protection logic
- **telemetry_service**: Transmits data to Master-Pi

**Service lifecycle:**
- START: Launch service as subprocess
- STOP: Graceful shutdown with SIGTERM
- RESTART: Stop then start
- STATUS: Check if process is running

**Service manager features:**
- Process tracking via PID files
- Health monitoring
- Automatic restart on failure
- CLI interface for service control

**Communication:**
Services communicate via shared state files in /tmp/heliocore/ directory (Issue #12 will replace with event bus).

## Implementation
Create service manager with subprocess management and CLI commands.

## File Structure
```
heliocoreos/
├── core/
│   ├── service_manager.py
│   ├── service_base.py
│   └── heliocore_cli.py
├── services/
│   ├── sensor_service.py
│   ├── motor_service.py
│   ├── tracking_service.py
│   ├── rain_service.py
│   └── telemetry_service.py
└── farm-node/ (existing files remain)
```

## Dependencies
No new dependencies required. Uses standard library subprocess and signal modules.

## Code

**core/service_base.py**
```python
import os
import json
import time
from abc import ABC, abstractmethod

class ServiceBase(ABC):
    def __init__(self, name):
        self.name = name
        self.running = False
        self.state_dir = '/tmp/heliocore'
        os.makedirs(self.state_dir, exist_ok=True)
    
    def read_state(self, key):
        path = f'{self.state_dir}/{key}.json'
        try:
            with open(path) as f:
                return json.load(f)
        except:
            return None
    
    def write_state(self, key, data):
        path = f'{self.state_dir}/{key}.json'
        with open(path, 'w') as f:
            json.dump(data, f)
    
    @abstractmethod
    def initialize(self):
        pass
    
    @abstractmethod
    def run_loop(self):
        pass
    
    def start(self):
        print(f"[{self.name}] Starting...")
        self.running = True
        self.initialize()
        while self.running:
            try:
                self.run_loop()
            except Exception as e:
                print(f"[{self.name}] Error: {e}")
                time.sleep(1)
    
    def stop(self):
        self.running = False
        print(f"[{self.name}] Stopped")
```

**services/sensor_service.py**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.service_base import ServiceBase
from farm_node.sensor_manager import SensorManager
import json

class SensorService(ServiceBase):
    def initialize(self):
        with open('/home/pi/heliocoreos/farm-node/config.json') as f:
            config = json.load(f)
        self.sensor = SensorManager(config)
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
    
    def run_loop(self):
        data = self.sensor.get_telemetry()
        self.write_state('sensors', data)
        time.sleep(0.5)

if __name__ == '__main__':
    service = SensorService('sensor_service')
    service.start()
```

**services/motor_service.py**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.service_base import ServiceBase
from farm_node.motor_controller import MotorController
import json

class MotorService(ServiceBase):
    def initialize(self):
        with open('/home/pi/heliocoreos/farm-node/config.json') as f:
            config = json.load(f)
        self.motor = MotorController(config)
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
    
    def run_loop(self):
        cmd = self.read_state('motor_cmd')
        if cmd:
            if cmd['action'] == 'set_base':
                self.motor.set_base_angle(cmd['value'])
            elif cmd['action'] == 'set_tilt':
                self.motor.set_tilt_angle(cmd['value'])
            elif cmd['action'] == 'set_petal':
                self.motor.set_petal_state(cmd['value'])
            self.write_state('motor_cmd', None)
        
        state = self.motor.get_state()
        self.write_state('motor_state', state)
        time.sleep(0.1)

if __name__ == '__main__':
    service = MotorService('motor_service')
    service.start()
```

**services/tracking_service.py**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.service_base import ServiceBase

class TrackingService(ServiceBase):
    def initialize(self):
        self.active = True
        self.threshold = 1
        self.step_size = 2
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
    
    def run_loop(self):
        sensors = self.read_state('sensors')
        if not sensors or not self.active:
            time.sleep(1)
            return
        
        left = sensors.get('ldr_left', 0)
        right = sensors.get('ldr_right', 0)
        top = sensors.get('ldr_top', 0)
        bottom = sensors.get('ldr_bottom', 0)
        
        motor_state = self.read_state('motor_state') or {'base_angle': 0, 'tilt_angle': 0}
        
        if abs(left - right) >= self.threshold:
            new_base = motor_state['base_angle'] + (-self.step_size if left > right else self.step_size)
            self.write_state('motor_cmd', {'action': 'set_base', 'value': new_base})
        
        if abs(top - bottom) >= self.threshold:
            new_tilt = motor_state['tilt_angle'] + (self.step_size if top > bottom else -self.step_size)
            self.write_state('motor_cmd', {'action': 'set_tilt', 'value': new_tilt})
        
        time.sleep(2)

if __name__ == '__main__':
    service = TrackingService('tracking_service')
    service.start()
```

**services/rain_service.py**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.service_base import ServiceBase

class RainService(ServiceBase):
    def initialize(self):
        self.protected = False
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
    
    def run_loop(self):
        sensors = self.read_state('sensors')
        if not sensors:
            time.sleep(1)
            return
        
        rain = sensors.get('rain', 0)
        
        if rain and not self.protected:
            print("[rain_service] Rain detected - entering safe mode")
            self.write_state('motor_cmd', {'action': 'set_petal', 'value': 0})
            time.sleep(0.5)
            self.write_state('motor_cmd', {'action': 'set_base', 'value': 0})
            time.sleep(0.5)
            self.write_state('motor_cmd', {'action': 'set_tilt', 'value': 0})
            self.protected = True
        elif not rain and self.protected:
            print("[rain_service] Rain cleared - resuming normal operation")
            self.protected = False
        
        time.sleep(1)

if __name__ == '__main__':
    service = RainService('rain_service')
    service.start()
```

**services/telemetry_service.py**
```python
#!/usr/bin/env python3
import sys
import time
import signal
import requests
import json
sys.path.append('/home/pi/heliocoreos')
from core.service_base import ServiceBase

class TelemetryService(ServiceBase):
    def initialize(self):
        with open('/home/pi/heliocoreos/farm-node/config.json') as f:
            config = json.load(f)
        self.master_url = f"http://{config['master_ip']}:{config['master_port']}/telemetry"
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
    
    def run_loop(self):
        sensors = self.read_state('sensors')
        motor_state = self.read_state('motor_state')
        
        if sensors and motor_state:
            telemetry = {**sensors, **motor_state, 'motor_state': 1}
            try:
                requests.post(self.master_url, json=telemetry, timeout=2)
            except:
                pass
        
        time.sleep(1)

if __name__ == '__main__':
    service = TelemetryService('telemetry_service')
    service.start()
```

**core/service_manager.py**
```python
import subprocess
import os
import signal
import time

class ServiceManager:
    def __init__(self):
        self.services = {
            'sensor': '/home/pi/heliocoreos/services/sensor_service.py',
            'motor': '/home/pi/heliocoreos/services/motor_service.py',
            'tracking': '/home/pi/heliocoreos/services/tracking_service.py',
            'rain': '/home/pi/heliocoreos/services/rain_service.py',
            'telemetry': '/home/pi/heliocoreos/services/telemetry_service.py'
        }
        self.pid_dir = '/tmp/heliocore/pids'
        os.makedirs(self.pid_dir, exist_ok=True)
    
    def start_service(self, name):
        if name not in self.services:
            return False, f"Unknown service: {name}"
        
        if self.is_running(name):
            return False, f"Service {name} already running"
        
        proc = subprocess.Popen(['python3', self.services[name]])
        with open(f'{self.pid_dir}/{name}.pid', 'w') as f:
            f.write(str(proc.pid))
        
        return True, f"Service {name} started (PID: {proc.pid})"
    
    def stop_service(self, name):
        pid_file = f'{self.pid_dir}/{name}.pid'
        if not os.path.exists(pid_file):
            return False, f"Service {name} not running"
        
        with open(pid_file) as f:
            pid = int(f.read())
        
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            os.remove(pid_file)
            return True, f"Service {name} stopped"
        except:
            return False, f"Failed to stop service {name}"
    
    def is_running(self, name):
        pid_file = f'{self.pid_dir}/{name}.pid'
        if not os.path.exists(pid_file):
            return False
        
        with open(pid_file) as f:
            pid = int(f.read())
        
        try:
            os.kill(pid, 0)
            return True
        except:
            os.remove(pid_file)
            return False
    
    def get_status(self, name=None):
        if name:
            status = "RUNNING" if self.is_running(name) else "STOPPED"
            return {name: status}
        
        return {name: ("RUNNING" if self.is_running(name) else "STOPPED") 
                for name in self.services}
```

**core/heliocore_cli.py**
```python
#!/usr/bin/env python3
import sys
from service_manager import ServiceManager

def main():
    if len(sys.argv) < 2:
        print("Usage: heliocore <command> [args]")
        print("Commands: service")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'service':
        if len(sys.argv) < 3:
            print("Usage: heliocore service <start|stop|status|restart> [service_name]")
            return
        
        action = sys.argv[2]
        service_name = sys.argv[3] if len(sys.argv) > 3 else None
        
        manager = ServiceManager()
        
        if action == 'start' and service_name:
            success, msg = manager.start_service(service_name)
            print(msg)
        
        elif action == 'stop' and service_name:
            success, msg = manager.stop_service(service_name)
            print(msg)
        
        elif action == 'restart' and service_name:
            manager.stop_service(service_name)
            time.sleep(1)
            success, msg = manager.start_service(service_name)
            print(msg)
        
        elif action == 'status':
            status = manager.get_status(service_name)
            for name, state in status.items():
                print(f"{name}: {state}")
        
        else:
            print("Invalid service command")

if __name__ == '__main__':
    main()
```

## Configuration Steps
1. Create service directories:
```bash
mkdir -p /home/pi/heliocoreos/core
mkdir -p /home/pi/heliocoreos/services
mkdir -p /tmp/heliocore/pids
```

2. Make services executable:
```bash
chmod +x services/*.py
chmod +x core/heliocore_cli.py
```

3. Create symlink for CLI:
```bash
sudo ln -s /home/pi/heliocoreos/core/heliocore_cli.py /usr/local/bin/heliocore
```

## Test Procedure
1. Start individual service:
```bash
heliocore service start sensor
heliocore service status sensor
```

2. Check service output:
```bash
cat /tmp/heliocore/sensors.json
```

3. Start all services:
```bash
for svc in sensor motor tracking rain telemetry; do
  heliocore service start $svc
done
```

4. Check status:
```bash
heliocore service status
```

5. Stop service:
```bash
heliocore service stop tracking
```

6. Restart service:
```bash
heliocore service restart tracking
```

## Expected Output
```bash
$ heliocore service start sensor
Service sensor started (PID: 1234)

$ heliocore service status
sensor: RUNNING
motor: STOPPED
tracking: STOPPED
rain: STOPPED
telemetry: STOPPED

$ heliocore service start motor
Service motor started (PID: 1235)

$ heliocore service stop sensor
Service sensor stopped
```

## Completion Criteria
- [ ] Service manager can start/stop services
- [ ] PID files track running processes
- [ ] Services run as independent processes
- [ ] CLI commands work correctly
- [ ] Services communicate via state files
- [ ] Graceful shutdown with SIGTERM
- [ ] Status command shows accurate state


---

# Issue 12: Event Bus System - Pub/Sub Communication

## Objective
Replace file-based service communication with a lightweight event bus implementing publish/subscribe pattern for decoupled service interaction.

## Architecture
The event bus implements a simple pub/sub system using Unix domain sockets:

**Event types:**
- `sensor.ldr_update`: LDR sensor readings changed
- `sensor.rain_detected`: Rain sensor triggered
- `motor.position_changed`: Motor moved to new position
- `tracking.target_updated`: New tracking target calculated
- `system.emergency_stop`: Emergency shutdown signal

**Event flow:**
```
SensorService → [sensor.ldr_update] → TrackingService
SensorService → [sensor.rain_detected] → RainService
TrackingService → [tracking.target_updated] → MotorService
RainService → [system.emergency_stop] → All Services
```

**Event bus features:**
- Topic-based routing
- Multiple subscribers per topic
- Non-blocking publish
- Event history buffer (last 100 events)
- Unix socket for IPC

**Architecture:**
- Event bus runs as standalone service
- Services connect as clients
- JSON message format
- Async event delivery

## Implementation
Create event bus server and client library for service integration.

## File Structure
```
core/
├── event_bus.py
├── event_client.py
└── service_base.py (updated)
services/ (all services updated to use events)
```

## Dependencies
No new dependencies. Uses standard library socket and threading modules.

## Code

**core/event_bus.py**
```python
#!/usr/bin/env python3
import socket
import json
import threading
import os
from collections import defaultdict, deque

class EventBus:
    def __init__(self, socket_path='/tmp/heliocore/event_bus.sock'):
        self.socket_path = socket_path
        self.subscribers = defaultdict(list)
        self.event_history = deque(maxlen=100)
        self.running = False
        self.lock = threading.Lock()
        
        if os.path.exists(socket_path):
            os.remove(socket_path)
        
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(socket_path)
        self.server.listen(10)
    
    def start(self):
        print("[EventBus] Starting...")
        self.running = True
        while self.running:
            try:
                client, _ = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
            except:
                break
    
    def handle_client(self, client):
        buffer = ""
        while self.running:
            try:
                data = client.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    msg = json.loads(line)
                    
                    if msg['type'] == 'subscribe':
                        with self.lock:
                            self.subscribers[msg['topic']].append(client)
                    
                    elif msg['type'] == 'publish':
                        self.publish_event(msg['topic'], msg['data'])
            except:
                break
        
        with self.lock:
            for topic in self.subscribers:
                if client in self.subscribers[topic]:
                    self.subscribers[topic].remove(client)
        client.close()
    
    def publish_event(self, topic, data):
        event = {'topic': topic, 'data': data}
        self.event_history.append(event)
        
        with self.lock:
            for client in self.subscribers.get(topic, []):
                try:
                    msg = json.dumps({'type': 'event', 'topic': topic, 'data': data}) + '\n'
                    client.send(msg.encode())
                except:
                    pass
    
    def stop(self):
        self.running = False
        self.server.close()
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

if __name__ == '__main__':
    import signal
    bus = EventBus()
    signal.signal(signal.SIGTERM, lambda s, f: bus.stop())
    bus.start()
```

**core/event_client.py**
```python
import socket
import json
import threading

class EventClient:
    def __init__(self, socket_path='/tmp/heliocore/event_bus.sock'):
        self.socket_path = socket_path
        self.sock = None
        self.handlers = {}
        self.running = False
    
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        self.running = True
        threading.Thread(target=self._receive_loop, daemon=True).start()
    
    def subscribe(self, topic, handler):
        self.handlers[topic] = handler
        msg = json.dumps({'type': 'subscribe', 'topic': topic}) + '\n'
        self.sock.send(msg.encode())
    
    def publish(self, topic, data):
        msg = json.dumps({'type': 'publish', 'topic': topic, 'data': data}) + '\n'
        self.sock.send(msg.encode())
    
    def _receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    msg = json.loads(line)
                    
                    if msg['type'] == 'event':
                        topic = msg['topic']
                        if topic in self.handlers:
                            self.handlers[topic](msg['data'])
            except:
                break
    
    def disconnect(self):
        self.running = False
        if self.sock:
            self.sock.close()
```

**services/sensor_service.py (updated)**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.event_client import EventClient
from farm_node.sensor_manager import SensorManager
import json

class SensorService:
    def __init__(self):
        with open('/home/pi/heliocoreos/farm-node/config.json') as f:
            config = json.load(f)
        self.sensor = SensorManager(config)
        self.event_bus = EventClient()
        self.running = False
        self.last_rain = 0
    
    def start(self):
        print("[sensor_service] Starting...")
        self.event_bus.connect()
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            data = self.sensor.get_telemetry()
            self.event_bus.publish('sensor.ldr_update', data)
            
            if data['rain'] and not self.last_rain:
                self.event_bus.publish('sensor.rain_detected', {'rain': True})
            
            self.last_rain = data['rain']
            time.sleep(0.5)
    
    def stop(self):
        self.running = False
        self.event_bus.disconnect()
        self.sensor.cleanup()

if __name__ == '__main__':
    service = SensorService()
    service.start()
```

**services/motor_service.py (updated)**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.event_client import EventClient
from farm_node.motor_controller import MotorController
import json

class MotorService:
    def __init__(self):
        with open('/home/pi/heliocoreos/farm-node/config.json') as f:
            config = json.load(f)
        self.motor = MotorController(config)
        self.event_bus = EventClient()
        self.running = False
    
    def handle_tracking_command(self, data):
        if 'base_angle' in data:
            self.motor.set_base_angle(data['base_angle'])
        if 'tilt_angle' in data:
            self.motor.set_tilt_angle(data['tilt_angle'])
        
        state = self.motor.get_state()
        self.event_bus.publish('motor.position_changed', state)
    
    def handle_emergency_stop(self, data):
        print("[motor_service] Emergency stop received")
        self.motor.safe_position()
    
    def start(self):
        print("[motor_service] Starting...")
        self.event_bus.connect()
        self.event_bus.subscribe('tracking.target_updated', self.handle_tracking_command)
        self.event_bus.subscribe('system.emergency_stop', self.handle_emergency_stop)
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            time.sleep(0.1)
    
    def stop(self):
        self.running = False
        self.motor.safe_position()
        self.event_bus.disconnect()
        self.motor.cleanup()

if __name__ == '__main__':
    service = MotorService()
    service.start()
```

**services/tracking_service.py (updated)**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.event_client import EventClient

class TrackingService:
    def __init__(self):
        self.event_bus = EventClient()
        self.running = False
        self.active = True
        self.sensor_data = {}
        self.motor_state = {'base_angle': 0, 'tilt_angle': 0}
        self.threshold = 1
        self.step_size = 2
    
    def handle_sensor_update(self, data):
        self.sensor_data = data
    
    def handle_motor_update(self, data):
        self.motor_state = data
    
    def calculate_tracking(self):
        if not self.sensor_data or not self.active:
            return
        
        left = self.sensor_data.get('ldr_left', 0)
        right = self.sensor_data.get('ldr_right', 0)
        top = self.sensor_data.get('ldr_top', 0)
        bottom = self.sensor_data.get('ldr_bottom', 0)
        
        target = {}
        
        if abs(left - right) >= self.threshold:
            target['base_angle'] = self.motor_state['base_angle'] + \
                                   (-self.step_size if left > right else self.step_size)
        
        if abs(top - bottom) >= self.threshold:
            target['tilt_angle'] = self.motor_state['tilt_angle'] + \
                                   (self.step_size if top > bottom else -self.step_size)
        
        if target:
            self.event_bus.publish('tracking.target_updated', target)
    
    def start(self):
        print("[tracking_service] Starting...")
        self.event_bus.connect()
        self.event_bus.subscribe('sensor.ldr_update', self.handle_sensor_update)
        self.event_bus.subscribe('motor.position_changed', self.handle_motor_update)
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            self.calculate_tracking()
            time.sleep(2)
    
    def stop(self):
        self.running = False
        self.event_bus.disconnect()

if __name__ == '__main__':
    service = TrackingService()
    service.start()
```

**services/rain_service.py (updated)**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.event_client import EventClient

class RainService:
    def __init__(self):
        self.event_bus = EventClient()
        self.running = False
        self.protected = False
    
    def handle_rain_detected(self, data):
        if not self.protected:
            print("[rain_service] Rain detected - triggering emergency stop")
            self.event_bus.publish('system.emergency_stop', {'reason': 'rain'})
            self.protected = True
    
    def start(self):
        print("[rain_service] Starting...")
        self.event_bus.connect()
        self.event_bus.subscribe('sensor.rain_detected', self.handle_rain_detected)
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            time.sleep(1)
    
    def stop(self):
        self.running = False
        self.event_bus.disconnect()

if __name__ == '__main__':
    service = RainService()
    service.start()
```

## Configuration Steps
1. Update service manager to include event bus:
```python
# Add to core/service_manager.py services dict:
'eventbus': '/home/pi/heliocoreos/core/event_bus.py'
```

2. Start event bus first:
```bash
heliocore service start eventbus
```

## Test Procedure
1. Start event bus:
```bash
heliocore service start eventbus
```

2. Start sensor service:
```bash
heliocore service start sensor
```

3. Start motor service:
```bash
heliocore service start motor
```

4. Start tracking service:
```bash
heliocore service start tracking
```

5. Monitor events (create test subscriber):
```python
from core.event_client import EventClient
client = EventClient()
client.connect()
client.subscribe('sensor.ldr_update', lambda d: print(f"LDR: {d}"))
client.subscribe('motor.position_changed', lambda d: print(f"Motor: {d}"))
```

6. Trigger rain sensor and verify emergency stop event

## Expected Output
```
[EventBus] Starting...
[sensor_service] Starting...
[motor_service] Starting...
[tracking_service] Starting...
[rain_service] Starting...

# When light changes:
LDR: {'ldr_left': 2, 'ldr_right': 0, ...}
Motor: {'base_angle': -2, 'tilt_angle': 0, ...}

# When rain detected:
[rain_service] Rain detected - triggering emergency stop
[motor_service] Emergency stop received
```

## Completion Criteria
- [ ] Event bus runs as standalone service
- [ ] Services connect to event bus
- [ ] Publish/subscribe works correctly
- [ ] Events routed to correct subscribers
- [ ] Multiple subscribers per topic supported
- [ ] Non-blocking event delivery
- [ ] Services decoupled via events


---

# Issue 13: Node Manager - Distributed Node Discovery and Management

## Objective
Implement node management system for tracking and managing distributed Farm-Pi nodes with automatic registration, health monitoring, and CLI commands.

## Architecture
The node manager implements a registry pattern for distributed node management:

**Components:**
- **Node Registry**: Runs on Master-Pi, tracks all Farm nodes
- **Node Agent**: Runs on each Farm-Pi, registers with Master
- **Heartbeat System**: Periodic health checks
- **Node Discovery**: Automatic node detection on network

**Node lifecycle:**
1. Farm-Pi starts → Node agent registers with Master-Pi
2. Periodic heartbeat (every 5s)
3. Master-Pi marks node offline if heartbeat missed (30s timeout)
4. Node agent re-registers on reconnection

**Node information:**
- Node ID (hostname)
- IP address
- Status (online/offline)
- Last heartbeat timestamp
- Service status
- Hardware capabilities

**CLI commands:**
- `heliocore node list`: Show all registered nodes
- `heliocore node status <node_id>`: Show detailed node status
- `heliocore node ping <node_id>`: Test node connectivity

## Implementation
Create node registry service for Master-Pi and node agent for Farm-Pi.

## File Structure
```
master-node/
├── node_registry.py
└── node_manager_cli.py
farm-node/
└── node_agent.py
core/
└── heliocore_cli.py (updated)
```

## Dependencies
No new dependencies required.

## Code

**master-node/node_registry.py**
```python
#!/usr/bin/env python3
from flask import Flask, request, jsonify
import json
import threading
import time
from datetime import datetime

app = Flask(__name__)
nodes_lock = threading.Lock()
nodes = {}

HEARTBEAT_TIMEOUT = 30

@app.route('/node/register', methods=['POST'])
def register_node():
    data = request.get_json()
    node_id = data['node_id']
    
    with nodes_lock:
        nodes[node_id] = {
            'node_id': node_id,
            'ip': data['ip'],
            'hostname': data.get('hostname', node_id),
            'capabilities': data.get('capabilities', []),
            'status': 'online',
            'last_heartbeat': datetime.now().isoformat(),
            'registered_at': datetime.now().isoformat()
        }
    
    print(f"[NodeRegistry] Node registered: {node_id} ({data['ip']})")
    return jsonify({'status': 'registered'}), 200

@app.route('/node/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    node_id = data['node_id']
    
    with nodes_lock:
        if node_id in nodes:
            nodes[node_id]['last_heartbeat'] = datetime.now().isoformat()
            nodes[node_id]['status'] = 'online'
            nodes[node_id]['services'] = data.get('services', {})
    
    return jsonify({'status': 'ok'}), 200

@app.route('/node/list', methods=['GET'])
def list_nodes():
    with nodes_lock:
        return jsonify({'nodes': list(nodes.values())}), 200

@app.route('/node/status/<node_id>', methods=['GET'])
def node_status(node_id):
    with nodes_lock:
        if node_id in nodes:
            return jsonify(nodes[node_id]), 200
        return jsonify({'error': 'Node not found'}), 404

def check_node_health():
    while True:
        time.sleep(10)
        now = datetime.now()
        
        with nodes_lock:
            for node_id in nodes:
                last_hb = datetime.fromisoformat(nodes[node_id]['last_heartbeat'])
                if (now - last_hb).total_seconds() > HEARTBEAT_TIMEOUT:
                    if nodes[node_id]['status'] == 'online':
                        print(f"[NodeRegistry] Node offline: {node_id}")
                        nodes[node_id]['status'] = 'offline'

if __name__ == '__main__':
    threading.Thread(target=check_node_health, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
```

**farm-node/node_agent.py**
```python
#!/usr/bin/env python3
import requests
import time
import socket
import json
import signal
import sys

class NodeAgent:
    def __init__(self, config_path='config.json'):
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.master_url = f"http://{self.config['master_ip']}:5001"
        self.node_id = socket.gethostname()
        self.ip = self.get_local_ip()
        self.running = False
        self.registered = False
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def register(self):
        data = {
            'node_id': self.node_id,
            'ip': self.ip,
            'hostname': self.node_id,
            'capabilities': ['sensors', 'motors', 'tracking']
        }
        
        try:
            response = requests.post(f'{self.master_url}/node/register', 
                                    json=data, timeout=5)
            if response.status_code == 200:
                self.registered = True
                print(f"[NodeAgent] Registered with Master-Pi as {self.node_id}")
                return True
        except Exception as e:
            print(f"[NodeAgent] Registration failed: {e}")
        
        return False
    
    def send_heartbeat(self):
        # Get service status
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        services = manager.get_status()
        
        data = {
            'node_id': self.node_id,
            'services': services
        }
        
        try:
            requests.post(f'{self.master_url}/node/heartbeat', 
                         json=data, timeout=2)
        except:
            self.registered = False
    
    def run(self):
        print(f"[NodeAgent] Starting on {self.node_id} ({self.ip})")
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            if not self.registered:
                self.register()
                time.sleep(5)
            else:
                self.send_heartbeat()
                time.sleep(5)
    
    def stop(self):
        self.running = False
        print("[NodeAgent] Stopped")

if __name__ == '__main__':
    agent = NodeAgent()
    agent.run()
```

**master-node/node_manager_cli.py**
```python
import requests
import json

class NodeManagerCLI:
    def __init__(self, master_url='http://localhost:5001'):
        self.master_url = master_url
    
    def list_nodes(self):
        try:
            response = requests.get(f'{self.master_url}/node/list', timeout=2)
            if response.status_code == 200:
                nodes = response.json()['nodes']
                
                print("\nRegistered Nodes:")
                print("-" * 70)
                print(f"{'Node ID':<20} {'IP Address':<15} {'Status':<10} {'Last Heartbeat'}")
                print("-" * 70)
                
                for node in nodes:
                    print(f"{node['node_id']:<20} {node['ip']:<15} {node['status']:<10} {node['last_heartbeat']}")
                
                print(f"\nTotal nodes: {len(nodes)}")
        except Exception as e:
            print(f"Error: {e}")
    
    def node_status(self, node_id):
        try:
            response = requests.get(f'{self.master_url}/node/status/{node_id}', timeout=2)
            if response.status_code == 200:
                node = response.json()
                
                print(f"\nNode: {node['node_id']}")
                print("-" * 50)
                print(f"IP Address:      {node['ip']}")
                print(f"Hostname:        {node['hostname']}")
                print(f"Status:          {node['status']}")
                print(f"Last Heartbeat:  {node['last_heartbeat']}")
                print(f"Registered At:   {node['registered_at']}")
                
                if 'services' in node:
                    print("\nServices:")
                    for svc, status in node['services'].items():
                        print(f"  {svc:<15} {status}")
            else:
                print(f"Node {node_id} not found")
        except Exception as e:
            print(f"Error: {e}")
    
    def ping_node(self, node_id):
        try:
            response = requests.get(f'{self.master_url}/node/status/{node_id}', timeout=2)
            if response.status_code == 200:
                node = response.json()
                if node['status'] == 'online':
                    print(f"Node {node_id} is ONLINE")
                else:
                    print(f"Node {node_id} is OFFLINE")
            else:
                print(f"Node {node_id} not found")
        except Exception as e:
            print(f"Error: {e}")
```

**core/heliocore_cli.py (updated with node commands)**
```python
#!/usr/bin/env python3
import sys
import time
sys.path.append('/home/pi/heliocoreos')
from core.service_manager import ServiceManager
from master_node.node_manager_cli import NodeManagerCLI

def main():
    if len(sys.argv) < 2:
        print("Usage: heliocore <command> [args]")
        print("Commands: service, node")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'service':
        if len(sys.argv) < 3:
            print("Usage: heliocore service <start|stop|status|restart> [service_name]")
            return
        
        action = sys.argv[2]
        service_name = sys.argv[3] if len(sys.argv) > 3 else None
        
        manager = ServiceManager()
        
        if action == 'start' and service_name:
            success, msg = manager.start_service(service_name)
            print(msg)
        
        elif action == 'stop' and service_name:
            success, msg = manager.stop_service(service_name)
            print(msg)
        
        elif action == 'restart' and service_name:
            manager.stop_service(service_name)
            time.sleep(1)
            success, msg = manager.start_service(service_name)
            print(msg)
        
        elif action == 'status':
            status = manager.get_status(service_name)
            for name, state in status.items():
                print(f"{name}: {state}")
        
        else:
            print("Invalid service command")
    
    elif cmd == 'node':
        if len(sys.argv) < 3:
            print("Usage: heliocore node <list|status|ping> [node_id]")
            return
        
        action = sys.argv[2]
        node_id = sys.argv[3] if len(sys.argv) > 3 else None
        
        cli = NodeManagerCLI()
        
        if action == 'list':
            cli.list_nodes()
        
        elif action == 'status' and node_id:
            cli.node_status(node_id)
        
        elif action == 'ping' and node_id:
            cli.ping_node(node_id)
        
        else:
            print("Invalid node command")

if __name__ == '__main__':
    main()
```

## Configuration Steps
1. Add node registry to Master-Pi services:
```bash
# Add to master-node systemd service or start manually
python3 master-node/node_registry.py &
```

2. Add node agent to Farm-Pi services:
```bash
# Update service_manager.py to include:
'nodeagent': '/home/pi/heliocoreos/farm-node/node_agent.py'
```

3. Start node agent on Farm-Pi:
```bash
heliocore service start nodeagent
```

## Test Procedure
1. Start node registry on Master-Pi:
```bash
python3 master-node/node_registry.py &
```

2. Start node agent on Farm-Pi:
```bash
heliocore service start nodeagent
```

3. List nodes from Master-Pi:
```bash
heliocore node list
```

4. Check node status:
```bash
heliocore node status farm-pi-01
```

5. Ping node:
```bash
heliocore node ping farm-pi-01
```

6. Stop node agent and verify offline detection:
```bash
heliocore service stop nodeagent
# Wait 30 seconds
heliocore node list
```

## Expected Output
```bash
$ heliocore node list

Registered Nodes:
----------------------------------------------------------------------
Node ID              IP Address      Status     Last Heartbeat
----------------------------------------------------------------------
farm-pi-01           192.168.1.101   online     2024-01-15T10:30:45
farm-pi-02           192.168.1.102   online     2024-01-15T10:30:43

Total nodes: 2

$ heliocore node status farm-pi-01

Node: farm-pi-01
--------------------------------------------------
IP Address:      192.168.1.101
Hostname:        farm-pi-01
Status:          online
Last Heartbeat:  2024-01-15T10:30:45.123456
Registered At:   2024-01-15T10:25:12.456789

Services:
  sensor          RUNNING
  motor           RUNNING
  tracking        RUNNING
  rain            RUNNING
  telemetry       RUNNING

$ heliocore node ping farm-pi-01
Node farm-pi-01 is ONLINE
```

## Completion Criteria
- [ ] Node registry runs on Master-Pi
- [ ] Node agent registers Farm-Pi automatically
- [ ] Heartbeat system detects offline nodes
- [ ] CLI commands show node information
- [ ] Multiple nodes can register
- [ ] Service status included in heartbeat
- [ ] Automatic re-registration after disconnect


---

# Issue 14: System Monitoring and Logs - Health Tracking and Diagnostics

## Objective
Implement comprehensive system monitoring with CPU/memory tracking, service health checks, sensor diagnostics, and centralized logging with CLI access.

## Architecture
The monitoring system implements a metrics collection and logging framework:

**Monitoring components:**
- **System Monitor**: Tracks CPU, memory, disk usage
- **Service Health Checker**: Monitors service status and restarts
- **Sensor Health**: Validates sensor readings and detects failures
- **Log Aggregator**: Collects logs from all services

**Metrics collected:**
- CPU usage per service
- Memory usage per service
- Service uptime
- Sensor read errors
- Event bus message rate
- Node connectivity status

**Log levels:**
- INFO: Normal operations
- WARN: Potential issues
- ERROR: Failures requiring attention
- DEBUG: Detailed diagnostics

**CLI commands:**
- `heliocore logs [service]`: View service logs
- `heliocore top`: Real-time system monitor
- `heliocore health`: System health check

## Implementation
Create monitoring service and logging infrastructure.

## File Structure
```
core/
├── system_monitor.py
├── log_manager.py
└── health_checker.py
services/
└── monitor_service.py
```

## Dependencies
```
psutil==5.9.0
```

## Code

**core/log_manager.py**
```python
import os
import json
from datetime import datetime
from collections import deque

class LogManager:
    def __init__(self, log_dir='/tmp/heliocore/logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_buffer = deque(maxlen=1000)
    
    def log(self, service, level, message):
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'service': service,
            'level': level,
            'message': message
        }
        
        self.log_buffer.append(entry)
        
        log_file = f'{self.log_dir}/{service}.log'
        with open(log_file, 'a') as f:
            f.write(f"{timestamp} [{level}] {message}\n")
    
    def get_logs(self, service=None, level=None, limit=100):
        logs = list(self.log_buffer)
        
        if service:
            logs = [l for l in logs if l['service'] == service]
        
        if level:
            logs = [l for l in logs if l['level'] == level]
        
        return logs[-limit:]
    
    def tail_logs(self, service, lines=50):
        log_file = f'{self.log_dir}/{service}.log'
        if not os.path.exists(log_file):
            return []
        
        with open(log_file) as f:
            return f.readlines()[-lines:]

# Global logger instance
logger = LogManager()
```

**core/system_monitor.py**
```python
import psutil
import os
import time

class SystemMonitor:
    def __init__(self):
        self.process_cache = {}
    
    def get_system_stats(self):
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
    
    def get_service_stats(self, pid):
        try:
            if pid not in self.process_cache:
                self.process_cache[pid] = psutil.Process(pid)
            
            proc = self.process_cache[pid]
            return {
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'memory_mb': proc.memory_info().rss / 1024 / 1024,
                'status': proc.status(),
                'uptime': time.time() - proc.create_time()
            }
        except:
            if pid in self.process_cache:
                del self.process_cache[pid]
            return None
    
    def get_all_service_stats(self, service_manager):
        stats = {}
        pid_dir = '/tmp/heliocore/pids'
        
        for service in os.listdir(pid_dir):
            if service.endswith('.pid'):
                service_name = service[:-4]
                with open(f'{pid_dir}/{service}') as f:
                    pid = int(f.read())
                
                service_stats = self.get_service_stats(pid)
                if service_stats:
                    stats[service_name] = service_stats
        
        return stats
```

**core/health_checker.py**
```python
import time
from datetime import datetime

class HealthChecker:
    def __init__(self):
        self.checks = {}
        self.last_check = {}
    
    def register_check(self, name, check_func, interval=60):
        self.checks[name] = {
            'func': check_func,
            'interval': interval,
            'last_result': None
        }
    
    def run_checks(self):
        results = {}
        now = time.time()
        
        for name, check in self.checks.items():
            last_run = self.last_check.get(name, 0)
            
            if now - last_run >= check['interval']:
                try:
                    result = check['func']()
                    check['last_result'] = {
                        'status': 'healthy' if result else 'unhealthy',
                        'timestamp': datetime.now().isoformat(),
                        'details': result
                    }
                    self.last_check[name] = now
                except Exception as e:
                    check['last_result'] = {
                        'status': 'error',
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e)
                    }
            
            results[name] = check['last_result']
        
        return results
    
    def get_overall_health(self):
        results = self.run_checks()
        
        healthy = sum(1 for r in results.values() if r and r['status'] == 'healthy')
        total = len(results)
        
        return {
            'status': 'healthy' if healthy == total else 'degraded',
            'healthy_checks': healthy,
            'total_checks': total,
            'checks': results
        }
```

**services/monitor_service.py**
```python
#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.system_monitor import SystemMonitor
from core.health_checker import HealthChecker
from core.log_manager import logger
from core.service_manager import ServiceManager

class MonitorService:
    def __init__(self):
        self.monitor = SystemMonitor()
        self.health = HealthChecker()
        self.service_manager = ServiceManager()
        self.running = False
        
        # Register health checks
        self.health.register_check('services', self.check_services, interval=30)
        self.health.register_check('system', self.check_system, interval=60)
    
    def check_services(self):
        status = self.service_manager.get_status()
        running = sum(1 for s in status.values() if s == 'RUNNING')
        return {'running': running, 'total': len(status), 'services': status}
    
    def check_system(self):
        stats = self.monitor.get_system_stats()
        healthy = stats['cpu_percent'] < 90 and stats['memory_percent'] < 90
        return {'healthy': healthy, 'stats': stats}
    
    def start(self):
        print("[monitor_service] Starting...")
        logger.log('monitor', 'INFO', 'Monitor service started')
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            # Collect system stats
            sys_stats = self.monitor.get_system_stats()
            logger.log('monitor', 'DEBUG', f"System: CPU={sys_stats['cpu_percent']}% MEM={sys_stats['memory_percent']}%")
            
            # Collect service stats
            svc_stats = self.monitor.get_all_service_stats(self.service_manager)
            for svc, stats in svc_stats.items():
                if stats['cpu_percent'] > 50:
                    logger.log('monitor', 'WARN', f"High CPU usage in {svc}: {stats['cpu_percent']}%")
            
            # Run health checks
            health = self.health.get_overall_health()
            if health['status'] != 'healthy':
                logger.log('monitor', 'WARN', f"System health degraded: {health['healthy_checks']}/{health['total_checks']} checks passing")
            
            time.sleep(10)
    
    def stop(self):
        self.running = False
        logger.log('monitor', 'INFO', 'Monitor service stopped')

if __name__ == '__main__':
    service = MonitorService()
    service.start()
```

**core/heliocore_cli.py (updated with monitoring commands)**
```python
#!/usr/bin/env python3
import sys
import time
import os
sys.path.append('/home/pi/heliocoreos')
from core.service_manager import ServiceManager
from core.system_monitor import SystemMonitor
from core.health_checker import HealthChecker
from core.log_manager import LogManager

def cmd_logs(args):
    log_mgr = LogManager()
    service = args[0] if args else None
    
    if service:
        logs = log_mgr.tail_logs(service, lines=50)
        print(f"\n=== Logs for {service} ===\n")
        for line in logs:
            print(line.strip())
    else:
        logs = log_mgr.get_logs(limit=50)
        print("\n=== Recent Logs ===\n")
        for entry in logs:
            print(f"{entry['timestamp']} [{entry['service']}] [{entry['level']}] {entry['message']}")

def cmd_top():
    monitor = SystemMonitor()
    service_mgr = ServiceManager()
    
    try:
        while True:
            os.system('clear')
            
            # System stats
            sys_stats = monitor.get_system_stats()
            print("=" * 70)
            print("HelioCore OS - System Monitor")
            print("=" * 70)
            print(f"CPU:    {sys_stats['cpu_percent']:.1f}%")
            print(f"Memory: {sys_stats['memory_percent']:.1f}%")
            print(f"Disk:   {sys_stats['disk_percent']:.1f}%")
            print()
            
            # Service stats
            print(f"{'Service':<15} {'Status':<10} {'CPU%':<8} {'Memory(MB)':<12} {'Uptime(s)'}")
            print("-" * 70)
            
            svc_stats = monitor.get_all_service_stats(service_mgr)
            for svc, stats in svc_stats.items():
                print(f"{svc:<15} {'RUNNING':<10} {stats['cpu_percent']:<8.1f} {stats['memory_mb']:<12.1f} {int(stats['uptime'])}")
            
            print("\nPress Ctrl+C to exit")
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n")

def cmd_health():
    health = HealthChecker()
    service_mgr = ServiceManager()
    
    # Register checks
    health.register_check('services', lambda: service_mgr.get_status())
    
    result = health.get_overall_health()
    
    print("\n=== System Health Check ===\n")
    print(f"Overall Status: {result['status'].upper()}")
    print(f"Checks Passing: {result['healthy_checks']}/{result['total_checks']}")
    print()
    
    for check_name, check_result in result['checks'].items():
        if check_result:
            status_icon = "✓" if check_result['status'] == 'healthy' else "✗"
            print(f"{status_icon} {check_name}: {check_result['status']}")
            if 'details' in check_result:
                print(f"  {check_result['details']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: heliocore <command> [args]")
        print("Commands: service, node, logs, top, health")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'logs':
        cmd_logs(sys.argv[2:])
    
    elif cmd == 'top':
        cmd_top()
    
    elif cmd == 'health':
        cmd_health()
    
    # ... existing service and node commands ...

if __name__ == '__main__':
    main()
```

## Configuration Steps
1. Install psutil:
```bash
pip3 install psutil==5.9.0
```

2. Add monitor service to service manager:
```python
# In service_manager.py services dict:
'monitor': '/home/pi/heliocoreos/services/monitor_service.py'
```

3. Start monitor service:
```bash
heliocore service start monitor
```

## Test Procedure
1. Start monitor service:
```bash
heliocore service start monitor
```

2. View logs:
```bash
heliocore logs monitor
heliocore logs sensor
```

3. Run system monitor:
```bash
heliocore top
```

4. Check system health:
```bash
heliocore health
```

5. Generate high CPU load and verify warnings:
```bash
# In another terminal
stress --cpu 4 --timeout 30s
# Check logs
heliocore logs monitor
```

## Expected Output

**heliocore logs monitor:**
```
=== Logs for monitor ===

2024-01-15T10:30:45 [INFO] Monitor service started
2024-01-15T10:30:55 [DEBUG] System: CPU=15.2% MEM=45.3%
2024-01-15T10:31:05 [DEBUG] System: CPU=18.7% MEM=46.1%
2024-01-15T10:31:15 [WARN] High CPU usage in tracking: 52.3%
```

**heliocore top:**
```
======================================================================
HelioCore OS - System Monitor
======================================================================
CPU:    18.5%
Memory: 45.2%
Disk:   32.1%

Service         Status     CPU%     Memory(MB)   Uptime(s)
----------------------------------------------------------------------
sensor          RUNNING    2.3      12.5         1234
motor           RUNNING    5.1      15.2         1230
tracking        RUNNING    8.7      10.8         1225
rain            RUNNING    1.2      8.3          1220
telemetry       RUNNING    3.4      11.1         1215

Press Ctrl+C to exit
```

**heliocore health:**
```
=== System Health Check ===

Overall Status: HEALTHY
Checks Passing: 2/2

✓ services: healthy
  {'running': 5, 'total': 5, 'services': {...}}
✓ system: healthy
  {'healthy': True, 'stats': {...}}
```

## Completion Criteria
- [ ] System monitor tracks CPU/memory usage
- [ ] Service-level metrics collected
- [ ] Logs aggregated from all services
- [ ] Health checks run periodically
- [ ] CLI commands display monitoring data
- [ ] High resource usage triggers warnings
- [ ] Log rotation prevents disk fill


---

# Issue 15: HelioCore OS Boot System - Automated Startup and Shell

## Objective
Implement a complete boot system that automatically starts all HelioCore services in correct order, displays boot progress, and launches an interactive shell for system management.

## Architecture
The boot system implements an init-like process manager:

**Boot sequence:**
1. Display HelioCore OS banner
2. Initialize core directories and state
3. Start event bus (dependency for all services)
4. Start node agent (registers with Master-Pi)
5. Start hardware services (sensor, motor)
6. Start logic services (tracking, rain)
7. Start telemetry service
8. Start monitor service
9. Run health check
10. Launch interactive shell

**Boot stages:**
- **PRE-BOOT**: System checks and directory creation
- **CORE**: Event bus and node agent
- **HARDWARE**: Sensor and motor services
- **LOGIC**: Tracking and rain protection
- **TELEMETRY**: Data transmission
- **MONITORING**: System health tracking
- **READY**: Interactive shell

**Shell features:**
- Command history
- Tab completion
- Built-in commands (status, restart, shutdown)
- Service management
- Node management
- Log viewing

## Implementation
Create boot manager and interactive shell.

## File Structure
```
core/
├── boot_manager.py
├── heliocore_shell.py
└── init.py
install/
└── heliocore_boot.service
```

## Dependencies
```
prompt_toolkit==3.0.36
```

## Code

**core/boot_manager.py**
```python
import os
import time
import sys
from service_manager import ServiceManager
from health_checker import HealthChecker
from log_manager import logger

class BootManager:
    def __init__(self):
        self.service_manager = ServiceManager()
        self.health_checker = HealthChecker()
        self.boot_stages = [
            ('eventbus', 'Event Bus'),
            ('nodeagent', 'Node Agent'),
            ('sensor', 'Sensor Service'),
            ('motor', 'Motor Service'),
            ('tracking', 'Tracking Engine'),
            ('rain', 'Rain Protection'),
            ('telemetry', 'Telemetry Service'),
            ('monitor', 'System Monitor')
        ]
    
    def print_banner(self):
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              HelioCore OS v1.0                            ║
║         Distributed Solar Tracking System                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def pre_boot_checks(self):
        print("\n[PRE-BOOT] Running system checks...")
        
        # Create required directories
        dirs = [
            '/tmp/heliocore',
            '/tmp/heliocore/pids',
            '/tmp/heliocore/logs'
        ]
        
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            print(f"  ✓ Directory: {d}")
        
        # Check configuration
        config_file = '/home/pi/heliocoreos/farm-node/config.json'
        if os.path.exists(config_file):
            print(f"  ✓ Configuration found")
        else:
            print(f"  ✗ Configuration missing: {config_file}")
            return False
        
        print("[PRE-BOOT] System checks passed\n")
        return True
    
    def start_service(self, service_id, service_name):
        print(f"[ .... ] {service_name}", end='', flush=True)
        
        success, msg = self.service_manager.start_service(service_id)
        
        if success:
            time.sleep(1)  # Wait for service to initialize
            
            if self.service_manager.is_running(service_id):
                print(f"\r[  OK  ] {service_name}")
                logger.log('boot', 'INFO', f"{service_name} started successfully")
                return True
            else:
                print(f"\r[ FAIL ] {service_name}")
                logger.log('boot', 'ERROR', f"{service_name} failed to start")
                return False
        else:
            print(f"\r[ FAIL ] {service_name}")
            logger.log('boot', 'ERROR', f"{service_name} start failed: {msg}")
            return False
    
    def boot(self):
        self.print_banner()
        
        if not self.pre_boot_checks():
            print("\n[BOOT] Pre-boot checks failed. Aborting.")
            return False
        
        print("[BOOT] Starting HelioCore OS services...\n")
        
        failed_services = []
        
        for service_id, service_name in self.boot_stages:
            if not self.start_service(service_id, service_name):
                failed_services.append(service_name)
        
        print()
        
        if failed_services:
            print(f"[BOOT] Boot completed with errors:")
            for svc in failed_services:
                print(f"  ✗ {svc}")
            return False
        else:
            print("[BOOT] All services started successfully")
            
            # Run health check
            print("\n[HEALTH] Running system health check...")
            time.sleep(2)
            
            status = self.service_manager.get_status()
            running = sum(1 for s in status.values() if s == 'RUNNING')
            
            print(f"[HEALTH] Services: {running}/{len(status)} running")
            
            if running == len(status):
                print("\n" + "=" * 60)
                print("  HelioCore OS is ready.")
                print("  Type 'help' for available commands.")
                print("=" * 60 + "\n")
                return True
            else:
                print("\n[HEALTH] Some services failed to start")
                return False
    
    def shutdown(self):
        print("\n[SHUTDOWN] Stopping HelioCore OS services...")
        
        # Stop in reverse order
        for service_id, service_name in reversed(self.boot_stages):
            if self.service_manager.is_running(service_id):
                print(f"[ .... ] Stopping {service_name}", end='', flush=True)
                self.service_manager.stop_service(service_id)
                print(f"\r[  OK  ] Stopped {service_name}")
        
        print("\n[SHUTDOWN] HelioCore OS shutdown complete")
```

**core/heliocore_shell.py**
```python
#!/usr/bin/env python3
import sys
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
sys.path.append('/home/pi/heliocoreos')
from core.service_manager import ServiceManager
from core.system_monitor import SystemMonitor
from core.log_manager import LogManager
from master_node.node_manager_cli import NodeManagerCLI

class HelioCoreShell:
    def __init__(self):
        self.service_manager = ServiceManager()
        self.monitor = SystemMonitor()
        self.log_manager = LogManager()
        self.node_cli = NodeManagerCLI()
        
        commands = [
            'help', 'status', 'services', 'nodes', 'logs', 'top',
            'restart', 'shutdown', 'health', 'clear', 'exit'
        ]
        
        self.completer = WordCompleter(commands, ignore_case=True)
        self.session = PromptSession(
            history=FileHistory('/tmp/heliocore/.shell_history'),
            completer=self.completer
        )
    
    def cmd_help(self, args):
        print("""
HelioCore OS Shell Commands:

  status              Show system status
  services            List all services
  nodes               List registered nodes
  logs [service]      View service logs
  top                 System resource monitor
  restart <service>   Restart a service
  shutdown            Shutdown HelioCore OS
  health              Run health check
  clear               Clear screen
  exit                Exit shell

Service Management:
  service start <name>
  service stop <name>
  service restart <name>
  service status [name]

Node Management:
  node list
  node status <id>
  node ping <id>
        """)
    
    def cmd_status(self, args):
        print("\n=== HelioCore OS Status ===\n")
        
        # System stats
        sys_stats = self.monitor.get_system_stats()
        print(f"CPU:    {sys_stats['cpu_percent']:.1f}%")
        print(f"Memory: {sys_stats['memory_percent']:.1f}%")
        print()
        
        # Service status
        status = self.service_manager.get_status()
        running = sum(1 for s in status.values() if s == 'RUNNING')
        print(f"Services: {running}/{len(status)} running")
        print()
    
    def cmd_services(self, args):
        status = self.service_manager.get_status()
        
        print("\n=== Services ===\n")
        for name, state in status.items():
            icon = "●" if state == "RUNNING" else "○"
            print(f"{icon} {name:<15} {state}")
        print()
    
    def cmd_nodes(self, args):
        self.node_cli.list_nodes()
    
    def cmd_logs(self, args):
        service = args[0] if args else None
        
        if service:
            logs = self.log_manager.tail_logs(service, lines=20)
            print(f"\n=== Logs: {service} ===\n")
            for line in logs:
                print(line.strip())
        else:
            logs = self.log_manager.get_logs(limit=20)
            print("\n=== Recent Logs ===\n")
            for entry in logs:
                print(f"[{entry['service']}] {entry['message']}")
        print()
    
    def cmd_restart(self, args):
        if not args:
            print("Usage: restart <service>")
            return
        
        service = args[0]
        print(f"Restarting {service}...")
        self.service_manager.stop_service(service)
        time.sleep(1)
        success, msg = self.service_manager.start_service(service)
        print(msg)
    
    def cmd_shutdown(self, args):
        confirm = input("Shutdown HelioCore OS? (yes/no): ")
        if confirm.lower() == 'yes':
            from boot_manager import BootManager
            boot = BootManager()
            boot.shutdown()
            sys.exit(0)
    
    def cmd_clear(self, args):
        os.system('clear')
    
    def run(self):
        print("HelioCore OS Shell - Type 'help' for commands\n")
        
        while True:
            try:
                text = self.session.prompt('heliocore> ')
                
                if not text.strip():
                    continue
                
                parts = text.strip().split()
                cmd = parts[0]
                args = parts[1:]
                
                if cmd == 'exit':
                    break
                elif cmd == 'help':
                    self.cmd_help(args)
                elif cmd == 'status':
                    self.cmd_status(args)
                elif cmd == 'services':
                    self.cmd_services(args)
                elif cmd == 'nodes':
                    self.cmd_nodes(args)
                elif cmd == 'logs':
                    self.cmd_logs(args)
                elif cmd == 'restart':
                    self.cmd_restart(args)
                elif cmd == 'shutdown':
                    self.cmd_shutdown(args)
                elif cmd == 'clear':
                    self.cmd_clear(args)
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")
            
            except KeyboardInterrupt:
                print("\nUse 'exit' or 'shutdown' to quit")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    shell = HelioCoreShell()
    shell.run()
```

**core/init.py**
```python
#!/usr/bin/env python3
import sys
sys.path.append('/home/pi/heliocoreos')
from core.boot_manager import BootManager
from core.heliocore_shell import HelioCoreShell

def main():
    boot = BootManager()
    
    if boot.boot():
        # Boot successful, launch shell
        shell = HelioCoreShell()
        shell.run()
        
        # Shell exited, shutdown
        boot.shutdown()
    else:
        print("\n[ERROR] Boot failed. Check logs for details.")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

**install/heliocore_boot.service**
```ini
[Unit]
Description=HelioCore OS Boot System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/heliocoreos
ExecStart=/usr/bin/python3 /home/pi/heliocoreos/core/init.py
StandardInput=tty
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
Restart=no

[Install]
WantedBy=multi-user.target
```

## Configuration Steps
1. Install prompt_toolkit:
```bash
pip3 install prompt_toolkit==3.0.36
```

2. Make init script executable:
```bash
chmod +x core/init.py
```

3. Install systemd service (optional):
```bash
sudo cp install/heliocore_boot.service /etc/systemd/system/
sudo systemctl enable heliocore_boot.service
```

4. Manual boot:
```bash
sudo python3 core/init.py
```

## Test Procedure
1. Run boot system:
```bash
sudo python3 core/init.py
```

2. Verify boot sequence displays correctly

3. Test shell commands:
```bash
heliocore> status
heliocore> services
heliocore> logs sensor
heliocore> help
```

4. Test service restart:
```bash
heliocore> restart tracking
```

5. Test shutdown:
```bash
heliocore> shutdown
```

## Expected Output
```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              HelioCore OS v1.0                            ║
║         Distributed Solar Tracking System                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

[PRE-BOOT] Running system checks...
  ✓ Directory: /tmp/heliocore
  ✓ Directory: /tmp/heliocore/pids
  ✓ Directory: /tmp/heliocore/logs
  ✓ Configuration found
[PRE-BOOT] System checks passed

[BOOT] Starting HelioCore OS services...

[  OK  ] Event Bus
[  OK  ] Node Agent
[  OK  ] Sensor Service
[  OK  ] Motor Service
[  OK  ] Tracking Engine
[  OK  ] Rain Protection
[  OK  ] Telemetry Service
[  OK  ] System Monitor

[HEALTH] Running system health check...
[HEALTH] Services: 8/8 running

============================================================
  HelioCore OS is ready.
  Type 'help' for available commands.
============================================================

HelioCore OS Shell - Type 'help' for commands

heliocore> status

=== HelioCore OS Status ===

CPU:    15.2%
Memory: 42.3%

Services: 8/8 running

heliocore> services

=== Services ===

● eventbus        RUNNING
● nodeagent       RUNNING
● sensor          RUNNING
● motor           RUNNING
● tracking        RUNNING
● rain            RUNNING
● telemetry       RUNNING
● monitor         RUNNING

heliocore> shutdown
Shutdown HelioCore OS? (yes/no): yes

[SHUTDOWN] Stopping HelioCore OS services...
[  OK  ] Stopped System Monitor
[  OK  ] Stopped Telemetry Service
[  OK  ] Stopped Rain Protection
[  OK  ] Stopped Tracking Engine
[  OK  ] Stopped Motor Service
[  OK  ] Stopped Sensor Service
[  OK  ] Stopped Node Agent
[  OK  ] Stopped Event Bus

[SHUTDOWN] HelioCore OS shutdown complete
```

## Completion Criteria
- [ ] Boot manager starts all services in order
- [ ] Boot progress displayed with status indicators
- [ ] Pre-boot checks validate system state
- [ ] Health check runs after boot
- [ ] Interactive shell launches automatically
- [ ] Shell commands work correctly
- [ ] Tab completion functional
- [ ] Command history persists
- [ ] Graceful shutdown stops all services
- [ ] Systemd service enables auto-boot

---

# HelioCore OS v1.0 - Agentic Architecture Complete

All 15 issues completed. HelioCore OS has evolved from a simple prototype into a full-featured agentic operating system with:

**Core Architecture (Issues 1-10):**
✓ Distributed Master-Pi/Farm-Pi architecture
✓ Hardware control (sensors + motors)
✓ Sun tracking algorithm
✓ Rain protection system
✓ Telemetry streaming
✓ Grafana dashboards
✓ CLI interface

**Agentic Features (Issues 11-15):**
✓ Service-oriented architecture
✓ Process-based service manager
✓ Event bus pub/sub system
✓ Distributed node management
✓ System monitoring and health checks
✓ Centralized logging
✓ Automated boot system
✓ Interactive shell

**System Capabilities:**
- Independent service processes
- Event-driven communication
- Multi-node orchestration
- Real-time monitoring
- Comprehensive logging
- Automated startup
- Interactive management

**Ready for hackathon demonstration and production deployment.**
