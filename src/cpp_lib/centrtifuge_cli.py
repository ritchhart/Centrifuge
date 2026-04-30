# centrifuge_cli.py
"""
Command-line client for Centrifuge + Loader server.

Usage:
    python centrifuge_cli.py ping
    python centrifuge_cli.py help
    python centrifuge_cli.py status

    # Centrifuge commands [6]
    python centrifuge_cli.py centrifuge.profiles
    python centrifuge_cli.py centrifuge.diagnostics
    python centrifuge_cli.py centrifuge.initialize -p "Centrifuge profile"
    python centrifuge_cli.py centrifuge.open_door -b 1
    python centrifuge_cli.py centrifuge.close_door
    python centrifuge_cli.py centrifuge.spin --vel 55 --accel 60 --decel 90 --mode 1 --time 10 --bucket 1
    python centrifuge_cli.py centrifuge.stop -b 1
    python centrifuge_cli.py centrifuge.close

    # Loader commands [8]
    python centrifuge_cli.py loader.profiles
    python centrifuge_cli.py loader.diagnostics
    python centrifuge_cli.py loader.initialize -p "Loader profile"
    python centrifuge_cli.py loader.home
    python centrifuge_cli.py loader.park
    python centrifuge_cli.py loader.open_door -b 1
    python centrifuge_cli.py loader.load_plate -b 1 --gripper-offset 0.0 --plate-height 14.5 --speed 0 --options 0
    python centrifuge_cli.py loader.unload_plate -b 1 --gripper-offset 0.0 --plate-height 14.5 --speed 0 --options 0
    python centrifuge_cli.py loader.spin --vel 55 --accel 60 --decel 90 --mode 1 --time 10 --bucket-load 1 --bucket-unload 1
    python centrifuge_cli.py loader.stop -b 1
    python centrifuge_cli.py loader.close
"""

import socket
import json
import argparse
import sys

HOST = '127.0.0.1'
PORT = 5555


def send_command(command, params=None, host=HOST, port=PORT, timeout=120):
    request = json.dumps({"command": command, "params": params or {}})
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.sendall(request.encode('utf-8'))
        sock.shutdown(socket.SHUT_WR)
        data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.decode('utf-8'))
    except ConnectionRefusedError:
        return {"status": "error",
                "error": "Cannot connect — is centrifuge_server.py running?"}
    except socket.timeout:
        return {"status": "error", "error": "Command timed out"}
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(
        description='Centrifuge + Loader CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('command', help='Command (e.g., centrifuge.spin, loader.load_plate)')
    parser.add_argument('-p', '--profile', help='Profile name')
    parser.add_argument('-b', '--bucket', type=int, default=1, help='Bucket number (1-2)')

    # Centrifuge spin params [6]
    parser.add_argument('--vel', type=float, default=50.0, help='Velocity %% (1-100)')
    parser.add_argument('--accel', type=float, default=100.0, help='Acceleration %% (1-100)')
    parser.add_argument('--decel', type=float, default=100.0, help='Deceleration %% (1-100)')
    parser.add_argument('--mode', type=int, default=0,
                        help='Timer mode: 0=total, 1=at_speed, 2=continuous')
    parser.add_argument('--time', type=int, default=60, help='Seconds (1-86400)')

    # Loader-specific params [8]
    parser.add_argument('--bucket-load', type=int, default=1, help='Load bucket (1-2)')
    parser.add_argument('--bucket-unload', type=int, default=1, help='Unload bucket (1-2)')
    parser.add_argument('--gripper-offset', type=float, default=0.0)
    parser.add_argument('--gripper-offset-load', type=float, default=0.0)
    parser.add_argument('--gripper-offset-unload', type=float, default=0.0)
    parser.add_argument('--plate-height', type=float, default=0.0)
    parser.add_argument('--plate-height-load', type=float, default=0.0)
    parser.add_argument('--plate-height-unload', type=float, default=0.0)
    parser.add_argument('--speed', type=int, default=0)
    parser.add_argument('--speed-load', type=int, default=0)
    parser.add_argument('--speed-unload', type=int, default=0)
    parser.add_argument('--options', type=int, default=0)
    parser.add_argument('--load-options', type=int, default=0)
    parser.add_argument('--unload-options', type=int, default=0)

    parser.add_argument('--host', default=HOST)
    parser.add_argument('--port', type=int, default=PORT)

    args = parser.parse_args()

    # Build params from command
    params = {}
    cmd = args.command
    subcmd = cmd.split('.')[-1] if '.' in cmd else cmd

    if subcmd == 'initialize':
        if not args.profile:
            print("Error: --profile required"); sys.exit(1)
        params['profile_name'] = args.profile

    elif subcmd in ('open_door', 'stop'):
        params['bucket_num'] = args.bucket

    elif subcmd == 'spin':
        if cmd.startswith('loader.'):
            # Extended spin [8]
            params = {
                'vel_percent': args.vel, 'accel_percent': args.accel,
                'decel_percent': args.decel, 'timer_mode': args.mode,
                'time_seconds': args.time,
                'bucket_num_load': args.bucket_load,
                'bucket_num_unload': args.bucket_unload,
                'gripper_offset_load': args.gripper_offset_load,
                'gripper_offset_unload': args.gripper_offset_unload,
                'plate_height_load': args.plate_height_load,
                'plate_height_unload': args.plate_height_unload,
                'speed_load': args.speed_load,
                'speed_unload': args.speed_unload,
                'load_options': args.load_options,
                'unload_options': args.unload_options,
            }
        else:
            # Simple spin [6]
            params = {
                'vel_percent': args.vel, 'accel_percent': args.accel,
                'decel_percent': args.decel, 'timer_mode': args.mode,
                'time_seconds': args.time, 'bucket_num': args.bucket,
            }

    elif subcmd in ('load_plate', 'unload_plate'):
        params = {
            'bucket_num': args.bucket,
            'gripper_offset': args.gripper_offset,
            'plate_height': args.plate_height,
            'speed': args.speed,
            'options': args.options,
        }

    result = send_command(cmd, params, args.host, args.port)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('status') == 'ok' else 1)


if __name__ == '__main__':
    main()