#!/usr/bin/env python3
import sys
import os
import time

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import FileHistory
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

sys.path.append('/home/pi/heliocoreos')
from core.service_manager import ServiceManager
from core.system_monitor import SystemMonitor
from core.log_manager import LogManager

class HelioCoreShell:
    def __init__(self):
        self.service_manager = ServiceManager()
        self.monitor = SystemMonitor()
        self.log_manager = LogManager()
        
        self.commands = {
            'help': self.cmd_help,
            'status': self.cmd_status,
            'services': self.cmd_services,
            'nodes': self.cmd_nodes,
            'logs': self.cmd_logs,
            'restart': self.cmd_restart,
            'shutdown': self.cmd_shutdown,
            'health': self.cmd_health,
            'clear': self.cmd_clear,
            'exit': None,
            'service': self.cmd_service,
            'node': self.cmd_node,
        }
        
        if HAS_PROMPT_TOOLKIT:
            completer = WordCompleter(list(self.commands.keys()), ignore_case=True)
            self.session = PromptSession(
                history=FileHistory('/tmp/heliocore/.shell_history'),
                completer=completer
            )
        else:
            self.session = None
    
    def get_input(self, prompt_str):
        if self.session:
            return self.session.prompt(prompt_str)
        else:
            return input(prompt_str)
    
    def cmd_help(self, args):
        print("""
HelioCore OS Shell Commands:

  status              Show system status
  services            List all services
  nodes               List registered nodes
  logs [service]      View service logs
  restart <service>   Restart a service
  shutdown            Shutdown HelioCore OS
  health              Run health check
  clear               Clear screen
  exit                Exit shell

Service Management:
  service start <name>
  service stop <name>
  service restart <name>
  service status [name]

Node Management:
  node list
  node status <id>
  node ping <id>
        """)
    
    def cmd_status(self, args):
        print("\n=== HelioCore OS Status ===\n")
        
        # System stats
        try:
            sys_stats = self.monitor.get_system_stats()
            print(f"CPU:    {sys_stats['cpu_percent']:.1f}%")
            print(f"Memory: {sys_stats['memory_percent']:.1f}%")
            print()
        except:
            print("System stats unavailable (psutil not installed)")
            print()
        
        # Service status
        status = self.service_manager.get_status()
        running = sum(1 for s in status.values() if s == 'RUNNING')
        print(f"Services: {running}/{len(status)} running")
        print()
    
    def cmd_services(self, args):
        status = self.service_manager.get_status()
        
        print("\n=== Services ===\n")
        for name, state in status.items():
            icon = "\u25cf" if state == "RUNNING" else "\u25cb"
            print(f"{icon} {name:<15} {state}")
        print()
    
    def cmd_nodes(self, args):
        try:
            from master_node.node_manager_cli import NodeManagerCLI
            cli = NodeManagerCLI()
            cli.list_nodes()
        except Exception as e:
            print(f"Node manager unavailable: {e}")
    
    def cmd_logs(self, args):
        service = args[0] if args else None
        
        if service:
            logs = self.log_manager.tail_logs(service, lines=20)
            print(f"\n=== Logs: {service} ===\n")
            for line in logs:
                print(line.strip())
        else:
            logs = self.log_manager.get_logs(limit=20)
            print("\n=== Recent Logs ===\n")
            for entry in logs:
                print(f"[{entry['service']}] {entry['message']}")
        print()
    
    def cmd_restart(self, args):
        if not args:
            print("Usage: restart <service>")
            return
        
        service = args[0]
        print(f"Restarting {service}...")
        self.service_manager.stop_service(service)
        time.sleep(1)
        success, msg = self.service_manager.start_service(service)
        print(msg)
    
    def cmd_service(self, args):
        if not args:
            print("Usage: service <start|stop|restart|status> [name]")
            return
        
        action = args[0]
        name = args[1] if len(args) > 1 else None
        
        if action == 'start' and name:
            success, msg = self.service_manager.start_service(name)
            print(msg)
        elif action == 'stop' and name:
            success, msg = self.service_manager.stop_service(name)
            print(msg)
        elif action == 'restart' and name:
            self.service_manager.stop_service(name)
            time.sleep(1)
            success, msg = self.service_manager.start_service(name)
            print(msg)
        elif action == 'status':
            status = self.service_manager.get_status(name)
            for n, state in status.items():
                print(f"{n}: {state}")
        else:
            print("Invalid service command")
    
    def cmd_node(self, args):
        try:
            from master_node.node_manager_cli import NodeManagerCLI
            cli = NodeManagerCLI()
            
            if not args:
                print("Usage: node <list|status|ping> [id]")
                return
            
            action = args[0]
            node_id = args[1] if len(args) > 1 else None
            
            if action == 'list':
                cli.list_nodes()
            elif action == 'status' and node_id:
                cli.node_status(node_id)
            elif action == 'ping' and node_id:
                cli.ping_node(node_id)
            else:
                print("Invalid node command")
        except Exception as e:
            print(f"Node manager unavailable: {e}")
    
    def cmd_shutdown(self, args):
        confirm = input("Shutdown HelioCore OS? (yes/no): ")
        if confirm.lower() == 'yes':
            from core.boot_manager import BootManager
            boot = BootManager()
            boot.shutdown()
            sys.exit(0)
    
    def cmd_health(self, args):
        from core.health_checker import HealthChecker
        health = HealthChecker()
        health.register_check('services', lambda: self.service_manager.get_status())
        
        result = health.get_overall_health()
        
        print("\n=== System Health Check ===\n")
        print(f"Overall Status: {result['status'].upper()}")
        print(f"Checks Passing: {result['healthy_checks']}/{result['total_checks']}")
        print()
        
        for check_name, check_result in result['checks'].items():
            if check_result:
                icon = "\u2713" if check_result['status'] == 'healthy' else "\u2717"
                print(f"{icon} {check_name}: {check_result['status']}")
        print()
    
    def cmd_clear(self, args):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def run(self):
        print("HelioCore OS Shell - Type 'help' for commands\n")
        
        while True:
            try:
                text = self.get_input('heliocore> ')
                
                if not text.strip():
                    continue
                
                parts = text.strip().split()
                cmd = parts[0]
                args = parts[1:]
                
                if cmd == 'exit':
                    break
                elif cmd in self.commands:
                    handler = self.commands[cmd]
                    if handler:
                        handler(args)
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")
            
            except KeyboardInterrupt:
                print("\nUse 'exit' or 'shutdown' to quit")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    shell = HelioCoreShell()
    shell.run()
