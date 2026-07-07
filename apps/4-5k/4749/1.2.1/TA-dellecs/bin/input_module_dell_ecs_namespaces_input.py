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
    pass


def collect_events(helper, ew):
    """
    Configure objects to collect_events.

    :param helper: splunk object
    :param ew: event write splunk object
    """
    dellecs_obj = DellECSCollect(helper, ew, input_type="namespace")
    helper.log_info("Start data collection for input: {}".format(
        dellecs_obj.INPUT_NAME))
    try:
        dellecs_obj.handle_endpoint_conf_api()
    except Exception as e:
        helper.log_error(str(e))
        helper.log_error("Traceback for Namespace Endpoints: {}".format(traceback.format_exc()))

    try:
        dellecs_obj.handle_dependent_endpoint_conf_api()
    except Exception as e:
        helper.log_error(str(e))
        helper.log_error("Traceback for Dependent Namespace Endpoints: {}".format(traceback.format_exc()))

    helper.log_info("Data collection is Over for input: {}".format(
        dellecs_obj.INPUT_NAME))
