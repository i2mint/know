"""defines simulate_http_sensor"""

import requests


def simulate_http_sensor(filename, target_url):
    """Reads from a local file and sends it in binary format in an HTTP POST request.

    :param filename: The file to read
    :param target_url: The URL to send the data to.
    """
    with open(filename, 'rb') as fp:
        data = fp.read()
        response = requests.post(
            target_url, data=data, headers={'Content-type': 'application/octet-stream'}
        )
        print(f'response: {response}')
