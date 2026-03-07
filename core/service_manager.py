import subprocess
import os
import signal
import time

class ServiceManager:
    def __init__(self):
        self.services = {
            'eventbus': '/home/pi/heliocoreos/core/event_bus.py',
            'nodeagent': '/home/pi/heliocoreos/farm-node/node_agent.py',
            'sensor': '/home/pi/heliocoreos/services/sensor_service.py',
            'motor': '/home/pi/heliocoreos/services/motor_service.py',
            'tracking': '/home/pi/heliocoreos/services/tracking_service.py',
            'rain': '/home/pi/heliocoreos/services/rain_service.py',
            'telemetry': '/home/pi/heliocoreos/services/telemetry_service.py',
            'monitor': '/home/pi/heliocoreos/services/monitor_service.py'
        }
        self.pid_dir = '/tmp/heliocore/pids'
        os.makedirs(self.pid_dir, exist_ok=True)
    
    def start_service(self, name):
        if name not in self.services:
            return False, f"Unknown service: {name}"
        
        if self.is_running(name):
            return False, f"Service {name} already running"
        
        proc = subprocess.Popen(['python3', self.services[name]])
        with open(f'{self.pid_dir}/{name}.pid', 'w') as f:
            f.write(str(proc.pid))
        
        return True, f"Service {name} started (PID: {proc.pid})"
    
    def stop_service(self, name):
        pid_file = f'{self.pid_dir}/{name}.pid'
        if not os.path.exists(pid_file):
            return False, f"Service {name} not running"
        
        with open(pid_file) as f:
            pid = int(f.read())
        
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            os.remove(pid_file)
            return True, f"Service {name} stopped"
        except:
            return False, f"Failed to stop service {name}"
    
    def is_running(self, name):
        pid_file = f'{self.pid_dir}/{name}.pid'
        if not os.path.exists(pid_file):
            return False
        
        with open(pid_file) as f:
            pid = int(f.read())
        
        try:
            os.kill(pid, 0)
            return True
        except:
            os.remove(pid_file)
            return False
    
    def get_status(self, name=None):
        if name:
            status = "RUNNING" if self.is_running(name) else "STOPPED"
            return {name: status}
        
        return {name: ("RUNNING" if self.is_running(name) else "STOPPED") 
                for name in self.services}
