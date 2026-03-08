#!/usr/bin/env python3
"""Test the updated telemetry pipeline with all 21 metrics."""
import threading, time, sys, os, json, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'master-node'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'demo'))

# Start telemetry server
from telemetry_server import app
t = threading.Thread(
    target=lambda: app.run(host='127.0.0.1', port=5888, debug=False, use_reloader=False),
    daemon=True
)
t.start()
time.sleep(2)

# Run simulator for 3 ticks
from demo_simulator import FarmSimulator
sim = FarmSimulator(master_url='http://127.0.0.1:5888')
sim.sim_speed = 0.05

passed = 0
failed = 0

def test(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print("  [PASS] {}".format(name))
    else:
        failed += 1
        print("  [FAIL] {}".format(name))

print("=" * 60)
print("Metrics Pipeline Test (21 metrics)")
print("=" * 60)

# Send a few ticks
for i in range(3):
    sim.sim_time += sim.sim_speed
    sun_az, sun_el = sim.get_sun_position()
    ldr_l, ldr_r, ldr_t, ldr_b = sim.get_ldr_readings(sun_az, sun_el)
    sim.update_rain()
    sim.update_tracking(ldr_l, ldr_r, ldr_t, ldr_b)
    sim.send_telemetry(ldr_l, ldr_r, ldr_t, ldr_b)
    time.sleep(0.5)

# Get metrics
r = urllib.request.urlopen('http://127.0.0.1:5888/metrics', timeout=3)
metrics_text = r.read().decode()
metric_lines = [l.strip() for l in metrics_text.strip().split('\n') if l.strip()]

print()
print("Metrics returned ({} lines):".format(len(metric_lines)))
for line in metric_lines:
    print("  " + line)

# Check all 21 expected metric names
expected = [
    'ldr_left', 'ldr_right', 'ldr_top', 'ldr_bottom',
    'rain_sensor', 'petal_state', 'tilt_angle', 'base_angle',
    'motor_state', 'farm_online',
    'tracking_active', 'tracking_direction', 'alignment_error',
    'motor_base_state', 'motor_tilt_state', 'motor_temperature',
    'cpu_usage', 'memory_usage',
    'heliocore_service_health', 'light_intensity_avg', 'farm_node_latency'
]

print()
print("Checking all 21 metrics:")
metric_dict = {}
for line in metric_lines:
    parts = line.split(' ', 1)
    if len(parts) == 2:
        metric_dict[parts[0]] = parts[1]

for name in expected:
    present = name in metric_dict
    test("{} = {}".format(name, metric_dict.get(name, 'MISSING')), present)

# Check /status has new fields
r = urllib.request.urlopen('http://127.0.0.1:5888/status', timeout=3)
status = json.loads(r.read().decode())

print()
print("Checking /status JSON:")
new_fields = ['tracking_active', 'tracking_direction', 'alignment_error',
              'motor_base_state', 'motor_tilt_state', 'motor_temperature',
              'heliocore_service_health', 'light_intensity_avg']

for f in new_fields:
    test("/status has '{}'".format(f), f in status)

print()
print("=" * 60)
total = passed + failed
result = "ALL PASSED" if failed == 0 else "{} FAILED".format(failed)
print("RESULT: {}/{} tests — {}".format(passed, total, result))
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
