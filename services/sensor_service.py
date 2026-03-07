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
