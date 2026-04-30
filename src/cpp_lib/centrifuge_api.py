# centrifuge_api.py
"""
Python API for controlling the Agilent Centrifuge.
Connects to the centrifuge_server.py TCP interface.

Usage:
    from centrifuge_api import CentrifugeAPI
    
    cent = CentrifugeAPI()
    cent.initialize("Centrifuge profile")
    cent.open_door(1)
    cent.spin(vel_percent=55, time_seconds=10)
    cent.close()
"""

import socket
import json


class CentrifugeAPI:
    def __init__(self, host='127.0.0.1', port=5555, timeout=120):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send(self, command, params=None):
        request = json.dumps({"command": command, "params": params or {}})
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
            sock.sendall(request.encode('utf-8'))
            sock.shutdown(socket.SHUT_WR)
            data = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            result = json.loads(data.decode('utf-8'))
            if result.get('status') == 'error':
                raise CentrifugeError(result.get('error', 'Unknown error'))
            return result
        finally:
            sock.close()

    def ping(self):
        return self._send('ping')

    def info(self):
        return self._send('info')

    def enumerate_profiles(self):
        result = self._send('profiles')
        return result.get('profiles', [])

    def show_diagnostics(self, modal=False, security_level=0):
        """Open vendor diagnostics to configure COM port [6]"""
        return self._send('diagnostics', {
            'modal': modal, 'security_level': security_level
        })

    def initialize(self, profile_name):
        """Connect to centrifuge using named profile [6]"""
        return self._send('initialize', {'profile_name': profile_name})

    def close(self):
        return self._send('close')

    def open_door(self, bucket_num=1):
        """bucket_num: 1-2 [6]"""
        return self._send('open_door', {'bucket_num': bucket_num})

    def close_door(self):
        return self._send('close_door')

    def spin(self, vel_percent=50.0, accel_percent=100.0,
             decel_percent=100.0, timer_mode=0, time_seconds=60,
             bucket_num=1):
        """
        Run spin cycle [6].
        timer_mode: 0=TOTAL_TIME, 1=TIME_AT_SPEED, 2=CONTINUOUS
        vel/accel/decel: 1-100%, time: 1-86400s, bucket: 1-2
        """
        return self._send('spin', {
            'vel_percent': vel_percent,
            'accel_percent': accel_percent,
            'decel_percent': decel_percent,
            'timer_mode': timer_mode,
            'time_seconds': time_seconds,
            'bucket_num': bucket_num,
        })

    def stop(self, bucket_num=1):
        return self._send('stop', {'bucket_num': bucket_num})

    def abort(self):
        return self._send('abort')

    def retry(self):
        return self._send('retry')

    def ignore_error(self):
        return self._send('ignore')

    def get_last_error(self):
        return self._send('last_error')

    def get_hardware_version(self):
        return self._send('hardware_version')


class CentrifugeError(Exception):
    pass