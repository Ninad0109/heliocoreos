#!/usr/bin/env python3
import json
import time
import requests
import signal
import sys
from sensor_manager import SensorManager
from motor_controller import MotorController
from tracking_algorithm import TrackingAlgorithm
from rain_protection import RainProtection

class FarmNode:
    def __init__(self, config_path='config.json'):
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.master_url = f"http://{self.config['master_ip']}:{self.config['master_port']}/telemetry"
        self.telemetry_interval = self.config['telemetry_interval']
        
        print("Initializing Farm Node...")
        self.sensor = SensorManager(self.config)
        self.motor = MotorController(self.config)
        self.tracker = TrackingAlgorithm(self.sensor, self.motor, self.config)
        self.protection = RainProtection(self.sensor, self.motor, self.tracker)
        
        self.running = False
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def collect_telemetry(self):
        sensor_data = self.sensor.get_telemetry()
        motor_state = self.motor.get_state()
        
        telemetry = {
            'ldr_left': sensor_data['ldr_left'],
            'ldr_right': sensor_data['ldr_right'],
            'ldr_top': sensor_data['ldr_top'],
            'ldr_bottom': sensor_data['ldr_bottom'],
            'rain': sensor_data['rain'],
            'petal_state': motor_state['petal_state'],
            'tilt_angle': motor_state['tilt_angle'],
            'base_angle': motor_state['base_angle'],
            'motor_state': int(self.tracker.is_active())
        }
        
        return telemetry
    
    def send_telemetry(self, data):
        try:
            response = requests.post(self.master_url, json=data, timeout=2)
            return response.status_code == 200
        except Exception as e:
            print(f"Telemetry transmission failed: {e}")
            return False
    
    def run(self):
        print("Farm Node starting...")
        print(f"Master-Pi: {self.master_url}")
        print("Starting sun tracking...")
        
        self.tracker.start()
        self.running = True
        
        while self.running:
            try:
                # Update protection system (highest priority)
                protection_state = self.protection.update()
                
                # Update tracking (if not protected)
                if not self.protection.is_protected():
                    self.tracker.update()
                
                # Collect and send telemetry
                telemetry = self.collect_telemetry()
                self.send_telemetry(telemetry)
                
                # Status output
                print(f"State: {protection_state.name} | Base: {telemetry['base_angle']}\u00b0 | Tilt: {telemetry['tilt_angle']}\u00b0 | Rain: {telemetry['rain']}")
                
                time.sleep(self.telemetry_interval)
                
            except Exception as e:
                print(f"Error in control loop: {e}")
                time.sleep(1)
        
        self.cleanup()
    
    def shutdown(self, signum, frame):
        print("\nShutdown signal received...")
        self.running = False
    
    def cleanup(self):
        print("Moving to safe position...")
        self.tracker.stop()
        self.motor.safe_position()
        self.sensor.cleanup()
        self.motor.cleanup()
        print("Farm Node shutdown complete")
        sys.exit(0)

if __name__ == '__main__':
    node = FarmNode()
    node.run()
