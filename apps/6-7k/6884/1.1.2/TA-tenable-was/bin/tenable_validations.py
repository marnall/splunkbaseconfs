import re
import time
import datetime
import calendar
import croniter


# common field validations for IO and SC
def get_interval(interval):
    """Converts cron schedule or string interval to integer interval.

    Args:
        interval (string): cron string or seconds

    Returns:
        int: interval between modinput invocations in seconds
    """
    try:
        return int(interval)
    except:
        now = datetime.datetime.now()
        cron = croniter.croniter(interval, now)
        first_invocation = cron.get_next(datetime.datetime)
        second_invocation = cron.get_next(datetime.datetime)
        return int((second_invocation - first_invocation).total_seconds())

def validate_start_time(helper, start_time):
    if not start_time:
        return

    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", start_time):
        helper.log_error("Validation Error: Start Time should be in YYYY-MM-DDThh:mm:ssZ format.")
        raise ValueError(
            "Start Time should be in YYYY-MM-DDThh:mm:ssZ format.")

    time_pattern = "%Y-%m-%dT%H:%M:%SZ"
    start_time = calendar.timegm(time.strptime(start_time, time_pattern))

    if start_time < 0:
        helper.log_error("Validation Error: Start Time can not be before 1970-01-01T00:00:00Z.")
        raise ValueError("Start Time can not be before 1970-01-01T00:00:00Z.")
    elif start_time >= int(time.time()):
        helper.log_error("Validation Error: Start Time can not be in the future.")
        raise ValueError("Start Time can not be in the future.")

def validate_io_interval(helper, interval):
    interval = get_interval(interval)
    if interval > 86400 or interval < 3600:
        helper.log_error('Validation Error: Interval should be between 3600 and 86400 seconds both included.')
        raise ValueError(
            'Interval should be between 3600 and 86400 seconds both included.')
