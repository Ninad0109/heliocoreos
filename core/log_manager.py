import os
import json
from datetime import datetime
from collections import deque

class LogManager:
    def __init__(self, log_dir='/tmp/heliocore/logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_buffer = deque(maxlen=1000)
    
    def log(self, service, level, message):
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'service': service,
            'level': level,
            'message': message
        }
        
        self.log_buffer.append(entry)
        
        log_file = f'{self.log_dir}/{service}.log'
        with open(log_file, 'a') as f:
            f.write(f"{timestamp} [{level}] {message}\n")
    
    def get_logs(self, service=None, level=None, limit=100):
        logs = list(self.log_buffer)
        
        if service:
            logs = [l for l in logs if l['service'] == service]
        
        if level:
            logs = [l for l in logs if l['level'] == level]
        
        return logs[-limit:]
    
    def tail_logs(self, service, lines=50):
        log_file = f'{self.log_dir}/{service}.log'
        if not os.path.exists(log_file):
            return []
        
        with open(log_file) as f:
            return f.readlines()[-lines:]

# Global logger instance
logger = LogManager()
