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
        data = {
            'node_id': self.node_id,
            'services': {}
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
        signal.signal(signal.SIGINT, lambda s, f: self.stop())
        
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
