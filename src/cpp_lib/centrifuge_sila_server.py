# centrifuge_sila_server.py
"""
SiLA 2 Server for Agilent Centrifuge [6] and CentrifugeLoader [8].
Maps all centrifuge_api.py functions to SiLA 2 commands.
Requires centrifuge_server.py to be running on localhost:5555.
"""

import asyncio
import logging
from sila.server import (
    Server, ServerConfig, Feature, UnobservableCommand,
    Boolean, String, Integer, Real, List, Structure, Custom
)
from sila import Element
from src.cpp_lib.centrifuge_api import CentrifugeAPI, LoaderAPI, status as system_status, DeviceError

logging.basicConfig(level=logging.INFO)

# ══════════════════════════════════════════════════════════
# Feature Definitions
# ══════════════════════════════════════════════════════════

system_feature = Feature(
    identifier="SystemControl",
    display_name="System Control"
)

centrifuge_feature = Feature(
    identifier="CentrifugeControl",
    display_name="Centrifuge Control"
)

loader_feature = Feature(
    identifier="LoaderControl",
    display_name="Centrifuge Loader Control"
)

# ══════════════════════════════════════════════════════════
# System Commands
# ══════════════════════════════════════════════════════════

def _ping(metadata):
    """Ping the centrifuge server to verify connectivity."""
    try:
        cent = CentrifugeAPI()
        result = cent.ping()
        return {"response": str(result)}
    except Exception as e:
        return {"response": f"error: {str(e)}"}


ping_command = UnobservableCommand(
    identifier="Ping",
    display_name="Ping",
    description="Ping the centrifuge server to verify it is running and reachable.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Server ping response",
            data_type=String
        )
    },
    function=_ping,
    feature=system_feature
)


def _get_status(metadata):
    """Get status of all connected devices."""
    try:
        result = system_status()
        return {"response": str(result)}
    except Exception as e:
        return {"response": f"error: {str(e)}"}


status_command = UnobservableCommand(
    identifier="GetStatus",
    display_name="Get Status",
    description="Get the status of all connected devices (centrifuge and loader).",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Device status information",
            data_type=String
        )
    },
    function=_get_status,
    feature=system_feature
)

# ══════════════════════════════════════════════════════════
# Centrifuge Commands [6]
# ══════════════════════════════════════════════════════════

def _centrifuge_initialize(profile_name, metadata):
    """Initialize the centrifuge with the given profile."""
    try:
        result = CentrifugeAPI().initialize(profile_name)
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_initialize_command = UnobservableCommand(
    identifier="CentrifugeInitialize",
    display_name="Initialize Centrifuge",
    description="Initialize the centrifuge with a named profile.",
    parameters={
        "profile_name": Element(
            identifier="ProfileName",
            display_name="Profile Name",
            description="Name of the centrifuge profile to initialize with",
            data_type=String
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Initialization result",
            data_type=String
        )
    },
    function=_centrifuge_initialize,
    feature=centrifuge_feature
)


def _centrifuge_close(metadata):
    """Disconnect from the centrifuge and release the serial port."""
    try:
        result = CentrifugeAPI().close()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_close_command = UnobservableCommand(
    identifier="CentrifugeClose",
    display_name="Close Centrifuge",
    description="Disconnect from the centrifuge and release the serial port.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Close result",
            data_type=String
        )
    },
    function=_centrifuge_close,
    feature=centrifuge_feature
)


def _centrifuge_open_door(bucket_num, metadata):
    """Open the centrifuge door to access a bucket."""
    try:
        result = CentrifugeAPI().open_door(int(bucket_num))
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_open_door_command = UnobservableCommand(
    identifier="CentrifugeOpenDoor",
    display_name="Open Centrifuge Door",
    description="Open the centrifuge door to access a specific bucket (1 or 2).",
    parameters={
        "bucket_num": Element(
            identifier="BucketNum",
            display_name="Bucket Number",
            description="Which bucket to present (1 or 2)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Open door result",
            data_type=String
        )
    },
    function=_centrifuge_open_door,
    feature=centrifuge_feature
)


def _centrifuge_close_door(metadata):
    """Close the centrifuge door."""
    try:
        result = CentrifugeAPI().close_door()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_close_door_command = UnobservableCommand(
    identifier="CentrifugeCloseDoor",
    display_name="Close Centrifuge Door",
    description="Close the centrifuge door.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Close door result",
            data_type=String
        )
    },
    function=_centrifuge_close_door,
    feature=centrifuge_feature
)


def _centrifuge_spin(vel_percent, accel_percent, decel_percent,
                     timer_mode, time_seconds, bucket_num, metadata):
    """Run a centrifuge spin cycle."""
    try:
        result = CentrifugeAPI().spin(
            vel_percent=float(vel_percent),
            accel_percent=float(accel_percent),
            decel_percent=float(decel_percent),
            timer_mode=int(timer_mode),
            time_seconds=int(time_seconds),
            bucket_num=int(bucket_num)
        )
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_spin_command = UnobservableCommand(
    identifier="CentrifugeSpin",
    display_name="Centrifuge Spin",
    description="Run a centrifuge spin cycle with specified parameters.",
    parameters={
        "vel_percent": Element(
            identifier="VelocityPercent",
            display_name="Velocity %",
            description="Speed as percentage of maximum (1-100)",
            data_type=Real
        ),
        "accel_percent": Element(
            identifier="AccelerationPercent",
            display_name="Acceleration %",
            description="Acceleration as percentage of maximum (1-100)",
            data_type=Real
        ),
        "decel_percent": Element(
            identifier="DecelerationPercent",
            display_name="Deceleration %",
            description="Deceleration/braking as percentage of maximum (1-100)",
            data_type=Real
        ),
        "timer_mode": Element(
            identifier="TimerMode",
            display_name="Timer Mode",
            description="0=total cycle time, 1=time at full speed, 2=spin continuously",
            data_type=Integer
        ),
        "time_seconds": Element(
            identifier="TimeSeconds",
            display_name="Time (seconds)",
            description="Duration in seconds (1-86400). Ignored if timer_mode=2.",
            data_type=Integer
        ),
        "bucket_num": Element(
            identifier="BucketNum",
            display_name="Bucket Number",
            description="Which bucket to present after spin completes (1 or 2)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Spin result",
            data_type=String
        )
    },
    function=_centrifuge_spin,
    feature=centrifuge_feature
)


def _centrifuge_stop(bucket_num, metadata):
    """Stop the centrifuge."""
    try:
        result = CentrifugeAPI().stop(int(bucket_num))
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_stop_command = UnobservableCommand(
    identifier="CentrifugeStop",
    display_name="Stop Centrifuge",
    description="Stop the centrifuge and present the specified bucket.",
    parameters={
        "bucket_num": Element(
            identifier="BucketNum",
            display_name="Bucket Number",
            description="Which bucket to present after stopping (1 or 2)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Stop result",
            data_type=String
        )
    },
    function=_centrifuge_stop,
    feature=centrifuge_feature
)


def _centrifuge_abort(metadata):
    """Abort the current centrifuge operation."""
    try:
        result = CentrifugeAPI().abort()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_abort_command = UnobservableCommand(
    identifier="CentrifugeAbort",
    display_name="Abort Centrifuge",
    description="Abort the current centrifuge operation immediately.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Abort result",
            data_type=String
        )
    },
    function=_centrifuge_abort,
    feature=centrifuge_feature
)


def _centrifuge_profiles(metadata):
    """List available centrifuge profiles."""
    try:
        profiles = CentrifugeAPI().enumerate_profiles()
        return {"response": str(profiles)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_profiles_command = UnobservableCommand(
    identifier="CentrifugeProfiles",
    display_name="List Centrifuge Profiles",
    description="Enumerate all available centrifuge profiles.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="List of available profiles",
            data_type=String
        )
    },
    function=_centrifuge_profiles,
    feature=centrifuge_feature
)


def _centrifuge_diagnostics(metadata):
    """Show centrifuge diagnostics."""
    try:
        result = CentrifugeAPI().show_diagnostics()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_diagnostics_command = UnobservableCommand(
    identifier="CentrifugeDiagnostics",
    display_name="Centrifuge Diagnostics",
    description="Show the centrifuge diagnostics dialog.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Diagnostics result",
            data_type=String
        )
    },
    function=_centrifuge_diagnostics,
    feature=centrifuge_feature
)


def _centrifuge_info(metadata):
    """Get centrifuge device info."""
    try:
        result = CentrifugeAPI().info()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_info_command = UnobservableCommand(
    identifier="CentrifugeInfo",
    display_name="Centrifuge Info",
    description="Get centrifuge device information.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Device info",
            data_type=String
        )
    },
    function=_centrifuge_info,
    feature=centrifuge_feature
)


def _centrifuge_retry(metadata):
    """Retry the last failed centrifuge operation."""
    try:
        result = CentrifugeAPI().retry()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_retry_command = UnobservableCommand(
    identifier="CentrifugeRetry",
    display_name="Centrifuge Retry",
    description="Retry the last failed centrifuge operation.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Retry result",
            data_type=String
        )
    },
    function=_centrifuge_retry,
    feature=centrifuge_feature
)


def _centrifuge_ignore_error(metadata):
    """Ignore the current centrifuge error and continue."""
    try:
        result = CentrifugeAPI().ignore_error()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_ignore_error_command = UnobservableCommand(
    identifier="CentrifugeIgnoreError",
    display_name="Centrifuge Ignore Error",
    description="Ignore the current centrifuge error and continue.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Ignore error result",
            data_type=String
        )
    },
    function=_centrifuge_ignore_error,
    feature=centrifuge_feature
)


def _centrifuge_last_error(metadata):
    """Get the last centrifuge error."""
    try:
        result = CentrifugeAPI().get_last_error()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


centrifuge_last_error_command = UnobservableCommand(
    identifier="CentrifugeLastError",
    display_name="Centrifuge Last Error",
    description="Get the last error from the centrifuge.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Last error information",
            data_type=String
        )
    },
    function=_centrifuge_last_error,
    feature=centrifuge_feature
)

# ══════════════════════════════════════════════════════════
# Loader Commands [8]
# ══════════════════════════════════════════════════════════

def _loader_initialize(profile_name, metadata):
    """Initialize the loader with the given profile."""
    try:
        result = LoaderAPI().initialize(profile_name)
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_initialize_command = UnobservableCommand(
    identifier="LoaderInitialize",
    display_name="Initialize Loader",
    description="Initialize the centrifuge loader with a named profile.",
    parameters={
        "profile_name": Element(
            identifier="ProfileName",
            display_name="Profile Name",
            description="Name of the loader profile to initialize with",
            data_type=String
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Initialization result",
            data_type=String
        )
    },
    function=_loader_initialize,
    feature=loader_feature
)


def _loader_close(metadata):
    """Disconnect from the loader."""
    try:
        result = LoaderAPI().close()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_close_command = UnobservableCommand(
    identifier="LoaderClose",
    display_name="Close Loader",
    description="Disconnect from the loader and release resources.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Close result",
            data_type=String
        )
    },
    function=_loader_close,
    feature=loader_feature
)


def _loader_home(metadata):
    """Home the loader mechanism."""
    try:
        result = LoaderAPI().home()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_home_command = UnobservableCommand(
    identifier="LoaderHome",
    display_name="Home Loader",
    description="Home the loader mechanism to its reference position.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Home result",
            data_type=String
        )
    },
    function=_loader_home,
    feature=loader_feature
)


def _loader_park(metadata):
    """Park the loader mechanism."""
    try:
        result = LoaderAPI().park()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_park_command = UnobservableCommand(
    identifier="LoaderPark",
    display_name="Park Loader",
    description="Park the loader mechanism in its rest position.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Park result",
            data_type=String
        )
    },
    function=_loader_park,
    feature=loader_feature
)


def _loader_open_door(bucket_num, metadata):
    """Open the loader door to access a bucket."""
    try:
        result = LoaderAPI().open_door(int(bucket_num))
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_open_door_command = UnobservableCommand(
    identifier="LoaderOpenDoor",
    display_name="Open Loader Door",
    description="Open the loader door to access a specific bucket.",
    parameters={
        "bucket_num": Element(
            identifier="BucketNum",
            display_name="Bucket Number",
            description="Which bucket to present (1 or 2)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Open door result",
            data_type=String
        )
    },
    function=_loader_open_door,
    feature=loader_feature
)


def _loader_close_door(metadata):
    """Close the loader door."""
    try:
        result = LoaderAPI().close_door()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_close_door_command = UnobservableCommand(
    identifier="LoaderCloseDoor",
    display_name="Close Loader Door",
    description="Close the loader door.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Close door result",
            data_type=String
        )
    },
    function=_loader_close_door,
    feature=loader_feature
)


def _loader_load_plate(bucket_num, gripper_offset, plate_height,
                       speed, options, metadata):
    """Load a plate into the specified bucket."""
    try:
        result = LoaderAPI().load_plate(
            bucket_num=int(bucket_num),
            gripper_offset=float(gripper_offset),
            plate_height=float(plate_height),
            speed=int(speed),
            options=int(options)
        )
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_load_plate_command = UnobservableCommand(
    identifier="LoaderLoadPlate",
    display_name="Load Plate",
    description="Load a plate into the specified centrifuge bucket.",
    parameters={
        "bucket_num": Element(
            identifier="BucketNum",
            display_name="Bucket Number",
            description="Target bucket (1 or 2)",
            data_type=Integer
        ),
        "gripper_offset": Element(
            identifier="GripperOffset",
            display_name="Gripper Offset",
            description="Gripper offset adjustment in mm",
            data_type=Real
        ),
        "plate_height": Element(
            identifier="PlateHeight",
            display_name="Plate Height",
            description="Height of the plate in mm",
            data_type=Real
        ),
        "speed": Element(
            identifier="Speed",
            display_name="Speed",
            description="Loading speed (0=default)",
            data_type=Integer
        ),
        "options": Element(
            identifier="Options",
            display_name="Options",
            description="Loading options flags (0=default)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Load plate result",
            data_type=String
        )
    },
    function=_loader_load_plate,
    feature=loader_feature
)


def _loader_unload_plate(bucket_num, gripper_offset, plate_height,
                         speed, options, metadata):
    """Unload a plate from the specified bucket."""
    try:
        result = LoaderAPI().unload_plate(
            bucket_num=int(bucket_num),
            gripper_offset=float(gripper_offset),
            plate_height=float(plate_height),
            speed=int(speed),
            options=int(options)
        )
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_unload_plate_command = UnobservableCommand(
    identifier="LoaderUnloadPlate",
    display_name="Unload Plate",
    description="Unload a plate from the specified centrifuge bucket.",
    parameters={
        "bucket_num": Element(
            identifier="BucketNum",
            display_name="Bucket Number",
            description="Source bucket (1 or 2)",
            data_type=Integer
        ),
        "gripper_offset": Element(
            identifier="GripperOffset",
            display_name="Gripper Offset",
            description="Gripper offset adjustment in mm",
            data_type=Real
        ),
        "plate_height": Element(
            identifier="PlateHeight",
            display_name="Plate Height",
            description="Height of the plate in mm",
            data_type=Real
        ),
        "speed": Element(
            identifier="Speed",
            display_name="Speed",
            description="Unloading speed (0=default)",
            data_type=Integer
        ),
        "options": Element(
            identifier="Options",
            display_name="Options",
            description="Unloading options flags (0=default)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Unload plate result",
            data_type=String
        )
    },
    function=_loader_unload_plate,
    feature=loader_feature
)


def _loader_spin(vel_percent, accel_percent, decel_percent, timer_mode,
                 time_seconds, bucket_num_load, bucket_num_unload,
                 gripper_offset_load, gripper_offset_unload,
                 plate_height_load, plate_height_unload,
                 speed_load, speed_unload,
                 load_options, unload_options, metadata):
    """Run a loader spin cycle with load/unload parameters."""
    try:
        result = LoaderAPI().spin(
            vel_percent=float(vel_percent),
            accel_percent=float(accel_percent),
            decel_percent=float(decel_percent),
            timer_mode=int(timer_mode),
            time_seconds=int(time_seconds),
            bucket_num_load=int(bucket_num_load),
            bucket_num_unload=int(bucket_num_unload),
            gripper_offset_load=float(gripper_offset_load),
            gripper_offset_unload=float(gripper_offset_unload),
            plate_height_load=float(plate_height_load),
            plate_height_unload=float(plate_height_unload),
            speed_load=int(speed_load),
            speed_unload=int(speed_unload),
            load_options=int(load_options),
            unload_options=int(unload_options)
        )
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_spin_command = UnobservableCommand(
    identifier="LoaderSpin",
    display_name="Loader Spin",
    description="Run an extended spin cycle with automatic plate load/unload parameters.",
    parameters={
        "vel_percent": Element(
            identifier="VelocityPercent",
            display_name="Velocity %",
            description="Speed as percentage of maximum (1-100)",
            data_type=Real
        ),
        "accel_percent": Element(
            identifier="AccelerationPercent",
            display_name="Acceleration %",
            description="Acceleration as percentage of maximum (1-100)",
            data_type=Real
        ),
        "decel_percent": Element(
            identifier="DecelerationPercent",
            display_name="Deceleration %",
            description="Deceleration as percentage of maximum (1-100)",
            data_type=Real
        ),
        "timer_mode": Element(
            identifier="TimerMode",
            display_name="Timer Mode",
            description="0=total cycle time, 1=time at full speed, 2=spin continuously",
            data_type=Integer
        ),
        "time_seconds": Element(
            identifier="TimeSeconds",
            display_name="Time (seconds)",
            description="Duration in seconds (1-86400). Ignored if timer_mode=2.",
            data_type=Integer
        ),
        "bucket_num_load": Element(
            identifier="BucketNumLoad",
            display_name="Load Bucket Number",
            description="Bucket to load plate into (1 or 2)",
            data_type=Integer
        ),
        "bucket_num_unload": Element(
            identifier="BucketNumUnload",
            display_name="Unload Bucket Number",
            description="Bucket to unload plate from (1 or 2)",
            data_type=Integer
        ),
        "gripper_offset_load": Element(
            identifier="GripperOffsetLoad",
            display_name="Gripper Offset (Load)",
            description="Gripper offset for loading in mm",
            data_type=Real
        ),
        "gripper_offset_unload": Element(
            identifier="GripperOffsetUnload",
            display_name="Gripper Offset (Unload)",
            description="Gripper offset for unloading in mm",
            data_type=Real
        ),
        "plate_height_load": Element(
            identifier="PlateHeightLoad",
            display_name="Plate Height (Load)",
            description="Plate height for loading in mm",
            data_type=Real
        ),
        "plate_height_unload": Element(
            identifier="PlateHeightUnload",
            display_name="Plate Height (Unload)",
            description="Plate height for unloading in mm",
            data_type=Real
        ),
        "speed_load": Element(
            identifier="SpeedLoad",
            display_name="Speed (Load)",
            description="Loading speed (0=default)",
            data_type=Integer
        ),
        "speed_unload": Element(
            identifier="SpeedUnload",
            display_name="Speed (Unload)",
            description="Unloading speed (0=default)",
            data_type=Integer
        ),
        "load_options": Element(
            identifier="LoadOptions",
            display_name="Load Options",
            description="Loading options flags (0=default)",
            data_type=Integer
        ),
        "unload_options": Element(
            identifier="UnloadOptions",
            display_name="Unload Options",
            description="Unloading options flags (0=default)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Spin result",
            data_type=String
        )
    },
    function=_loader_spin,
    feature=loader_feature
)


def _loader_stop(bucket_num, metadata):
    """Stop the loader."""
    try:
        result = LoaderAPI().stop(int(bucket_num))
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_stop_command = UnobservableCommand(
    identifier="LoaderStop",
    display_name="Stop Loader",
    description="Stop the loader and present the specified bucket.",
    parameters={
        "bucket_num": Element(
            identifier="BucketNum",
            display_name="Bucket Number",
            description="Which bucket to present after stopping (1 or 2)",
            data_type=Integer
        )
    },
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Stop result",
            data_type=String
        )
    },
    function=_loader_stop,
    feature=loader_feature
)


def _loader_abort(metadata):
    """Abort the current loader operation."""
    try:
        result = LoaderAPI().abort()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_abort_command = UnobservableCommand(
    identifier="LoaderAbort",
    display_name="Abort Loader",
    description="Abort the current loader operation immediately.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Abort result",
            data_type=String
        )
    },
    function=_loader_abort,
    feature=loader_feature
)


def _loader_profiles(metadata):
    """List available loader profiles."""
    try:
        profiles = LoaderAPI().enumerate_profiles()
        return {"response": str(profiles)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_profiles_command = UnobservableCommand(
    identifier="LoaderProfiles",
    display_name="List Loader Profiles",
    description="Enumerate all available loader profiles.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="List of available profiles",
            data_type=String
        )
    },
    function=_loader_profiles,
    feature=loader_feature
)


def _loader_diagnostics(metadata):
    """Show loader diagnostics."""
    try:
        result = LoaderAPI().show_diagnostics()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_diagnostics_command = UnobservableCommand(
    identifier="LoaderDiagnostics",
    display_name="Loader Diagnostics",
    description="Show the loader diagnostics dialog.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Diagnostics result",
            data_type=String
        )
    },
    function=_loader_diagnostics,
    feature=loader_feature
)


def _loader_info(metadata):
    """Get loader device info."""
    try:
        result = LoaderAPI().info()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_info_command = UnobservableCommand(
    identifier="LoaderInfo",
    display_name="Loader Info",
    description="Get loader device information.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Device info",
            data_type=String
        )
    },
    function=_loader_info,
    feature=loader_feature
)


def _loader_retry(metadata):
    """Retry the last failed loader operation."""
    try:
        result = LoaderAPI().retry()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_retry_command = UnobservableCommand(
    identifier="LoaderRetry",
    display_name="Loader Retry",
    description="Retry the last failed loader operation.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Retry result",
            data_type=String
        )
    },
    function=_loader_retry,
    feature=loader_feature
)


def _loader_ignore_error(metadata):
    """Ignore the current loader error and continue."""
    try:
        result = LoaderAPI().ignore_error()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_ignore_error_command = UnobservableCommand(
    identifier="LoaderIgnoreError",
    display_name="Loader Ignore Error",
    description="Ignore the current loader error and continue.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Ignore error result",
            data_type=String
        )
    },
    function=_loader_ignore_error,
    feature=loader_feature
)


def _loader_last_error(metadata):
    """Get the last loader error."""
    try:
        result = LoaderAPI().get_last_error()
        return {"response": str(result)}
    except DeviceError as e:
        return {"response": f"error: {str(e)}"}


loader_last_error_command = UnobservableCommand(
    identifier="LoaderLastError",
    display_name="Loader Last Error",
    description="Get the last error from the loader.",
    parameters={},
    responses={
        "response": Element(
            identifier="Response",
            display_name="Response",
            description="Last error information",
            data_type=String
        )
    },
    function=_loader_last_error,
    feature=loader_feature
)

# ══════════════════════════════════════════════════════════
# Server Startup
# ══════════════════════════════════════════════════════════

async def _main():
    server = Server(
        ServerConfig(
            hostname="127.0.0.1",
            port=50052,
            name="Agilent Centrifuge SiLA Server",
            description="SiLA 2 server for Agilent Centrifuge and CentrifugeLoader control"
        )
    )

    # Register all features
    server.register_feature(system_feature)
    server.register_feature(centrifuge_feature)
    server.register_feature(loader_feature)

    await server.start()
    try:
        print("=" * 60)
        print("Agilent Centrifuge SiLA 2 Server is running.")
        print("  Host: 127.0.0.1")
        print("  Port: 50052")
        print("  Features:")
        print("    - SystemControl (ping, status)")
        print("    - CentrifugeControl (initialize, spin, open/close door, stop, ...)")
        print("    - LoaderControl (initialize, home, park, load/unload plate, spin, ...)")
        print("=" * 60)
        print("Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        await server.stop()
        print("Server stopped successfully!")


def main():
    print("Starting Agilent Centrifuge SiLA 2 Server...")
    print("NOTE: Ensure centrifuge_server.py is running on localhost:5555")
    asyncio.run(_main())


if __name__ == "__main__":
    main()