import time
import calendar
import re

from ecs_helper import DellECSCollect
import traceback

"""
IMPORTANT
Edit only the validate_input and collect_events functions.
Do not edit any other part in this file.
This file is generated only once when creating the modular input.
"""


def validate_input(helper, definition):
    """
    Implement your own validation logic to validate the input stanza configurations.

    :param helper: splunk object
    :param definition: get parameter from UI
    """
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    start_time = definition.parameters.get('start_time', None)
    current_utc = int(time.time())
    time_pattern = "%Y-%m-%dT%H:%M"

    if start_time:
        if not re.match(
                r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])T(2[0-3]|[01][0-9]):[0-5][0-9]$", start_time):
            msg = 'Start Time should be in GMT time zone and \"%Y-%m-%dT%H:%M\" format.'
            helper.log_error("Error: {}".format(msg))
            raise Exception(msg)

        try:
            start_time = calendar.timegm(time.strptime(start_time, time_pattern))
        except Exception as e:
            helper.log_error("Error: {}".format(e))
            raise Exception(e)

        if start_time < 0:
            msg = 'Start time can not be lesser than "1970-01-01T00:00".'
            helper.log_error("Error: {}".format(msg))
            raise Exception(msg)

        if start_time > current_utc:
            msg = 'Start time can not be greater than current GMT.'
            helper.log_error("Error: {}".format(msg))
            raise Exception(msg)


def collect_events(helper, ew):
    """
    Configure objects to collect_events.

    :param helper: splunk object
    :param ew: event write splunk object
    """
    dellecs_obj = DellECSCollect(helper, ew)
    helper.log_info("Start data collection for input: {}".format(
        dellecs_obj.INPUT_NAME))
    try:
        dellecs_obj.handle_endpoint_conf_api()
    except Exception as e:
        helper.log_error(str(e))
        helper.log_error("Traceback for Endpoints: {}".format(traceback.format_exc()))

    try:
        dellecs_obj.handle_dependent_endpoint_conf_api()
    except Exception as e:
        helper.log_error(str(e))
        helper.log_error("Traceback for Dependent Endpoints: {}".format(traceback.format_exc()))

    helper.log_info("Data collection is Over for input: {}".format(
        dellecs_obj.INPUT_NAME))
