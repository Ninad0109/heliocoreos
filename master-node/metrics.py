import requests

def get_current_metrics(base_url='http://localhost:5000'):
    try:
        response = requests.get(f'{base_url}/status', timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None
