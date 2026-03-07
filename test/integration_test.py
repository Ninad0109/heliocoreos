#!/usr/bin/env python3
import requests
import time
import sys

def test_master_telemetry():
    print("Testing Master-Pi telemetry endpoint...")
    try:
        response = requests.get('http://localhost:5000/status', timeout=2)
        if response.status_code == 200:
            print("\u2713 Telemetry server responding")
            return True
    except:
        print("\u2717 Telemetry server not responding")
        return False

def test_master_metrics():
    print("Testing Master-Pi metrics endpoint...")
    try:
        response = requests.get('http://localhost:5000/metrics', timeout=2)
        if response.status_code == 200 and 'ldr_left' in response.text:
            print("\u2713 Metrics endpoint working")
            return True
    except:
        print("\u2717 Metrics endpoint not responding")
        return False

def test_grafana():
    print("Testing Grafana...")
    try:
        response = requests.get('http://localhost:3000', timeout=2)
        if response.status_code == 200:
            print("\u2713 Grafana accessible")
            return True
    except:
        print("\u2717 Grafana not accessible")
        return False

def test_farm_telemetry(master_ip):
    print(f"Testing Farm-Pi telemetry to {master_ip}...")
    test_data = {
        'ldr_left': 1,
        'ldr_right': 1,
        'ldr_top': 1,
        'ldr_bottom': 1,
        'rain': 0,
        'petal_state': 1,
        'tilt_angle': 45,
        'base_angle': 30,
        'motor_state': 1
    }
    try:
        response = requests.post(f'http://{master_ip}:5000/telemetry', json=test_data, timeout=2)
        if response.status_code == 200:
            print("\u2713 Farm telemetry transmission working")
            time.sleep(1)
            status = requests.get(f'http://{master_ip}:5000/status', timeout=2).json()
            if status['tilt_angle'] == 45:
                print("\u2713 Telemetry data received correctly")
                return True
    except Exception as e:
        print(f"\u2717 Farm telemetry failed: {e}")
        return False

def main():
    print("=== HelioCore OS Integration Test ===\n")
    
    results = []
    
    # Master-Pi tests
    results.append(test_master_telemetry())
    results.append(test_master_metrics())
    results.append(test_grafana())
    
    # Farm-Pi test
    master_ip = input("\nEnter Master-Pi IP address (or 'localhost'): ").strip()
    results.append(test_farm_telemetry(master_ip))
    
    print("\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("\n\u2713 All systems operational - HelioCore OS ready for deployment")
        sys.exit(0)
    else:
        print("\n\u2717 Some tests failed - check configuration")
        sys.exit(1)

if __name__ == '__main__':
    main()
