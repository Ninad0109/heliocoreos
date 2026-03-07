#!/usr/bin/env python3
"""Comprehensive HelioCore OS test suite - runs on Windows dev machine."""
import threading
import time
import sys
import os
import json
import urllib.request
import urllib.error
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
HELIO = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(HELIO, 'master-node'))
sys.path.insert(0, os.path.join(HELIO, 'core'))

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")

def post_json(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                headers={'Content-Type': 'application/json'})
    r = urllib.request.urlopen(req, timeout=3)
    return r.status, json.loads(r.read().decode())

def get_text(url):
    r = urllib.request.urlopen(url, timeout=3)
    return r.status, r.read().decode()

def get_json(url):
    status, text = get_text(url)
    return status, json.loads(text)

# =============================================
print("\n" + "=" * 60)
print("SECTION 1: Telemetry Server (Issue 2)")
print("=" * 60)

from telemetry_server import app as telem_app
t1 = threading.Thread(target=lambda: telem_app.run(host='127.0.0.1', port=5555,
                      debug=False, use_reloader=False), daemon=True)
t1.start()
time.sleep(1.5)

# POST /telemetry
s, body = post_json('http://127.0.0.1:5555/telemetry', {
    'ldr_left': 2, 'ldr_right': 1, 'ldr_top': 1, 'ldr_bottom': 0,
    'rain': 0, 'petal_state': 1, 'tilt_angle': 35, 'base_angle': 12, 'motor_state': 1
})
test("POST /telemetry -> 200", s == 200)
test("POST /telemetry -> status ok", body.get('status') == 'ok')

# GET /metrics
s, text = get_text('http://127.0.0.1:5555/metrics')
test("GET /metrics -> 200", s == 200)
test("GET /metrics -> contains ldr_left 2", 'ldr_left 2' in text)
test("GET /metrics -> contains rain_sensor 0", 'rain_sensor 0' in text)
test("GET /metrics -> contains farm_online 1", 'farm_online 1' in text)
test("GET /metrics -> 10 metric lines", len(text.strip().split('\n')) == 10)

# GET /status
s, data = get_json('http://127.0.0.1:5555/status')
test("GET /status -> 200", s == 200)
test("GET /status -> farm_online=True", data['farm_online'] == True)
test("GET /status -> tilt_angle=35", data['tilt_angle'] == 35)
test("GET /status -> base_angle=12", data['base_angle'] == 12)
test("GET /status -> has timestamp", data['timestamp'] is not None)

# Update telemetry and verify overwrite
post_json('http://127.0.0.1:5555/telemetry', {
    'ldr_left': 0, 'rain': 1, 'tilt_angle': 90
})
s, data = get_json('http://127.0.0.1:5555/status')
test("Telemetry overwrite -> ldr_left=0", data['ldr_left'] == 0)
test("Telemetry overwrite -> rain=1", data['rain'] == 1)
test("Telemetry overwrite -> tilt_angle=90", data['tilt_angle'] == 90)

# =============================================
print("\n" + "=" * 60)
print("SECTION 2: Node Registry (Issue 13)")
print("=" * 60)

from node_registry import app as node_app
t2 = threading.Thread(target=lambda: node_app.run(host='127.0.0.1', port=5556,
                      debug=False, use_reloader=False), daemon=True)
t2.start()
time.sleep(1.5)

# Register node 1
s, body = post_json('http://127.0.0.1:5556/node/register', {
    'node_id': 'farm-pi-01', 'ip': '192.168.1.101',
    'hostname': 'farm-pi-01', 'capabilities': ['sensors', 'motors']
})
test("Register node 1 -> 200", s == 200)

# Register node 2
s, body = post_json('http://127.0.0.1:5556/node/register', {
    'node_id': 'farm-pi-02', 'ip': '192.168.1.102',
    'hostname': 'farm-pi-02', 'capabilities': ['sensors']
})
test("Register node 2 -> 200", s == 200)

# Heartbeat with service info
s, body = post_json('http://127.0.0.1:5556/node/heartbeat', {
    'node_id': 'farm-pi-01',
    'services': {'sensor': 'RUNNING', 'motor': 'RUNNING', 'tracking': 'RUNNING'}
})
test("Heartbeat -> 200", s == 200)

# List nodes
s, data = get_json('http://127.0.0.1:5556/node/list')
nodes = data['nodes']
test("Node list -> 2 nodes", len(nodes) == 2)

# Node status
s, node = get_json('http://127.0.0.1:5556/node/status/farm-pi-01')
test("Node status -> online", node['status'] == 'online')
test("Node status -> has services", 'services' in node)
test("Node status -> sensor RUNNING", node.get('services', {}).get('sensor') == 'RUNNING')
test("Node status -> has registered_at", 'registered_at' in node)

# Unknown node -> 404
try:
    get_json('http://127.0.0.1:5556/node/status/unknown-node')
    test("Unknown node -> 404", False)
except urllib.error.HTTPError as e:
    test("Unknown node -> 404", e.code == 404)

# =============================================
print("\n" + "=" * 60)
print("SECTION 3: Metrics Helper (Issue 2)")
print("=" * 60)

from metrics import get_current_metrics
result = get_current_metrics('http://127.0.0.1:5555')
test("get_current_metrics() returns dict", isinstance(result, dict))
test("get_current_metrics() has farm_online", 'farm_online' in result)
test("get_current_metrics() bad url returns None", get_current_metrics('http://127.0.0.1:9999') is None)

# =============================================
print("\n" + "=" * 60)
print("SECTION 4: Log Manager (Issue 14)")
print("=" * 60)

sys.path.insert(0, os.path.join(HELIO, 'core'))
tmp_log_dir = os.path.join(tempfile.gettempdir(), 'heliocore_test_logs')

from log_manager import LogManager
lm = LogManager(log_dir=tmp_log_dir)

lm.log('sensor', 'INFO', 'Sensor initialized')
lm.log('sensor', 'DEBUG', 'Reading LDR pins')
lm.log('motor', 'WARN', 'High temperature detected')
lm.log('sensor', 'ERROR', 'LDR read timeout')

all_logs = lm.get_logs()
test("Log buffer has 4 entries", len(all_logs) == 4)

sensor_logs = lm.get_logs(service='sensor')
test("Filter by service=sensor -> 3 logs", len(sensor_logs) == 3)

warn_logs = lm.get_logs(level='WARN')
test("Filter by level=WARN -> 1 log", len(warn_logs) == 1)

tail = lm.tail_logs('sensor', lines=2)
test("Tail sensor logs -> 2 lines", len(tail) == 2)

test("Log file created", os.path.exists(os.path.join(tmp_log_dir, 'sensor.log')))

# =============================================
print("\n" + "=" * 60)
print("SECTION 5: Health Checker (Issue 14)")
print("=" * 60)

from health_checker import HealthChecker
hc = HealthChecker()

hc.register_check('always_healthy', lambda: {'status': 'ok'}, interval=0)
hc.register_check('always_unhealthy', lambda: None, interval=0)

result = hc.get_overall_health()
test("Overall status -> degraded", result['status'] == 'degraded')
test("Healthy checks -> 1", result['healthy_checks'] == 1)
test("Total checks -> 2", result['total_checks'] == 2)

# All healthy
hc2 = HealthChecker()
hc2.register_check('ok1', lambda: True, interval=0)
hc2.register_check('ok2', lambda: {'good': True}, interval=0)
result2 = hc2.get_overall_health()
test("All healthy -> status=healthy", result2['status'] == 'healthy')

# =============================================
print("\n" + "=" * 60)
print("SECTION 6: Service Base (Issue 11)")
print("=" * 60)

from service_base import ServiceBase
tmp_state_dir = os.path.join(tempfile.gettempdir(), 'heliocore_test_state')

class TestService(ServiceBase):
    def initialize(self): pass
    def run_loop(self): self.running = False

ts = TestService('test_svc')
ts.state_dir = tmp_state_dir
os.makedirs(tmp_state_dir, exist_ok=True)

ts.write_state('test_key', {'value': 42, 'active': True})
data = ts.read_state('test_key')
test("State write/read -> value=42", data['value'] == 42)
test("State write/read -> active=True", data['active'] == True)
test("Read missing state -> None", ts.read_state('nonexistent') is None)

# =============================================
print("\n" + "=" * 60)
print("SECTION 7: Config Validation")
print("=" * 60)

with open(os.path.join(HELIO, 'master-node', 'config.json')) as f:
    mc = json.load(f)
test("Master config -> telemetry_port exists", 'telemetry_port' in mc)
test("Master config -> telemetry_port=5000", mc['telemetry_port'] == 5000)
test("Master config -> refresh_rate=1.0", mc['refresh_rate'] == 1.0)

with open(os.path.join(HELIO, 'farm-node', 'config.json')) as f:
    fc = json.load(f)
test("Farm config -> 6 LDR pins", len(fc['ldr_pins']) == 6)
test("Farm config -> 2 rain pins", len(fc['rain_pins']) == 2)
test("Farm config -> base limits", fc['base_min_angle'] == -160 and fc['base_max_angle'] == 160)
test("Farm config -> tilt limits", fc['tilt_min_angle'] == 0 and fc['tilt_max_angle'] == 90)
test("Farm config -> 3 motors configured", all(k in fc for k in ['motor1_step','motor2_step','motor3_step']))

with open(os.path.join(HELIO, 'dashboards', 'grafana_dashboard.json')) as f:
    gc = json.load(f)
test("Grafana -> 6 panels", len(gc['dashboard']['panels']) == 6)
test("Grafana -> 1s refresh", gc['dashboard']['refresh'] == '1s')

# =============================================
print("\n" + "=" * 60)
print("SECTION 8: Module Import Tests")
print("=" * 60)

try:
    from service_manager import ServiceManager
    sm = ServiceManager()
    test("ServiceManager instantiates", True)
    test("ServiceManager -> 8 services registered", len(sm.services) == 8)
    test("ServiceManager -> has eventbus", 'eventbus' in sm.services)
    test("ServiceManager -> has nodeagent", 'nodeagent' in sm.services)
    test("ServiceManager -> has monitor", 'monitor' in sm.services)
except Exception as e:
    test(f"ServiceManager import: {e}", False)

try:
    from event_client import EventClient
    ec = EventClient()
    test("EventClient instantiates", True)
except Exception as e:
    test(f"EventClient import: {e}", False)

try:
    from node_manager_cli import NodeManagerCLI
    nc = NodeManagerCLI()
    test("NodeManagerCLI instantiates", True)
except Exception as e:
    test(f"NodeManagerCLI import: {e}", False)


# =============================================
# SUMMARY
# =============================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} tests passed, {failed} failed")
print("=" * 60)

# Cleanup
import shutil
for d in [tmp_log_dir, tmp_state_dir]:
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
