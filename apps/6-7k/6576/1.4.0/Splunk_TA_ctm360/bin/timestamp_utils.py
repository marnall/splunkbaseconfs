# encoding = utf-8

"""
Shared timestamp formatting utilities for CTM360 Add-on.
Used by CBS, HackerView, and ThreatCover input modules to provide
user-configurable timestamp formatting while preserving backward
compatibility with CTM360 App dashboards.
"""

from datetime import datetime, timezone


# Default timestamp format (ISO 8601)
DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def get_timestamp_format(helper):
    """
    Retrieve the user-configured timestamp format from the input stanza.
    Falls back to ISO 8601 if not set or empty.

    Args:
        helper: The Splunk modular input helper object.

    Returns:
        str: The timestamp format string, 'epoch' for epoch milliseconds, or 'mdy_12h' for M/D/YY format.
    """
    try:
        fmt = helper.get_arg("timestamp_format")
        if fmt and str(fmt).strip():
            return str(fmt).strip()
    except Exception:
        pass
    return DEFAULT_TIMESTAMP_FORMAT


def format_timestamp_ms(epoch_ms, fmt):
    """
    Format an epoch-millisecond timestamp according to the given format string.

    If fmt is 'epoch', returns the raw epoch_ms integer.
    If fmt is 'mdy_12h', returns M/D/YY HH:MM:SS.fff AM/PM format (no leading zeros).
    Otherwise, converts to a formatted datetime string in UTC using strftime.

    Args:
        epoch_ms: int or float, epoch time in milliseconds.
        fmt: str, a strftime format string, 'epoch', or 'mdy_12h'.

    Returns:
        The formatted timestamp (str or int).
    """
    if epoch_ms is None:
        return None
    if fmt == "epoch":
        return int(epoch_ms)
    try:
        dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
        
        # Special handling for M/D/YY format (no leading zeros)
        if fmt == "mdy_12h":
            # Format: M/D/YY HH:MM:SS.fff AM/PM
            month = dt.month
            day = dt.day
            year = dt.year % 100  # Last 2 digits of year
            hour = dt.hour
            minute = dt.minute
            second = dt.second
            millisecond = dt.microsecond // 1000  # Convert microseconds to milliseconds
            am_pm = "AM" if hour < 12 else "PM"
            hour_12 = hour if hour <= 12 else hour - 12
            if hour_12 == 0:
                hour_12 = 12
            return f"{month}/{day}/{year:02d} {hour_12:02d}:{minute:02d}:{second:02d}.{millisecond:03d} {am_pm}"
        
        return dt.strftime(fmt)
    except Exception:
        return int(epoch_ms)


def epoch_ms_to_seconds(epoch_ms):
    """
    Convert epoch milliseconds to epoch seconds (float) for Splunk _time.

    Args:
        epoch_ms: int or float, epoch time in milliseconds.

    Returns:
        float: epoch time in seconds with millisecond precision, or None.
    """
    if epoch_ms is None:
        return None
    return epoch_ms / 1000.0
