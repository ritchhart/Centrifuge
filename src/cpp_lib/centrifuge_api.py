# centrifuge_api.py
"""
Python API for both Centrifuge [6] and CentrifugeLoader [8].

Usage:
    from centrifuge_api import CentrifugeAPI, LoaderAPI

    cent = CentrifugeAPI()
    cent.initialize("Centrifuge profile")
    cent.spin(vel_percent=55, time_seconds=10)
    cent.close()

    loader = LoaderAPI()
    loader.initialize("Loader profile")
    loader.home()
    loader.load_plate(bucket_num=1, plate_height=14.5)
    loader.spin(vel_percent=55, time_seconds=10, bucket_num_load=1, bucket_num_unload=2)
    loader.unload_plate(bucket_num=2, plate_height=14.5)
    loader.close()
"""

import socket
import json


class _BaseAPI:
    def __init__(self, prefix, host='127.0.0.1', port=5555, timeout=120):
        self.prefix = prefix
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send(self, command, params=None):
        full_cmd = f"{self.prefix}.{command}" if self.prefix else command
        request = json.dumps({"command": full_cmd, "params": params or {}})
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
                raise DeviceError(result.get('error', 'Unknown error'))
            return result
        finally:
            sock.close()

    def ping(self):
        return self._send('ping')

    def info(self):
        return self._send('info')

    def enumerate_profiles(self):
        return self._send('profiles').get('profiles', [])

    def show_diagnostics(self, modal=False, security_level=0):
        return self._send('diagnostics', {
            'modal': modal, 'security_level': security_level})

    def initialize(self, profile_name):
        return self._send('initialize', {'profile_name': profile_name})

    def close(self):
        return self._send('close')

    def open_door(self, bucket_num=1):
        return self._send('open_door', {'bucket_num': bucket_num})

    def close_door(self):
        return self._send('close_door')

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


class CentrifugeAPI(_BaseAPI):
    """Direct centrifuge control [6]"""

    def __init__(self, **kwargs):
        super().__init__('centrifuge', **kwargs)

    def spin(self, vel_percent=50.0, accel_percent=100.0,
             decel_percent=100.0, timer_mode=0,
             time_seconds=60, bucket_num=1):
        """SpinCycle [6]: vel/accel/decel 1-100%, mode 0-2, time 1-86400s"""
        return self._send('spin', {
            'vel_percent': vel_percent, 'accel_percent': accel_percent,
            'decel_percent': decel_percent, 'timer_mode': timer_mode,
            'time_seconds': time_seconds, 'bucket_num': bucket_num})


class LoaderAPI(_BaseAPI):
    """Centrifuge with plate loader control [8]"""

    def __init__(self, **kwargs):
        super().__init__('loader', **kwargs)

    def home(self):
        """Home the loader mechanism [8]"""
        return self._send('home')

    def park(self):
        """Park the loader mechanism [8]"""
        return self._send('park')

    def load_plate(self, bucket_num=1, gripper_offset=0.0,
                   plate_height=0.0, speed=0, options=0):
        """Load a plate into the specified bucket [8]"""
        return self._send('load_plate', {
            'bucket_num': bucket_num, 'gripper_offset': gripper_offset,
            'plate_height': plate_height, 'speed': speed, 'options': options})

    def unload_plate(self, bucket_num=1, gripper_offset=0.0,
                     plate_height=0.0, speed=0, options=0):
        """Unload a plate from the specified bucket [8]"""
        return self._send('unload_plate', {
            'bucket_num': bucket_num, 'gripper_offset': gripper_offset,
            'plate_height': plate_height, 'speed': speed, 'options': options})

    def spin(self, vel_percent=50.0, accel_percent=100.0,
             decel_percent=100.0, timer_mode=0, time_seconds=60,
             bucket_num_load=1, bucket_num_unload=1,
             gripper_offset_load=0.0, gripper_offset_unload=0.0,
             plate_height_load=0.0, plate_height_unload=0.0,
             speed_load=0, speed_unload=0,
             load_options=0, unload_options=0):
        """Extended SpinCycle with load/unload parameters [8]"""
        return self._send('spin', {
            'vel_percent': vel_percent, 'accel_percent': accel_percent,
            'decel_percent': decel_percent, 'timer_mode': timer_mode,
            'time_seconds': time_seconds,
            'bucket_num_load': bucket_num_load,
            'bucket_num_unload': bucket_num_unload,
            'gripper_offset_load': gripper_offset_load,
            'gripper_offset_unload': gripper_offset_unload,
            'plate_height_load': plate_height_load,
            'plate_height_unload': plate_height_unload,
            'speed_load': speed_load, 'speed_unload': speed_unload,
            'load_options': load_options, 'unload_options': unload_options})


class DeviceError(Exception):
    pass


# ── Global convenience ──
def status(host='127.0.0.1', port=5555):
    """Get status of all devices"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((host, port))
        sock.sendall(json.dumps({"command": "status"}).encode('utf-8'))
        sock.shutdown(socket.SHUT_WR)
        data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.decode('utf-8'))
    finally:
        sock.close()