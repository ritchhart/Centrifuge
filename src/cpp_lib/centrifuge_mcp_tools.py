# centrifuge_mcp_tools.py
"""
MCP tool definitions for Agilent Centrifuge control.
Import these into your MCP agent framework.
"""

from centrifuge_api import CentrifugeAPI

cent = CentrifugeAPI()


def centrifuge_info() -> dict:
    """Get centrifuge status, ActiveX version, and connection state."""
    return cent.info()


def centrifuge_list_profiles() -> list:
    """List available configuration profiles for the centrifuge."""
    return cent.enumerate_profiles()


def centrifuge_initialize(profile_name: str) -> dict:
    """
    Connect to the centrifuge using a named profile.
    The profile contains COM port and connection settings.
    Call centrifuge_list_profiles() first to get available names.
    """
    return cent.initialize(profile_name)


def centrifuge_open_door(bucket_num: int = 1) -> dict:
    """
    Open the centrifuge door to access a bucket.
    Args: bucket_num: 1 or 2
    """
    return cent.open_door(bucket_num)


def centrifuge_close_door() -> dict:
    """Close the centrifuge door."""
    return cent.close_door()


def centrifuge_spin(
    vel_percent: float = 50.0,
    accel_percent: float = 100.0,
    decel_percent: float = 100.0,
    timer_mode: int = 0,
    time_seconds: int = 60,
    bucket_num: int = 1
) -> dict:
    """
    Run a centrifuge spin cycle.
    Args:
        vel_percent:   Speed as % of maximum (1-100)
        accel_percent: Acceleration as % of maximum (1-100)
        decel_percent: Deceleration/braking as % of maximum (1-100)
        timer_mode:    0=total cycle time, 1=time at full speed, 2=continuous
        time_seconds:  Duration in seconds (1-86400)
        bucket_num:    Which bucket to present after spin (1 or 2)
    """
    return cent.spin(vel_percent, accel_percent, decel_percent,
                     timer_mode, time_seconds, bucket_num)


def centrifuge_stop(bucket_num: int = 1) -> dict:
    """Emergency stop the centrifuge. Opens door to specified bucket."""
    return cent.stop(bucket_num)


def centrifuge_disconnect() -> dict:
    """Disconnect from the centrifuge."""
    return cent.close()