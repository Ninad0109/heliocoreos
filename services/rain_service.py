#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.event_client import EventClient

class RainService:
    def __init__(self):
        self.event_bus = EventClient()
        self.running = False
        self.protected = False
    
    def handle_rain_detected(self, data):
        if not self.protected:
            print("[rain_service] Rain detected - triggering emergency stop")
            self.event_bus.publish('system.emergency_stop', {'reason': 'rain'})
            self.protected = True
    
    def start(self):
        print("[rain_service] Starting...")
        self.event_bus.connect()
        self.event_bus.subscribe('sensor.rain_detected', self.handle_rain_detected)
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            time.sleep(1)
    
    def stop(self):
        self.running = False
        self.event_bus.disconnect()

if __name__ == '__main__':
    service = RainService()
    service.start()
