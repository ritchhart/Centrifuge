# centrifuge_server.py
"""
Hosts the Agilent Centrifuge ActiveX control in a wxPython window [6]
and exposes a TCP command interface for external control.

Run this once — it stays alive in the background.
Commands come in via TCP JSON messages on port 5555.
"""

import wx
import wx.lib.activex
import comtypes.client
import json
import socket
import threading
import queue
import time
import struct
import sys
import traceback

assert struct.calcsize('P') * 8 == 32, "Must use 32-bit Python!"

# ── Configuration ──
DLL_PATH = r"C:\Program Files (x86)\Agilent Technologies\VWorks ActiveX Controls\AgilentCentrifuge.dll"
CENTRIFUGE_CLSID = '{411EA0D8-D1A5-4183-B7CE-41C8951C990A}'
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555


class CentrifugeController:
    """Wraps the ActiveX control with thread-safe command dispatch"""

    def __init__(self, ax_ctrl):
        self.cent = ax_ctrl
        self.initialized = False
        self.profile_name = None

    def get_info(self):
        result = {}
        try:
            result['activex_version'] = self.cent.GetActiveXVersion()
        except Exception as e:
            result['activex_version'] = f"error: {e}"
        try:
            result['last_error'] = self.cent.GetLastError()
        except Exception as e:
            result['last_error'] = f"error: {e}"
        try:
            result['initialized'] = self.initialized
            result['profile'] = self.profile_name
        except:
            pass
        return result

    def enumerate_profiles(self):
        profiles = self.cent.EnumerateProfiles()
        if profiles is None:
            return []
        if isinstance(profiles, (list, tuple)):
            return list(profiles)
        # Handle VARIANT/SAFEARRAY
        try:
            return [str(p) for p in profiles]
        except:
            return [str(profiles)]

    def show_diagnostics(self, modal=False, security_level=0):
        """Opens vendor diagnostics UI for COM port configuration [6]"""
        self.cent.ShowDiagsDialog(modal, security_level)
        return {"status": "ok", "message": "Diagnostics dialog opened"}

    def initialize(self, profile_name):
        """Connect to centrifuge using named profile [6]"""
        self.cent.Blocking = True
        result = self.cent.Initialize(profile_name)
        if result == 0:
            self.initialized = True
            self.profile_name = profile_name
            hw_ver = ""
            try:
                hw_ver = self.cent.GetHardwareVersion()
            except:
                pass
            return {
                "status": "ok",
                "result": result,
                "hardware_version": hw_ver
            }
        else:
            error = self.cent.GetLastError()
            return {"status": "error", "result": result, "error": error}

    def close(self):
        """Disconnect from centrifuge [6]"""
        self.cent.Blocking = True
        result = self.cent.Close()
        self.initialized = False
        return {"status": "ok" if result == 0 else "error", "result": result}

    def open_door(self, bucket_num=1):
        """Open door — bucket_num: 1-2 [6]"""
        self.cent.Blocking = True
        result = self.cent.OpenDoor(bucket_num)
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.cent.GetLastError()}
        return {"status": "ok", "result": result}

    def close_door(self):
        """Close door [6]"""
        self.cent.Blocking = True
        result = self.cent.CloseDoor()
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.cent.GetLastError()}
        return {"status": "ok", "result": result}

    def spin_cycle(self, vel_percent=50.0, accel_percent=100.0,
                   decel_percent=100.0, timer_mode=0, time_seconds=60,
                   bucket_num=1):
        """
        Run spin cycle [6].
        vel_percent:   1-100 (% of max velocity)
        accel_percent: 1-100 (% of max acceleration)
        decel_percent: 1-100 (% of max deceleration)
        timer_mode:    0=TOTAL_TIME, 1=TIME_AT_SPEED, 2=CONTINUOUS
        time_seconds:  1-86400
        bucket_num:    1-2 (presented after spin)
        """
        self.cent.Blocking = True
        result = self.cent.SpinCycle(
            float(vel_percent), float(accel_percent), float(decel_percent),
            int(timer_mode), int(time_seconds), int(bucket_num)
        )
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.cent.GetLastError()}
        return {"status": "ok", "result": result}

    def stop_spin(self, bucket_num=1):
        """Emergency stop — bucket_num: 1-2 [6]"""
        self.cent.Blocking = True
        result = self.cent.StopSpinCycle(bucket_num)
        return {"status": "ok" if result == 0 else "error", "result": result}

    def abort(self):
        """Abort current error state [6]"""
        result = self.cent.Abort()
        return {"status": "ok" if result == 0 else "error", "result": result}

    def retry(self):
        """Retry last failed action [6]"""
        result = self.cent.Retry()
        return {"status": "ok" if result == 0 else "error", "result": result}

    def ignore_error(self):
        """Ignore current error and continue [6]"""
        result = self.cent.Ignore()
        return {"status": "ok" if result == 0 else "error", "result": result}

    def get_hardware_version(self):
        return {"hardware_version": self.cent.GetHardwareVersion()}

    def get_last_error(self):
        return {"last_error": self.cent.GetLastError()}

    def dispatch(self, command, params):
        """Route a command string to the appropriate method"""
        commands = {
            'info':           lambda p: self.get_info(),
            'profiles':       lambda p: {"profiles": self.enumerate_profiles()},
            'diagnostics':    lambda p: self.show_diagnostics(
                                  p.get('modal', False),
                                  p.get('security_level', 0)),
            'initialize':     lambda p: self.initialize(p['profile_name']),
            'close':          lambda p: self.close(),
            'open_door':      lambda p: self.open_door(p.get('bucket_num', 1)),
            'close_door':     lambda p: self.close_door(),
            'spin':           lambda p: self.spin_cycle(**{
                                  k: p[k] for k in p
                                  if k in ['vel_percent', 'accel_percent',
                                           'decel_percent', 'timer_mode',
                                           'time_seconds', 'bucket_num']}),
            'stop':           lambda p: self.stop_spin(p.get('bucket_num', 1)),
            'abort':          lambda p: self.abort(),
            'retry':          lambda p: self.retry(),
            'ignore':         lambda p: self.ignore_error(),
            'hardware_version': lambda p: self.get_hardware_version(),
            'last_error':     lambda p: self.get_last_error(),
            'ping':           lambda p: {"status": "ok", "message": "pong"},
        }

        if command not in commands:
            return {"status": "error",
                    "error": f"Unknown command: {command}",
                    "available": list(commands.keys())}

        return commands[command](params or {})


class TCPCommandServer(threading.Thread):
    """TCP server that accepts JSON commands and dispatches to ActiveX"""

    def __init__(self, controller, wx_app, host=SERVER_HOST, port=SERVER_PORT):
        super().__init__(daemon=True)
        self.controller = controller
        self.wx_app = wx_app
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(1.0)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"[SERVER] Listening on {self.host}:{self.port}")

        while self.running:
            try:
                client, addr = server.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(client, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[SERVER] Accept error: {e}")

        server.close()

    def handle_client(self, client, addr):
        try:
            data = b''
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Try to parse — supports single command per connection
                try:
                    request = json.loads(data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    continue  # Keep reading

            if not data:
                return

            request = json.loads(data.decode('utf-8'))
            command = request.get('command', '')
            params = request.get('params', {})

            # Dispatch to wx main thread and wait for result
            result_queue = queue.Queue()

            def do_command():
                try:
                    result = self.controller.dispatch(command, params)
                    result_queue.put(result)
                except Exception as e:
                    result_queue.put({
                        "status": "error",
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    })

            # Execute on the wx main thread (required for ActiveX) [6]
            wx.CallAfter(do_command)

            # Wait for result (timeout 120s for long spin cycles)
            try:
                result = result_queue.get(timeout=120)
            except queue.Empty:
                result = {"status": "error", "error": "Command timed out"}

            response = json.dumps(result, default=str)
            client.sendall(response.encode('utf-8'))

        except Exception as e:
            try:
                error_resp = json.dumps({"status": "error", "error": str(e)})
                client.sendall(error_resp.encode('utf-8'))
            except:
                pass
        finally:
            client.close()


class CentrifugeFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Centrifuge Server", size=(500, 300))

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Host ActiveX control [6]
        self.ax = wx.lib.activex.ActiveXCtrl(
            panel, CENTRIFUGE_CLSID, size=(1, 1)
        )
        sizer.Add(self.ax, 0)

        self.log_ctrl = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(480, 200)
        )
        sizer.Add(self.log_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_diags = wx.Button(panel, label="Open Diagnostics")
        btn_diags.Bind(wx.EVT_BUTTON, self.on_diags)
        btn_sizer.Add(btn_diags, 0, wx.ALL, 3)
        sizer.Add(btn_sizer)

        panel.SetSizer(sizer)

        # Create controller wrapper
        self.controller = CentrifugeController(self.ax.ctrl)
        self.log("ActiveX control hosted")

        # Start TCP server
        self.server = TCPCommandServer(self.controller, wx.GetApp())
        self.server.start()
        self.log(f"TCP command server on {SERVER_HOST}:{SERVER_PORT}")
        self.log("Ready for commands")

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def log(self, msg):
        self.log_ctrl.AppendText(f"{msg}\n")

    def on_diags(self, evt):
        try:
            self.controller.show_diagnostics(modal=False, security_level=0)
        except Exception as e:
            self.log(f"Diagnostics error: {e}")

    def on_close(self, evt):
        self.server.running = False
        try:
            self.controller.close()
        except:
            pass
        self.Destroy()


if __name__ == '__main__':
    comtypes.client.GetModule(DLL_PATH)
    app = wx.App()
    frame = CentrifugeFrame()
    frame.Show()
    print("[SERVER] Centrifuge server running. Close window to stop.")
    app.MainLoop()