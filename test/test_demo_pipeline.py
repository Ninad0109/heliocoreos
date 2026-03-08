#!/usr/bin/env python3
"""Live integration test: Simulator -> Telemetry Server."""
import threading
import time
import sys
import json
import os
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'master-node'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'demo'))

# Start telemetry server on test port
from telemetry_server import app
t = threading.Thread(
    target=lambda: app.run(host='127.0.0.1', port=5777, debug=False, use_reloader=False),
    daemon=True
)
t.start()
time.sleep(2)

# Create simulator
from demo_simulator import FarmSimulator
sim = FarmSimulator(master_url='http://127.0.0.1:5777')
sim.sim_speed = 0.05

print("=" * 70)
print("LIVE INTEGRATION TEST: Simulator -> Telemetry Server")
print("=" * 70)
print()

passed = 0
total = 10

for i in range(total):
    sim.sim_time += sim.sim_speed
    if sim.sim_time >= 1.0:
        sim.sim_time = 0.0

    sun_az, sun_el = sim.get_sun_position()
    ldr_l, ldr_r, ldr_t, ldr_b = sim.get_ldr_readings(sun_az, sun_el)
    sim.update_rain()
    sim.update_tracking(ldr_l, ldr_r, ldr_t, ldr_b)
    sent = sim.send_telemetry(ldr_l, ldr_r, ldr_t, ldr_b)

    # Verify server state
    r = urllib.request.urlopen('http://127.0.0.1:5777/status', timeout=2)
    status = json.loads(r.read().decode())

    match = (
        status['base_angle'] == round(sim.base_angle, 1) and
        status['tilt_angle'] == round(sim.tilt_angle, 1) and
        sent
    )

    if match:
        passed += 1
        verdict = "PASS"
    else:
        verdict = "FAIL"

    state = "RAIN" if sim.rain else "TRACK"
    print("  Tick {:2d}  Sun:{:+7.1f}/{:5.1f}  Panel:{:+7.1f}/{:5.1f}  "
          "LDR:{}{}{}{} [{}]  TX:{}  [{}]".format(
              i + 1, sun_az, sun_el, sim.base_angle, sim.tilt_angle,
              ldr_l, ldr_r, ldr_t, ldr_b, state,
              "OK" if sent else "FAIL", verdict))

# Verify metrics endpoint
print()
r = urllib.request.urlopen('http://127.0.0.1:5777/metrics', timeout=2)
metrics = r.read().decode()
metric_lines = [l for l in metrics.strip().split('\n') if l]

print("Prometheus /metrics endpoint ({} lines):".format(len(metric_lines)))
for line in metric_lines:
    print("  " + line)

# Verify /status JSON
print()
r = urllib.request.urlopen('http://127.0.0.1:5777/status', timeout=2)
status = json.loads(r.read().decode())
print("Final /status JSON:")
for k, v in status.items():
    print("  {}: {}".format(k, v))

print()
print("=" * 70)
result = "ALL PASSED" if passed == total else "{} FAILED".format(total - passed)
print("RESULT: {}/{} ticks verified — {}".format(passed, total, result))
print("=" * 70)

sys.exit(0 if passed == total else 1)
