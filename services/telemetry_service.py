#!/usr/bin/env python3
import sys
import time
import signal
import requests
import json
sys.path.append('/home/pi/heliocoreos')
from core.event_client import EventClient

class TelemetryService:
    def __init__(self):
        with open('/home/pi/heliocoreos/farm-node/config.json') as f:
            config = json.load(f)
        self.master_url = f"http://{config['master_ip']}:{config['master_port']}/telemetry"
        self.event_bus = EventClient()
        self.running = False
        self.sensor_data = {}
        self.motor_state = {}
    
    def handle_sensor_update(self, data):
        self.sensor_data = data
    
    def handle_motor_update(self, data):
        self.motor_state = data
    
    def start(self):
        print("[telemetry_service] Starting...")
        self.event_bus.connect()
        self.event_bus.subscribe('sensor.ldr_update', self.handle_sensor_update)
        self.event_bus.subscribe('motor.position_changed', self.handle_motor_update)
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            if self.sensor_data and self.motor_state:
                telemetry = {**self.sensor_data, **self.motor_state, 'motor_state': 1}
                try:
                    requests.post(self.master_url, json=telemetry, timeout=2)
                except:
                    pass
            time.sleep(1)
    
    def stop(self):
        self.running = False
        self.event_bus.disconnect()

if __name__ == '__main__':
    service = TelemetryService()
    service.start()
