import requests
import json

class NodeManagerCLI:
    def __init__(self, master_url='http://localhost:5001'):
        self.master_url = master_url
    
    def list_nodes(self):
        try:
            response = requests.get(f'{self.master_url}/node/list', timeout=2)
            if response.status_code == 200:
                nodes = response.json()['nodes']
                
                print("\nRegistered Nodes:")
                print("-" * 70)
                print(f"{'Node ID':<20} {'IP Address':<15} {'Status':<10} {'Last Heartbeat'}")
                print("-" * 70)
                
                for node in nodes:
                    print(f"{node['node_id']:<20} {node['ip']:<15} {node['status']:<10} {node['last_heartbeat']}")
                
                print(f"\nTotal nodes: {len(nodes)}")
        except Exception as e:
            print(f"Error: {e}")
    
    def node_status(self, node_id):
        try:
            response = requests.get(f'{self.master_url}/node/status/{node_id}', timeout=2)
            if response.status_code == 200:
                node = response.json()
                
                print(f"\nNode: {node['node_id']}")
                print("-" * 50)
                print(f"IP Address:      {node['ip']}")
                print(f"Hostname:        {node['hostname']}")
                print(f"Status:          {node['status']}")
                print(f"Last Heartbeat:  {node['last_heartbeat']}")
                print(f"Registered At:   {node['registered_at']}")
                
                if 'services' in node:
                    print("\nServices:")
                    for svc, status in node['services'].items():
                        print(f"  {svc:<15} {status}")
            else:
                print(f"Node {node_id} not found")
        except Exception as e:
            print(f"Error: {e}")
    
    def ping_node(self, node_id):
        try:
            response = requests.get(f'{self.master_url}/node/status/{node_id}', timeout=2)
            if response.status_code == 200:
                node = response.json()
                if node['status'] == 'online':
                    print(f"Node {node_id} is ONLINE")
                else:
                    print(f"Node {node_id} is OFFLINE")
            else:
                print(f"Node {node_id} not found")
        except Exception as e:
            print(f"Error: {e}")
