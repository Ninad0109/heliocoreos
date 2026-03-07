import os
import json
import time
from abc import ABC, abstractmethod

class ServiceBase(ABC):
    def __init__(self, name):
        self.name = name
        self.running = False
        self.state_dir = '/tmp/heliocore'
        os.makedirs(self.state_dir, exist_ok=True)
    
    def read_state(self, key):
        path = f'{self.state_dir}/{key}.json'
        try:
            with open(path) as f:
                return json.load(f)
        except:
            return None
    
    def write_state(self, key, data):
        path = f'{self.state_dir}/{key}.json'
        with open(path, 'w') as f:
            json.dump(data, f)
    
    @abstractmethod
    def initialize(self):
        pass
    
    @abstractmethod
    def run_loop(self):
        pass
    
    def start(self):
        print(f"[{self.name}] Starting...")
        self.running = True
        self.initialize()
        while self.running:
            try:
                self.run_loop()
            except Exception as e:
                print(f"[{self.name}] Error: {e}")
                time.sleep(1)
    
    def stop(self):
        self.running = False
        print(f"[{self.name}] Stopped")
