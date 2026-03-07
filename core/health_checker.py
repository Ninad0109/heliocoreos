import time
from datetime import datetime

class HealthChecker:
    def __init__(self):
        self.checks = {}
        self.last_check = {}
    
    def register_check(self, name, check_func, interval=60):
        self.checks[name] = {
            'func': check_func,
            'interval': interval,
            'last_result': None
        }
    
    def run_checks(self):
        results = {}
        now = time.time()
        
        for name, check in self.checks.items():
            last_run = self.last_check.get(name, 0)
            
            if now - last_run >= check['interval']:
                try:
                    result = check['func']()
                    check['last_result'] = {
                        'status': 'healthy' if result else 'unhealthy',
                        'timestamp': datetime.now().isoformat(),
                        'details': result
                    }
                    self.last_check[name] = now
                except Exception as e:
                    check['last_result'] = {
                        'status': 'error',
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e)
                    }
            
            results[name] = check['last_result']
        
        return results
    
    def get_overall_health(self):
        results = self.run_checks()
        
        healthy = sum(1 for r in results.values() if r and r['status'] == 'healthy')
        total = len(results)
        
        return {
            'status': 'healthy' if healthy == total else 'degraded',
            'healthy_checks': healthy,
            'total_checks': total,
            'checks': results
        }
