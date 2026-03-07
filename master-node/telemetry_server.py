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
