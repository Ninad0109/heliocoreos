#!/usr/bin/env python3
import sys
import time
import os
sys.path.append('/home/pi/heliocoreos')
from core.service_manager import ServiceManager
from core.log_manager import LogManager
from core.system_monitor import SystemMonitor
from core.health_checker import HealthChecker

def cmd_logs(args):
    log_mgr = LogManager()
    service = args[0] if args else None
    
    if service:
        logs = log_mgr.tail_logs(service, lines=50)
        print(f"\n=== Logs for {service} ===\n")
        for line in logs:
            print(line.strip())
    else:
        logs = log_mgr.get_logs(limit=50)
        print("\n=== Recent Logs ===\n")
        for entry in logs:
            print(f"{entry['timestamp']} [{entry['service']}] [{entry['level']}] {entry['message']}")

def cmd_top():
    monitor = SystemMonitor()
    service_mgr = ServiceManager()
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # System stats
            sys_stats = monitor.get_system_stats()
            print("=" * 70)
            print("HelioCore OS - System Monitor")
            print("=" * 70)
            print(f"CPU:    {sys_stats['cpu_percent']:.1f}%")
            print(f"Memory: {sys_stats['memory_percent']:.1f}%")
            print(f"Disk:   {sys_stats['disk_percent']:.1f}%")
            print()
            
            # Service stats
            print(f"{'Service':<15} {'Status':<10} {'CPU%':<8} {'Memory(MB)':<12} {'Uptime(s)'}")
            print("-" * 70)
            
            svc_stats = monitor.get_all_service_stats(service_mgr)
            for svc, stats in svc_stats.items():
                print(f"{svc:<15} {'RUNNING':<10} {stats['cpu_percent']:<8.1f} {stats['memory_mb']:<12.1f} {int(stats['uptime'])}")
            
            print("\nPress Ctrl+C to exit")
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n")

def cmd_health():
    health = HealthChecker()
    service_mgr = ServiceManager()
    
    # Register checks
    health.register_check('services', lambda: service_mgr.get_status())
    
    result = health.get_overall_health()
    
    print("\n=== System Health Check ===\n")
    print(f"Overall Status: {result['status'].upper()}")
    print(f"Checks Passing: {result['healthy_checks']}/{result['total_checks']}")
    print()
    
    for check_name, check_result in result['checks'].items():
        if check_result:
            status_icon = "\u2713" if check_result['status'] == 'healthy' else "\u2717"
            print(f"{status_icon} {check_name}: {check_result['status']}")
            if 'details' in check_result:
                print(f"  {check_result['details']}")

def cmd_service(args):
    if not args:
        print("Usage: heliocore service <start|stop|status|restart> [service_name]")
        return
    
    action = args[0]
    service_name = args[1] if len(args) > 1 else None
    manager = ServiceManager()
    
    if action == 'start' and service_name:
        success, msg = manager.start_service(service_name)
        print(msg)
    elif action == 'stop' and service_name:
        success, msg = manager.stop_service(service_name)
        print(msg)
    elif action == 'restart' and service_name:
        manager.stop_service(service_name)
        time.sleep(1)
        success, msg = manager.start_service(service_name)
        print(msg)
    elif action == 'status':
        status = manager.get_status(service_name)
        for name, state in status.items():
            print(f"{name}: {state}")
    else:
        print("Invalid service command")

def cmd_node(args):
    from master_node.node_manager_cli import NodeManagerCLI
    
    if not args:
        print("Usage: heliocore node <list|status|ping> [node_id]")
        return
    
    action = args[0]
    node_id = args[1] if len(args) > 1 else None
    cli = NodeManagerCLI()
    
    if action == 'list':
        cli.list_nodes()
    elif action == 'status' and node_id:
        cli.node_status(node_id)
    elif action == 'ping' and node_id:
        cli.ping_node(node_id)
    else:
        print("Invalid node command")

def main():
    if len(sys.argv) < 2:
        print("Usage: heliocore <command> [args]")
        print("Commands: service, node, logs, top, health")
        return
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == 'service':
        cmd_service(args)
    elif cmd == 'node':
        cmd_node(args)
    elif cmd == 'logs':
        cmd_logs(args)
    elif cmd == 'top':
        cmd_top()
    elif cmd == 'health':
        cmd_health()
    else:
        print(f"Unknown command: {cmd}")

if __name__ == '__main__':
    main()
