# centrifuge_server.py
"""
Hosts both the Agilent Centrifuge and CentrifugeLoader ActiveX controls
and exposes a TCP command interface for external control.

Commands are namespaced:
    centrifuge.*  — direct centrifuge control [6]
    loader.*      — centrifuge + plate loader control [8]
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
import traceback

assert struct.calcsize('P') * 8 == 32, "Must use 32-bit Python!"

# ── Configuration ──
ACTIVEX_DIR = r"C:\Program Files (x86)\Agilent Technologies\VWorks ActiveX Controls"
CENTRIFUGE_DLL = ACTIVEX_DIR + r"\AgilentCentrifuge.dll"
LOADER_DLL = ACTIVEX_DIR + r"\AgilentCentrifugeLoader.dll"

CENTRIFUGE_CLSID = '{411EA0D8-D1A5-4183-B7CE-41C8951C990A}'
LOADER_CLSID = '{A0E5DD8C-EBAB-414D-88C2-2578FD43B6B5}'

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555


# ══════════════════════════════════════════════════════════
# Controller: Centrifuge (original) [6]
# ══════════════════════════════════════════════════════════
class CentrifugeController:
    """Wraps the Centrifuge ActiveX control [6]"""

    def __init__(self, ax_ctrl):
        self.cent = ax_ctrl
        self.initialized = False
        self.profile_name = None

    def get_info(self):
        result = {'device': 'centrifuge', 'initialized': self.initialized,
                  'profile': self.profile_name}
        for key, call in [
            ('activex_version', lambda: self.cent.GetActiveXVersion()),
            ('hardware_version', lambda: self.cent.GetHardwareVersion() if self.initialized else 'N/A'),
            ('last_error', lambda: self.cent.GetLastError()),
        ]:
            try:
                result[key] = call()
            except Exception as e:
                result[key] = f"error: {e}"
        return result

    def enumerate_profiles(self):
        profiles = self.cent.EnumerateProfiles()
        if profiles is None:
            return []
        if isinstance(profiles, (list, tuple)):
            return list(profiles)
        try:
            return [str(p) for p in profiles]
        except:
            return [str(profiles)]

    def show_diagnostics(self, modal=False, security_level=0):
        self.cent.ShowDiagsDialog(modal, security_level)
        return {"status": "ok", "message": "Diagnostics dialog opened"}

    def initialize(self, profile_name):
        self.cent.Blocking = True
        result = self.cent.Initialize(profile_name)
        if result == 0:
            self.initialized = True
            self.profile_name = profile_name
            hw = ""
            try:
                hw = self.cent.GetHardwareVersion()
            except:
                pass
            return {"status": "ok", "result": result, "hardware_version": hw}
        else:
            return {"status": "error", "result": result,
                    "error": self.cent.GetLastError()}

    def close(self):
        self.cent.Blocking = True
        result = self.cent.Close()
        self.initialized = False
        return {"status": "ok" if result == 0 else "error", "result": result}

    def open_door(self, bucket_num=1):
        self.cent.Blocking = True
        result = self.cent.OpenDoor(bucket_num)
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.cent.GetLastError()}
        return {"status": "ok", "result": result}

    def close_door(self):
        self.cent.Blocking = True
        result = self.cent.CloseDoor()
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.cent.GetLastError()}
        return {"status": "ok", "result": result}

    def spin_cycle(self, vel_percent=50.0, accel_percent=100.0,
                   decel_percent=100.0, timer_mode=0,
                   time_seconds=60, bucket_num=1):
        """SpinCycle per [6]: vel/accel/decel 1-100%, timer_mode 0-2,
        time 1-86400s, bucket 1-2"""
        self.cent.Blocking = True
        result = self.cent.SpinCycle(
            float(vel_percent), float(accel_percent), float(decel_percent),
            int(timer_mode), int(time_seconds), int(bucket_num))
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.cent.GetLastError()}
        return {"status": "ok", "result": result}

    def stop_spin(self, bucket_num=1):
        self.cent.Blocking = True
        result = self.cent.StopSpinCycle(bucket_num)
        return {"status": "ok" if result == 0 else "error", "result": result}

    def abort(self):
        return {"status": "ok" if self.cent.Abort() == 0 else "error"}

    def retry(self):
        return {"status": "ok" if self.cent.Retry() == 0 else "error"}

    def ignore_error(self):
        return {"status": "ok" if self.cent.Ignore() == 0 else "error"}

    def dispatch(self, command, params):
        commands = {
            'info':         lambda p: self.get_info(),
            'profiles':     lambda p: {"profiles": self.enumerate_profiles()},
            'diagnostics':  lambda p: self.show_diagnostics(
                                p.get('modal', False), p.get('security_level', 0)),
            'initialize':   lambda p: self.initialize(p['profile_name']),
            'close':        lambda p: self.close(),
            'open_door':    lambda p: self.open_door(p.get('bucket_num', 1)),
            'close_door':   lambda p: self.close_door(),
            'spin':         lambda p: self.spin_cycle(**{
                                k: p[k] for k in p if k in
                                ['vel_percent', 'accel_percent', 'decel_percent',
                                 'timer_mode', 'time_seconds', 'bucket_num']}),
            'stop':         lambda p: self.stop_spin(p.get('bucket_num', 1)),
            'abort':        lambda p: self.abort(),
            'retry':        lambda p: self.retry(),
            'ignore':       lambda p: self.ignore_error(),
            'last_error':   lambda p: {"last_error": self.cent.GetLastError()},
        }
        if command not in commands:
            return {"status": "error", "error": f"Unknown centrifuge command: {command}",
                    "available": list(commands.keys())}
        return commands[command](params or {})


# ══════════════════════════════════════════════════════════
# Controller: CentrifugeLoader [8]
# ══════════════════════════════════════════════════════════
class LoaderController:
    """Wraps the CentrifugeLoader ActiveX control [8]"""

    def __init__(self, ax_ctrl):
        self.loader = ax_ctrl
        self.initialized = False
        self.profile_name = None

    def get_info(self):
        result = {'device': 'loader', 'initialized': self.initialized,
                  'profile': self.profile_name}
        for key, call in [
            ('activex_version', lambda: self.loader.GetActiveXVersion()),
            ('hardware_version', lambda: self.loader.GetHardwareVersion() if self.initialized else 'N/A'),
            ('centrifuge_activex_version',
             lambda: self.loader.GetCentrifugeActiveXVersion() if self.initialized else 'N/A'),
            ('centrifuge_hardware_version',
             lambda: self.loader.GetCentrifugeHardwareVersion() if self.initialized else 'N/A'),
            ('last_error', lambda: self.loader.GetLastError()),
        ]:
            try:
                result[key] = call()
            except Exception as e:
                result[key] = f"error: {e}"
        return result

    def enumerate_profiles(self):
        profiles = self.loader.EnumerateProfiles()
        if profiles is None:
            return []
        if isinstance(profiles, (list, tuple)):
            return list(profiles)
        try:
            return [str(p) for p in profiles]
        except:
            return [str(profiles)]

    def show_diagnostics(self, modal=False, security_level=0):
        self.loader.ShowDiagsDialog(modal, security_level)
        return {"status": "ok", "message": "Loader diagnostics dialog opened"}

    def initialize(self, profile_name):
        self.loader.Blocking = True
        result = self.loader.Initialize(profile_name)
        if result == 0:
            self.initialized = True
            self.profile_name = profile_name
            hw = ""
            try:
                hw = self.loader.GetHardwareVersion()
            except:
                pass
            return {"status": "ok", "result": result, "hardware_version": hw}
        else:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}

    def close(self):
        self.loader.Blocking = True
        result = self.loader.Close()
        self.initialized = False
        return {"status": "ok" if result == 0 else "error", "result": result}

    def home(self):
        """Home the loader mechanism [8]"""
        self.loader.Blocking = True
        result = self.loader.Home()
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}
        return {"status": "ok", "result": result}

    def park(self):
        """Park the loader mechanism [8]"""
        self.loader.Blocking = True
        result = self.loader.Park()
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}
        return {"status": "ok", "result": result}

    def open_door(self, bucket_num=1):
        self.loader.Blocking = True
        result = self.loader.OpenDoor(bucket_num)
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}
        return {"status": "ok", "result": result}

    def close_door(self):
        self.loader.Blocking = True
        result = self.loader.CloseDoor()
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}
        return {"status": "ok", "result": result}

    def load_plate(self, bucket_num=1, gripper_offset=0.0,
                   plate_height=0.0, speed=0, options=0):
        """Load a plate into a bucket [8]"""
        self.loader.Blocking = True
        result = self.loader.LoadPlate(
            int(bucket_num), float(gripper_offset),
            float(plate_height), int(speed), int(options))
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}
        return {"status": "ok", "result": result}

    def unload_plate(self, bucket_num=1, gripper_offset=0.0,
                     plate_height=0.0, speed=0, options=0):
        """Unload a plate from a bucket [8]"""
        self.loader.Blocking = True
        result = self.loader.UnloadPlate(
            int(bucket_num), float(gripper_offset),
            float(plate_height), int(speed), int(options))
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}
        return {"status": "ok", "result": result}

    def spin_cycle(self, vel_percent=50.0, accel_percent=100.0,
                   decel_percent=100.0, timer_mode=0, time_seconds=60,
                   bucket_num_load=1, bucket_num_unload=1,
                   gripper_offset_load=0.0, gripper_offset_unload=0.0,
                   plate_height_load=0.0, plate_height_unload=0.0,
                   speed_load=0, speed_unload=0,
                   load_options=0, unload_options=0):
        """Extended SpinCycle with load/unload parameters [8]"""
        self.loader.Blocking = True
        result = self.loader.SpinCycle(
            float(vel_percent), float(accel_percent), float(decel_percent),
            int(timer_mode), int(time_seconds),
            int(bucket_num_load), int(bucket_num_unload),
            float(gripper_offset_load), float(gripper_offset_unload),
            float(plate_height_load), float(plate_height_unload),
            int(speed_load), int(speed_unload),
            int(load_options), int(unload_options))
        if result != 0:
            return {"status": "error", "result": result,
                    "error": self.loader.GetLastError()}
        return {"status": "ok", "result": result}

    def stop_spin(self, bucket_num=1):
        self.loader.Blocking = True
        result = self.loader.StopSpinCycle(bucket_num)
        return {"status": "ok" if result == 0 else "error", "result": result}

    def abort(self):
        return {"status": "ok" if self.loader.Abort() == 0 else "error"}

    def retry(self):
        return {"status": "ok" if self.loader.Retry() == 0 else "error"}

    def ignore_error(self):
        return {"status": "ok" if self.loader.Ignore() == 0 else "error"}

    def dispatch(self, command, params):
        commands = {
            'info':         lambda p: self.get_info(),
            'profiles':     lambda p: {"profiles": self.enumerate_profiles()},
            'diagnostics':  lambda p: self.show_diagnostics(
                                p.get('modal', False), p.get('security_level', 0)),
            'initialize':   lambda p: self.initialize(p['profile_name']),
            'close':        lambda p: self.close(),
            'home':         lambda p: self.home(),
            'park':         lambda p: self.park(),
            'open_door':    lambda p: self.open_door(p.get('bucket_num', 1)),
            'close_door':   lambda p: self.close_door(),
            'load_plate':   lambda p: self.load_plate(**{
                                k: p[k] for k in p if k in
                                ['bucket_num', 'gripper_offset', 'plate_height',
                                 'speed', 'options']}),
            'unload_plate': lambda p: self.unload_plate(**{
                                k: p[k] for k in p if k in
                                ['bucket_num', 'gripper_offset', 'plate_height',
                                 'speed', 'options']}),
            'spin':         lambda p: self.spin_cycle(**{
                                k: p[k] for k in p if k in
                                ['vel_percent', 'accel_percent', 'decel_percent',
                                 'timer_mode', 'time_seconds',
                                 'bucket_num_load', 'bucket_num_unload',
                                 'gripper_offset_load', 'gripper_offset_unload',
                                 'plate_height_load', 'plate_height_unload',
                                 'speed_load', 'speed_unload',
                                 'load_options', 'unload_options']}),
            'stop':         lambda p: self.stop_spin(p.get('bucket_num', 1)),
            'abort':        lambda p: self.abort(),
            'retry':        lambda p: self.retry(),
            'ignore':       lambda p: self.ignore_error(),
            'last_error':   lambda p: {"last_error": self.loader.GetLastError()},
        }
        if command not in commands:
            return {"status": "error",
                    "error": f"Unknown loader command: {command}",
                    "available": list(commands.keys())}
        return commands[command](params or {})


# ══════════════════════════════════════════════════════════
# TCP Command Server
# ══════════════════════════════════════════════════════════
class TCPCommandServer(threading.Thread):
    """
    TCP server accepting JSON commands.
    Commands are namespaced: 'centrifuge.<cmd>' or 'loader.<cmd>'
    Global commands: 'ping', 'help', 'status'
    """

    def __init__(self, centrifuge_ctrl, loader_ctrl,
                 host=SERVER_HOST, port=SERVER_PORT):
        super().__init__(daemon=True)
        self.centrifuge = centrifuge_ctrl
        self.loader = loader_ctrl
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
                threading.Thread(target=self.handle_client,
                                 args=(client, addr), daemon=True).start()
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
                try:
                    json.loads(data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    continue

            if not data:
                return

            request = json.loads(data.decode('utf-8'))
            command = request.get('command', '')
            params = request.get('params', {})

            result_queue = queue.Queue()

            def do_command():
                try:
                    result = self.route_command(command, params)
                    result_queue.put(result)
                except Exception as e:
                    result_queue.put({"status": "error", "error": str(e),
                                      "traceback": traceback.format_exc()})

            wx.CallAfter(do_command)

            try:
                result = result_queue.get(timeout=120)
            except queue.Empty:
                result = {"status": "error", "error": "Command timed out"}

            client.sendall(json.dumps(result, default=str).encode('utf-8'))

        except Exception as e:
            try:
                client.sendall(json.dumps(
                    {"status": "error", "error": str(e)}).encode('utf-8'))
            except:
                pass
        finally:
            client.close()

    def route_command(self, command, params):
        """Route namespaced commands to the appropriate controller"""

        # Global commands
        if command == 'ping':
            return {"status": "ok", "message": "pong"}
        elif command == 'help':
            return {
                "status": "ok",
                "devices": {
                    "centrifuge": [
                        "info", "profiles", "diagnostics", "initialize",
                        "close", "open_door", "close_door", "spin",
                        "stop", "abort", "retry", "ignore", "last_error"
                    ],
                    "loader": [
                        "info", "profiles", "diagnostics", "initialize",
                        "close", "home", "park", "open_door", "close_door",
                        "load_plate", "unload_plate", "spin", "stop",
                        "abort", "retry", "ignore", "last_error"
                    ]
                },
                "usage": "Commands are namespaced: 'centrifuge.spin', 'loader.load_plate', etc.",
                "global": ["ping", "help", "status"]
            }
        elif command == 'status':
            result = {"status": "ok"}
            try:
                result['centrifuge'] = self.centrifuge.get_info()
            except Exception as e:
                result['centrifuge'] = {"error": str(e)}
            try:
                result['loader'] = self.loader.get_info()
            except Exception as e:
                result['loader'] = {"error": str(e)}
            return result

        # Namespaced commands
        if '.' in command:
            device, cmd = command.split('.', 1)
            if device == 'centrifuge' and self.centrifuge:
                return self.centrifuge.dispatch(cmd, params)
            elif device == 'loader' and self.loader:
                return self.loader.dispatch(cmd, params)
            else:
                return {"status": "error",
                        "error": f"Unknown device: {device}",
                        "available_devices": ["centrifuge", "loader"]}

        # Fallback: try centrifuge first for backward compatibility
        if self.centrifuge:
            try:
                return self.centrifuge.dispatch(command, params)
            except:
                pass

        return {"status": "error",
                "error": f"Unknown command: {command}. Use 'help' for available commands."}


# ══════════════════════════════════════════════════════════
# wxPython Frame — hosts both ActiveX controls
# ══════════════════════════════════════════════════════════
class CentrifugeFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Centrifuge + Loader Server",
                         size=(600, 400))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # ── Host Centrifuge ActiveX [6] ──
        self.centrifuge_ctrl = None
        try:
            self.ax_cent = wx.lib.activex.ActiveXCtrl(
                panel, CENTRIFUGE_CLSID, size=(1, 1))
            self.centrifuge_ctrl = CentrifugeController(self.ax_cent.ctrl)
            sizer.Add(self.ax_cent, 0)
            cent_status = "Centrifuge ActiveX: OK"
        except Exception as e:
            cent_status = f"Centrifuge ActiveX FAILED: {e}"

        # ── Host CentrifugeLoader ActiveX [8] ──
        self.loader_ctrl = None
        try:
            self.ax_loader = wx.lib.activex.ActiveXCtrl(
                panel, LOADER_CLSID, size=(1, 1))
            self.loader_ctrl = LoaderController(self.ax_loader.ctrl)
            sizer.Add(self.ax_loader, 0)
            loader_status = "Loader ActiveX: OK"
        except Exception as e:
            loader_status = f"Loader ActiveX FAILED: {e}"

        # ── Log display ──
        self.log_ctrl = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(580, 220))
        sizer.Add(self.log_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        # ── Buttons ──
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [
            ("Centrifuge Diags", self.on_cent_diags),
            ("Loader Diags", self.on_loader_diags),
            ("Status", self.on_status),
        ]:
            btn = wx.Button(panel, label=label)
            btn.Bind(wx.EVT_BUTTON, handler)
            btn_sizer.Add(btn, 0, wx.ALL, 3)
        sizer.Add(btn_sizer)

        panel.SetSizer(sizer)

        self.log(cent_status)
        self.log(loader_status)

        # ── Start TCP server ──
        self.server = TCPCommandServer(
            self.centrifuge_ctrl, self.loader_ctrl)
        self.server.start()
        self.log(f"TCP server on {SERVER_HOST}:{SERVER_PORT}")
        self.log("Ready — use 'help' command for available commands")

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def log(self, msg):
        self.log_ctrl.AppendText(f"{msg}\n")

    def on_cent_diags(self, evt):
        if self.centrifuge_ctrl:
            try:
                self.centrifuge_ctrl.show_diagnostics(modal=False)
            except Exception as e:
                self.log(f"Centrifuge diags error: {e}")

    def on_loader_diags(self, evt):
        if self.loader_ctrl:
            try:
                self.loader_ctrl.show_diagnostics(modal=False)
            except Exception as e:
                self.log(f"Loader diags error: {e}")

    def on_status(self, evt):
        for name, ctrl in [("Centrifuge", self.centrifuge_ctrl),
                           ("Loader", self.loader_ctrl)]:
            if ctrl:
                try:
                    info = ctrl.get_info()
                    self.log(f"{name}: {json.dumps(info, default=str)}")
                except Exception as e:
                    self.log(f"{name} error: {e}")

    def on_close(self, evt):
        self.server.running = False
        for ctrl in [self.centrifuge_ctrl, self.loader_ctrl]:
            if ctrl:
                try:
                    ctrl.close()
                except:
                    pass
        self.Destroy()


if __name__ == '__main__':
    # Generate type libraries
    comtypes.client.GetModule(CENTRIFUGE_DLL)
    comtypes.client.GetModule(LOADER_DLL)

    app = wx.App()
    frame = CentrifugeFrame()
    frame.Show()
    print("[SERVER] Centrifuge + Loader server running.")
    app.MainLoop()