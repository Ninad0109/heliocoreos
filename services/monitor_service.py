#!/usr/bin/env python3
import sys
import time
import signal
sys.path.append('/home/pi/heliocoreos')
from core.system_monitor import SystemMonitor
from core.health_checker import HealthChecker
from core.log_manager import logger
from core.service_manager import ServiceManager

class MonitorService:
    def __init__(self):
        self.monitor = SystemMonitor()
        self.health = HealthChecker()
        self.service_manager = ServiceManager()
        self.running = False
        
        # Register health checks
        self.health.register_check('services', self.check_services, interval=30)
        self.health.register_check('system', self.check_system, interval=60)
    
    def check_services(self):
        status = self.service_manager.get_status()
        running = sum(1 for s in status.values() if s == 'RUNNING')
        return {'running': running, 'total': len(status), 'services': status}
    
    def check_system(self):
        stats = self.monitor.get_system_stats()
        healthy = stats['cpu_percent'] < 90 and stats['memory_percent'] < 90
        return {'healthy': healthy, 'stats': stats}
    
    def start(self):
        print("[monitor_service] Starting...")
        logger.log('monitor', 'INFO', 'Monitor service started')
        self.running = True
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        
        while self.running:
            # Collect system stats
            sys_stats = self.monitor.get_system_stats()
            logger.log('monitor', 'DEBUG', f"System: CPU={sys_stats['cpu_percent']}% MEM={sys_stats['memory_percent']}%")
            
            # Collect service stats
            svc_stats = self.monitor.get_all_service_stats(self.service_manager)
            for svc, stats in svc_stats.items():
                if stats['cpu_percent'] > 50:
                    logger.log('monitor', 'WARN', f"High CPU usage in {svc}: {stats['cpu_percent']}%")
            
            # Run health checks
            health = self.health.get_overall_health()
            if health['status'] != 'healthy':
                logger.log('monitor', 'WARN', f"System health degraded: {health['healthy_checks']}/{health['total_checks']} checks passing")
            
            time.sleep(10)
    
    def stop(self):
        self.running = False
        logger.log('monitor', 'INFO', 'Monitor service stopped')

if __name__ == '__main__':
    service = MonitorService()
    service.start()
