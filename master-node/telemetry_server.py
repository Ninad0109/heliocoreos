from flask import Flask, request, jsonify
import json
import time
import threading
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

app = Flask(__name__)
telemetry_lock = threading.Lock()

telemetry_data = {
    # Original metrics
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
    "farm_online": False,
    # New metrics from Grafana dashboard
    "tracking_active": 0,
    "tracking_direction": 0,
    "alignment_error": 0,
    "motor_base_state": 0,
    "motor_tilt_state": 0,
    "motor_temperature": 0,
    "heliocore_service_health": 0,
    "light_intensity_avg": 0,
    "farm_node_latency": 0
}

# Track when last telemetry was received for latency calculation
_last_receive_time = 0


@app.route('/telemetry', methods=['POST'])
def receive_telemetry():
    global telemetry_data, _last_receive_time
    data = request.get_json()
    now = time.time()

    with telemetry_lock:
        # Calculate farm node latency (round-trip estimate in ms)
        if _last_receive_time > 0:
            delta_ms = (now - _last_receive_time) * 1000
            # Latency = how much the interval deviates from expected ~1000ms
            telemetry_data['farm_node_latency'] = round(max(0, delta_ms - 1000), 1)
        _last_receive_time = now

        telemetry_data.update(data)
        telemetry_data['timestamp'] = datetime.now().isoformat()
        telemetry_data['farm_online'] = True

        # Server-side computed metrics (if farm didn't send them)
        ldr_l = telemetry_data['ldr_left']
        ldr_r = telemetry_data['ldr_right']
        ldr_t = telemetry_data['ldr_top']
        ldr_b = telemetry_data['ldr_bottom']

        if 'light_intensity_avg' not in data:
            telemetry_data['light_intensity_avg'] = round(
                (ldr_l + ldr_r + ldr_t + ldr_b) / 4.0, 2)

        if 'alignment_error' not in data:
            telemetry_data['alignment_error'] = abs(ldr_l - ldr_r) + abs(ldr_t - ldr_b)

        if 'tracking_active' not in data:
            telemetry_data['tracking_active'] = telemetry_data['motor_state']

        if 'tracking_direction' not in data:
            diff = ldr_r - ldr_l
            if diff > 0:
                telemetry_data['tracking_direction'] = 1   # moving right/east
            elif diff < 0:
                telemetry_data['tracking_direction'] = 2   # moving left/west
            else:
                telemetry_data['tracking_direction'] = 0   # aligned/idle

        if 'heliocore_service_health' not in data:
            telemetry_data['heliocore_service_health'] = 1 if telemetry_data['farm_online'] else 0

    return jsonify({"status": "ok"}), 200


@app.route('/metrics', methods=['GET'])
def get_metrics():
    with telemetry_lock:
        d = telemetry_data

        # System metrics from psutil (master-pi side)
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory().percent
        else:
            cpu = 0.0
            mem = 0.0

        lines = [
            # Original metrics
            f"ldr_left {d['ldr_left']}",
            f"ldr_right {d['ldr_right']}",
            f"ldr_top {d['ldr_top']}",
            f"ldr_bottom {d['ldr_bottom']}",
            f"rain_sensor {d['rain']}",
            f"petal_state {d['petal_state']}",
            f"tilt_angle {d['tilt_angle']}",
            f"base_angle {d['base_angle']}",
            f"motor_state {d['motor_state']}",
            f"farm_online {int(d['farm_online'])}",
            # New dashboard metrics
            f"tracking_active {d['tracking_active']}",
            f"tracking_direction {d['tracking_direction']}",
            f"alignment_error {d['alignment_error']}",
            f"motor_base_state {d['motor_base_state']}",
            f"motor_tilt_state {d['motor_tilt_state']}",
            f"motor_temperature {d['motor_temperature']}",
            f"cpu_usage {cpu}",
            f"memory_usage {mem}",
            f"heliocore_service_health {d['heliocore_service_health']}",
            f"light_intensity_avg {d['light_intensity_avg']}",
            f"farm_node_latency {d['farm_node_latency']}"
        ]

    return "\n".join(lines), 200, {'Content-Type': 'text/plain'}


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
