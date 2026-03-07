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
