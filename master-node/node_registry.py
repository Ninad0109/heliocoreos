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
