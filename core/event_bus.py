#!/usr/bin/env python3
import socket
import json
import threading
import os
from collections import defaultdict, deque

class EventBus:
    def __init__(self, socket_path='/tmp/heliocore/event_bus.sock'):
        self.socket_path = socket_path
        self.subscribers = defaultdict(list)
        self.event_history = deque(maxlen=100)
        self.running = False
        self.lock = threading.Lock()
        
        if os.path.exists(socket_path):
            os.remove(socket_path)
        
        os.makedirs(os.path.dirname(socket_path), exist_ok=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(socket_path)
        self.server.listen(10)
    
    def start(self):
        print("[EventBus] Starting...")
        self.running = True
        while self.running:
            try:
                client, _ = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
            except:
                break
    
    def handle_client(self, client):
        buffer = ""
        while self.running:
            try:
                data = client.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    msg = json.loads(line)
                    
                    if msg['type'] == 'subscribe':
                        with self.lock:
                            self.subscribers[msg['topic']].append(client)
                    
                    elif msg['type'] == 'publish':
                        self.publish_event(msg['topic'], msg['data'])
            except:
                break
        
        with self.lock:
            for topic in self.subscribers:
                if client in self.subscribers[topic]:
                    self.subscribers[topic].remove(client)
        client.close()
    
    def publish_event(self, topic, data):
        event = {'topic': topic, 'data': data}
        self.event_history.append(event)
        
        with self.lock:
            for client in self.subscribers.get(topic, []):
                try:
                    msg = json.dumps({'type': 'event', 'topic': topic, 'data': data}) + '\n'
                    client.send(msg.encode())
                except:
                    pass
    
    def stop(self):
        self.running = False
        self.server.close()
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

if __name__ == '__main__':
    import signal
    bus = EventBus()
    signal.signal(signal.SIGTERM, lambda s, f: bus.stop())
    bus.start()
