import requests

def simulate_http_sensor(filename, target_url):
    with open(filename, 'rb') as fp:
        data = fp.read()
        response = requests.post(target_url, data=data, headers={'Content-type': 'application/octet-stream'})
        print(f'response: {response}')

