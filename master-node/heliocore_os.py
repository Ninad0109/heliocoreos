#!/usr/bin/env python3
import os
import sys
import time
import json
from datetime import datetime
from metrics import get_current_metrics

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_status(online):
    return "ONLINE" if online else "OFFLINE"

def format_binary(value):
    return "YES" if value else "NO"

def format_petal(state):
    return "OPEN" if state else "CLOSED"

def format_motor(state):
    return "ACTIVE" if state else "IDLE"

def display_dashboard(data, start_time):
    clear_screen()
    
    uptime = int(time.time() - start_time)
    
    print("=" * 50)
    print("           HelioCore OS v1.0")
    print("=" * 50)
    print()
    
    if data:
        print(f"Farm Node: {format_status(data.get('farm_online', False))}")
        print(f"Sun Tracking: {format_motor(data.get('motor_state', 0))}")
        print(f"Rain Protection: {'ACTIVE' if data.get('rain', 0) else 'STANDBY'}")
        print()
        
        print("Sensors")
        print("-" * 50)
        print(f"Left Light:   {data.get('ldr_left', 0)}")
        print(f"Right Light:  {data.get('ldr_right', 0)}")
        print(f"Top Light:    {data.get('ldr_top', 0)}")
        print(f"Bottom Light: {data.get('ldr_bottom', 0)}")
        print(f"Rain:         {format_binary(data.get('rain', 0))}")
        print()
        
        print("Motors")
        print("-" * 50)
        print(f"Base Angle:   {data.get('base_angle', 0)}°")
        print(f"Tilt Angle:   {data.get('tilt_angle', 0)}°")
        print(f"Petals:       {format_petal(data.get('petal_state', 0))}")
        print()
        
        if data.get('timestamp'):
            print(f"Last Update:  {data['timestamp']}")
    else:
        print("Farm Node: OFFLINE")
        print("Waiting for telemetry data...")
        print()
    
    print(f"System Uptime: {uptime}s")
    print()
    print("Press Ctrl+C to exit")

def main():
    with open('config.json') as f:
        config = json.load(f)
    
    base_url = f"http://localhost:{config['telemetry_port']}"
    refresh_rate = config.get('refresh_rate', 1.0)
    start_time = time.time()
    
    print("Starting HelioCore OS...")
    time.sleep(1)
    
    try:
        while True:
            data = get_current_metrics(base_url)
            display_dashboard(data, start_time)
            time.sleep(refresh_rate)
    except KeyboardInterrupt:
        clear_screen()
        print("\nHelioCore OS shutdown complete.")
        sys.exit(0)

if __name__ == '__main__':
    main()
