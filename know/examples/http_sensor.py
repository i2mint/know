from threading import Thread
from time import sleep
import sys

from flask import Flask
from know.http_sensor_sim import simulate_http_sensor
from flaskstream2py.flask_request_reader import FlaskRequestReader

app = Flask(__name__)


@app.route('/', methods=['POST'])
def handle_stream():
    print('received request')
    reader = FlaskRequestReader()
    reader.open()
    try:
        while True:
            chk = reader.read()
            print(f'chk: {str(chk)}')
    except:
        print('Request ended. Closing reader.')
        reader.close()
        return 'success'


def sensor_thread(filename=None):
    sleep(2)
    simulate_http_sensor(filename, 'http://127.0.0.1:5000')


if __name__ == '__main__':
    print(f'sys args: {sys.argv}')
    t = Thread(target=sensor_thread, args=sys.argv[1:])
    t.start()
    app.run()
