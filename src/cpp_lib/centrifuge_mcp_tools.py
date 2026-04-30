# centrifuge_mcp_tools.py
"""
MCP tool definitions for Agilent Centrifuge [6] and CentrifugeLoader [8].
Connects to centrifuge_server.py via TCP on localhost:5555.

Each function is a self-contained tool that an MCP agent can call.
All return JSON-serializable dicts with a 'status' field.
"""

from centrifuge_api import CentrifugeAPI, LoaderAPI, status as _status, DeviceError


# ══════════════════════════════════════════════════════════
# Global / System Tools
# ══════════════════════════════════════════════════════════

def system_ping() -> dict:
    """Ping the centrifuge server to verify it is running and reachable."""
    try:
        cent = CentrifugeAPI()
        return cent.ping()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def system_status() -> dict:
    """Get the status of all connected devices (centrifuge and loader),
    including initialization state, profile names, and version info."""
    try:
        return _status()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def system_help() -> dict:
    """List all available commands for both the centrifuge and loader."""
    import socket, json
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect(('127.0.0.1', 5555))
        sock.sendall(json.dumps({"command": "help"}).encode('utf-8'))
        sock.shutdown(socket.SHUT_WR)
        data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        sock.close()


# ══════════════════════════════════════════════════════════
# Centrifuge Tools [6]
# ══════════════════════════════════════════════════════════

def centrifuge_info() -> dict:
    """Get centrifuge status including ActiveX version, hardware version,
    initialization state, active profile, and last error."""
    try:
        return CentrifugeAPI().info()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_list_profiles() -> list:
    """List available configuration profiles for the centrifuge.
    Profiles contain COM port and connection settings configured
    via the diagnostics dialog."""
    try:
        return CentrifugeAPI().enumerate_profiles()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_show_diagnostics(modal: bool = False,
                                 security_level: int = 0) -> dict:
    """Open the vendor diagnostics dialog for the centrifuge.
    Use this to configure COM port settings and create profiles.
    Args:
        modal: If True, blocks until dialog closes.
        security_level: 0=Admin, 1=Technician, 2=Operator, 3=Guest, -1=No access
    """
    try:
        return CentrifugeAPI().show_diagnostics(modal, security_level)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_initialize(profile_name: str) -> dict:
    """Connect to the centrifuge using a named profile.
    The profile specifies the serial port and connection parameters.
    Call centrifuge_list_profiles() first to get available names.
    Args:
        profile_name: Name of the profile to use for initialization.
    """
    try:
        return CentrifugeAPI().initialize(profile_name)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_close() -> dict:
    """Disconnect from the centrifuge and release the serial port."""
    try:
        return CentrifugeAPI().close()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_open_door(bucket_num: int = 1) -> dict:
    """Open the centrifuge door to access a bucket.
    Args:
        bucket_num: Which bucket to present (1 or 2).
    """
    try:
        return CentrifugeAPI().open_door(bucket_num)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_close_door() -> dict:
    """Close the centrifuge door."""
    try:
        return CentrifugeAPI().close_door()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_spin(vel_percent: float = 50.0,
                     accel_percent: float = 100.0,
                     decel_percent: float = 100.0,
                     timer_mode: int = 0,
                     time_seconds: int = 60,
                     bucket_num: int = 1) -> dict:
    """Run a centrifuge spin cycle.
    Args:
        vel_percent: Speed as percentage of maximum (1-100).
        accel_percent: Acceleration as percentage of maximum (1-100).
        decel_percent: Deceleration/braking as percentage of maximum (1-100).
        timer_mode: 0=total cycle time, 1=time at full speed, 2=spin continuously until stopped.
        time_seconds: Duration in seconds (1-86400). Ignored if timer_mode=2.
        bucket_num: Which bucket to present after spin completes (1 or 2).
    """
    try:
        return CentrifugeAPI().spin(
            vel_percent, accel_percent, decel_percent,
            timer_mode, time_seconds, bucket_num)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_stop(bucket_num: int = 1) -> dict:
    """Emergency stop the centrifuge and open door to specified bucket.
    Args:
        bucket_num: Which bucket to present after stopping (1 or 2).
    """
    try:
        return CentrifugeAPI().stop(bucket_num)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_abort() -> dict:
    """Abort the current task that is in an error state and clear the error."""
    try:
        return CentrifugeAPI().abort()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_retry() -> dict:
    """Retry the last action that resulted in an error."""
    try:
        return CentrifugeAPI().retry()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_ignore_error() -> dict:
    """Ignore the current error and proceed to the next step.
    WARNING: Use with caution — errors exist for a reason."""
    try:
        return CentrifugeAPI().ignore_error()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def centrifuge_get_last_error() -> dict:
    """Get the last error message from the centrifuge."""
    try:
        return CentrifugeAPI().get_last_error()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


# ══════════════════════════════════════════════════════════
# CentrifugeLoader Tools [8]
# ══════════════════════════════════════════════════════════

def loader_info() -> dict:
    """Get loader status including ActiveX version, firmware version,
    hardware version, underlying centrifuge versions, initialization
    state, active profile, and last error."""
    try:
        return LoaderAPI().info()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_list_profiles() -> list:
    """List available configuration profiles for the centrifuge loader."""
    try:
        return LoaderAPI().enumerate_profiles()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_show_diagnostics(modal: bool = False,
                             security_level: int = 0) -> dict:
    """Open the vendor diagnostics dialog for the centrifuge loader.
    Use this to configure COM port settings and create profiles.
    Args:
        modal: If True, blocks until dialog closes.
        security_level: 0=Admin, 1=Technician, 2=Operator, 3=Guest, -1=No access
    """
    try:
        return LoaderAPI().show_diagnostics(modal, security_level)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_initialize(profile_name: str) -> dict:
    """Connect to the centrifuge loader using a named profile.
    The profile specifies COM port settings for both the loader and
    the underlying centrifuge.
    Args:
        profile_name: Name of the profile to use.
    """
    try:
        return LoaderAPI().initialize(profile_name)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_close() -> dict:
    """Disconnect from the centrifuge loader."""
    try:
        return LoaderAPI().close()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_home() -> dict:
    """Home the loader mechanism. This moves the loader to its
    reference/home position. Should be called after initialization."""
    try:
        return LoaderAPI().home()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_park() -> dict:
    """Park the loader mechanism. Moves the loader to its parked/stowed
    position. Call before disconnecting."""
    try:
        return LoaderAPI().park()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_open_door(bucket_num: int = 1) -> dict:
    """Open the centrifuge door via the loader to access a bucket.
    Args:
        bucket_num: Which bucket to present (1 or 2).
    """
    try:
        return LoaderAPI().open_door(bucket_num)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_close_door() -> dict:
    """Close the centrifuge door via the loader."""
    try:
        return LoaderAPI().close_door()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_load_plate(bucket_num: int = 1,
                       gripper_offset: float = 0.0,
                       plate_height: float = 0.0,
                       speed: int = 0,
                       options: int = 0) -> dict:
    """Load a microplate into a centrifuge bucket using the loader arm.
    Args:
        bucket_num: Target bucket (1 or 2).
        gripper_offset: Gripper position offset for plate pickup.
        plate_height: Height of the microplate being loaded.
        speed: Movement speed setting (0 for default).
        options: Additional load options flags.
    """
    try:
        return LoaderAPI().load_plate(
            bucket_num, gripper_offset, plate_height, speed, options)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_unload_plate(bucket_num: int = 1,
                         gripper_offset: float = 0.0,
                         plate_height: float = 0.0,
                         speed: int = 0,
                         options: int = 0) -> dict:
    """Unload a microplate from a centrifuge bucket using the loader arm.
    Args:
        bucket_num: Source bucket (1 or 2).
        gripper_offset: Gripper position offset for plate placement.
        plate_height: Height of the microplate being unloaded.
        speed: Movement speed setting (0 for default).
        options: Additional unload options flags.
    """
    try:
        return LoaderAPI().unload_plate(
            bucket_num, gripper_offset, plate_height, speed, options)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_spin(vel_percent: float = 50.0,
                 accel_percent: float = 100.0,
                 decel_percent: float = 100.0,
                 timer_mode: int = 0,
                 time_seconds: int = 60,
                 bucket_num_load: int = 1,
                 bucket_num_unload: int = 1,
                 gripper_offset_load: float = 0.0,
                 gripper_offset_unload: float = 0.0,
                 plate_height_load: float = 0.0,
                 plate_height_unload: float = 0.0,
                 speed_load: int = 0,
                 speed_unload: int = 0,
                 load_options: int = 0,
                 unload_options: int = 0) -> dict:
    """Run a full spin cycle with automatic plate load and unload.
    This is the extended loader version that handles the complete
    load-spin-unload workflow.
    Args:
        vel_percent: Speed as percentage of maximum (1-100).
        accel_percent: Acceleration as percentage of maximum (1-100).
        decel_percent: Deceleration/braking as percentage of maximum (1-100).
        timer_mode: 0=total cycle time, 1=time at full speed, 2=continuous.
        time_seconds: Duration in seconds (1-86400).
        bucket_num_load: Bucket to load plate into before spinning (1 or 2).
        bucket_num_unload: Bucket to unload plate from after spinning (1 or 2).
        gripper_offset_load: Gripper offset for loading.
        gripper_offset_unload: Gripper offset for unloading.
        plate_height_load: Plate height for loading.
        plate_height_unload: Plate height for unloading.
        speed_load: Loader speed for loading (0=default).
        speed_unload: Loader speed for unloading (0=default).
        load_options: Additional load option flags.
        unload_options: Additional unload option flags.
    """
    try:
        return LoaderAPI().spin(
            vel_percent, accel_percent, decel_percent,
            timer_mode, time_seconds,
            bucket_num_load, bucket_num_unload,
            gripper_offset_load, gripper_offset_unload,
            plate_height_load, plate_height_unload,
            speed_load, speed_unload,
            load_options, unload_options)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_stop(bucket_num: int = 1) -> dict:
    """Emergency stop the centrifuge via the loader and open door.
    Args:
        bucket_num: Which bucket to present after stopping (1 or 2).
    """
    try:
        return LoaderAPI().stop(bucket_num)
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_abort() -> dict:
    """Abort the current loader task that is in an error state."""
    try:
        return LoaderAPI().abort()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_retry() -> dict:
    """Retry the last loader action that resulted in an error."""
    try:
        return LoaderAPI().retry()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_ignore_error() -> dict:
    """Ignore the current loader error and proceed.
    WARNING: Use with caution."""
    try:
        return LoaderAPI().ignore_error()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_get_last_error() -> dict:
    """Get the last error message from the centrifuge loader."""
    try:
        return LoaderAPI().get_last_error()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_get_firmware_version() -> dict:
    """Get the loader firmware version."""
    try:
        return LoaderAPI().get_firmware_version()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}


def loader_get_centrifuge_versions() -> dict:
    """Get the underlying centrifuge ActiveX and hardware versions
    as reported through the loader."""
    try:
        return LoaderAPI().get_centrifuge_versions()
    except DeviceError as e:
        return {"status": "error", "error": str(e)}