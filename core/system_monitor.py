import psutil
import os
import time

class SystemMonitor:
    def __init__(self):
        self.process_cache = {}
    
    def get_system_stats(self):
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
    
    def get_service_stats(self, pid):
        try:
            if pid not in self.process_cache:
                self.process_cache[pid] = psutil.Process(pid)
            
            proc = self.process_cache[pid]
            return {
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'memory_mb': proc.memory_info().rss / 1024 / 1024,
                'status': proc.status(),
                'uptime': time.time() - proc.create_time()
            }
        except:
            if pid in self.process_cache:
                del self.process_cache[pid]
            return None
    
    def get_all_service_stats(self, service_manager):
        stats = {}
        pid_dir = '/tmp/heliocore/pids'
        
        if not os.path.exists(pid_dir):
            return stats
        
        for service in os.listdir(pid_dir):
            if service.endswith('.pid'):
                service_name = service[:-4]
                try:
                    with open(f'{pid_dir}/{service}') as f:
                        pid = int(f.read())
                    
                    service_stats = self.get_service_stats(pid)
                    if service_stats:
                        stats[service_name] = service_stats
                except:
                    pass
        
        return stats
