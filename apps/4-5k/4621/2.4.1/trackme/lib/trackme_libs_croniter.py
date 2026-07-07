#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os
import sys
from collections import OrderedDict
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlencode
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import croniter
from croniter import croniter
from datetime import datetime, timedelta

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def cron_to_seconds(cron_expression):
    now = datetime.now()
    cron_iter = croniter(cron_expression, now)

    next_execution = cron_iter.get_next(datetime)
    previous_execution = cron_iter.get_prev(datetime)

    diff = next_execution - previous_execution
    return diff.total_seconds()


def validate_cron_schedule(cron_expression):
    """
    Validate a 5-field cron expression (standard format without seconds).
    Returns True if the expression is valid, raises ValueError if invalid.
    """
    # Split the cron expression into fields
    fields = cron_expression.split()

    # Check for exactly 5 fields (standard cron format)
    if len(fields) != 5:
        raise ValueError(
            f"Invalid number of fields in cron expression: {cron_expression}. Expected exactly 5 fields, got {len(fields)}."
        )

    try:
        # Validate the cron expression by attempting to create a croniter object
        croniter(cron_expression)
        return True
    except (ValueError, KeyError) as e:
        # croniter raises ValueError for invalid cron expressions
        error_msg = f"Invalid cron expression: {cron_expression}, Error: {str(e)}"
        get_effective_logger().error(error_msg)
        raise ValueError(error_msg)


def add_minutes_to_cron(cron_expr, minutes_to_add):
    """
    Adds minutes_to_add to the minute field of a standard 5-field cron expression.
    Handles overflow to the hour field. Only supports fixed minute and hour values (not ranges, lists, or steps).
    """
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        raise ValueError("Only standard 5-field cron expressions are supported.")

    # Only support single-value minute and hour fields (not lists, ranges, or steps)
    try:
        minute = int(fields[0])
        hour = int(fields[1])
    except ValueError:
        raise ValueError("Minute and hour fields must be integers for this function.")

    minute += minutes_to_add
    if minute >= 60:
        minute -= 60
        hour += 1
        if hour >= 24:
            hour -= 24
            # If you want to handle day/month/weekday overflow, add here

    fields[0] = str(minute)
    fields[1] = str(hour)
    return " ".join(fields)
