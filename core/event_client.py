import socket
import json
import threading

class EventClient:
    def __init__(self, socket_path='/tmp/heliocore/event_bus.sock'):
        self.socket_path = socket_path
        self.sock = None
        self.handlers = {}
        self.running = False
    
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        self.running = True
        threading.Thread(target=self._receive_loop, daemon=True).start()
    
    def subscribe(self, topic, handler):
        self.handlers[topic] = handler
        msg = json.dumps({'type': 'subscribe', 'topic': topic}) + '\n'
        self.sock.send(msg.encode())
    
    def publish(self, topic, data):
        msg = json.dumps({'type': 'publish', 'topic': topic, 'data': data}) + '\n'
        self.sock.send(msg.encode())
    
    def _receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    msg = json.loads(line)
                    
                    if msg['type'] == 'event':
                        topic = msg['topic']
                        if topic in self.handlers:
                            self.handlers[topic](msg['data'])
            except:
                break
    
    def disconnect(self):
        self.running = False
        if self.sock:
            self.sock.close()
