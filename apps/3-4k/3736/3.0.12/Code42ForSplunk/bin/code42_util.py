import time
from distutils.util import strtobool  # pylint: disable=no-name-in-module,import-error


def parse_boolean(val, default=False):
    if val is None:
        return default
    return strtobool(str(val))


def get_current_timestamp_in_seconds():
    """Returns the number of seconds since the epoch as an int"""
    # time.time() returns a float, and on some systems, sub-second precision
    return int(time.time())
