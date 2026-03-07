#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.event_client import EventClient

class TrackingService:
    def __init__(self):
        self.event_bus = EventClient()
        self.running = False
        self.active = True
        self.sensor_data = {}
        self.motor_state = {'base_angle': 0, 'tilt_angle': 0}
        self.threshold = 1
        self.step_size = 2
    
    def handle_sensor_update(self, data):
        self.sensor_data = data
    
    def handle_motor_update(self, data):
        self.motor_state = data
    
    def calculate_tracking(self):
        if not self.sensor_data or not self.active:
            return
        
        left = self.sensor_data.get('ldr_left', 0)
        right = self.sensor_data.get('ldr_right', 0)
        top = self.sensor_data.get('ldr_top', 0)
        bottom = self.sensor_data.get('ldr_bottom', 0)
        
        target = {}
        
        if abs(left - right) >= self.threshold:
            target['base_angle'] = self.motor_state['base_angle'] + \
                                   (-self.step_size if left > right else self.step_size)
        
        if abs(top - bottom) >= self.threshold:
            target['tilt_angle'] = self.motor_state['tilt_angle'] + \
                                   (self.step_size if top > bottom else -self.step_size)
        
        if target:
            self.event_bus.publish('tracking.target_updated', target)
    
    def start(self):
        print("[tracking_service] Starting...")
        self.event_bus.connect()
        self.event_bus.subscribe('sensor.ldr_update', self.handle_sensor_update)
        self.event_bus.subscribe('motor.position_changed', self.handle_motor_update)
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            self.calculate_tracking()
            time.sleep(2)
    
    def stop(self):
        self.running = False
        self.event_bus.disconnect()

if __name__ == '__main__':
    service = TrackingService()
    service.start()
