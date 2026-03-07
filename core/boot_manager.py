import os
import time
import sys
from core.service_manager import ServiceManager
from core.health_checker import HealthChecker
from core.log_manager import logger

class BootManager:
    def __init__(self):
        self.service_manager = ServiceManager()
        self.health_checker = HealthChecker()
        self.boot_stages = [
            ('eventbus', 'Event Bus'),
            ('nodeagent', 'Node Agent'),
            ('sensor', 'Sensor Service'),
            ('motor', 'Motor Service'),
            ('tracking', 'Tracking Engine'),
            ('rain', 'Rain Protection'),
            ('telemetry', 'Telemetry Service'),
            ('monitor', 'System Monitor')
        ]
    
    def print_banner(self):
        banner = """
\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
\u2551                                                           \u2551
\u2551              HelioCore OS v1.0                            \u2551
\u2551         Distributed Solar Tracking System                 \u2551
\u2551                                                           \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
        """
        print(banner)
    
    def pre_boot_checks(self):
        print("\n[PRE-BOOT] Running system checks...")
        
        # Create required directories
        dirs = [
            '/tmp/heliocore',
            '/tmp/heliocore/pids',
            '/tmp/heliocore/logs'
        ]
        
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            print(f"  \u2713 Directory: {d}")
        
        # Check configuration
        config_file = '/home/pi/heliocoreos/farm-node/config.json'
        if os.path.exists(config_file):
            print(f"  \u2713 Configuration found")
        else:
            print(f"  \u2717 Configuration missing: {config_file}")
            return False
        
        print("[PRE-BOOT] System checks passed\n")
        return True
    
    def start_service(self, service_id, service_name):
        print(f"[ .... ] {service_name}", end='', flush=True)
        
        success, msg = self.service_manager.start_service(service_id)
        
        if success:
            time.sleep(1)  # Wait for service to initialize
            
            if self.service_manager.is_running(service_id):
                print(f"\r[  OK  ] {service_name}")
                logger.log('boot', 'INFO', f"{service_name} started successfully")
                return True
            else:
                print(f"\r[ FAIL ] {service_name}")
                logger.log('boot', 'ERROR', f"{service_name} failed to start")
                return False
        else:
            print(f"\r[ FAIL ] {service_name}")
            logger.log('boot', 'ERROR', f"{service_name} start failed: {msg}")
            return False
    
    def boot(self):
        self.print_banner()
        
        if not self.pre_boot_checks():
            print("\n[BOOT] Pre-boot checks failed. Aborting.")
            return False
        
        print("[BOOT] Starting HelioCore OS services...\n")
        
        failed_services = []
        
        for service_id, service_name in self.boot_stages:
            if not self.start_service(service_id, service_name):
                failed_services.append(service_name)
        
        print()
        
        if failed_services:
            print(f"[BOOT] Boot completed with errors:")
            for svc in failed_services:
                print(f"  \u2717 {svc}")
            return False
        else:
            print("[BOOT] All services started successfully")
            
            # Run health check
            print("\n[HEALTH] Running system health check...")
            time.sleep(2)
            
            status = self.service_manager.get_status()
            running = sum(1 for s in status.values() if s == 'RUNNING')
            
            print(f"[HEALTH] Services: {running}/{len(status)} running")
            
            if running == len(status):
                print("\n" + "=" * 60)
                print("  HelioCore OS is ready.")
                print("  Type 'help' for available commands.")
                print("=" * 60 + "\n")
                return True
            else:
                print("\n[HEALTH] Some services failed to start")
                return False
    
    def shutdown(self):
        print("\n[SHUTDOWN] Stopping HelioCore OS services...")
        
        # Stop in reverse order
        for service_id, service_name in reversed(self.boot_stages):
            if self.service_manager.is_running(service_id):
                print(f"[ .... ] Stopping {service_name}", end='', flush=True)
                self.service_manager.stop_service(service_id)
                print(f"\r[  OK  ] Stopped {service_name}")
        
        print("\n[SHUTDOWN] HelioCore OS shutdown complete")
