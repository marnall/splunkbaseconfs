
# encoding = utf-8

import time
import datetime
from ta_jupiterone_log_manager import setup_logging
from ta_jupiterone_apiclient import JupiterOneAlerts


logger = setup_logging('ta_jupiterone_alerts')

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Provide the validation logic to validate the input stanza configurations."""
    pass


def validate_input_params(helper):
    """Provide the validation logic to validate the input stanza configurations."""
    input_name = helper.get_arg('name')
    try:
        interval = int(helper.get_arg('interval'))
    except ValueError:
        logger.error("JupiterOne Validation Error: Invalid Interval for input: {}.".format(input_name))
        return False
    try:
        start_datetime = helper.get_arg('start_datetime')
        if start_datetime is not None:
            input_date = datetime.datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        logger.error("JupiterOne Validation Error: Start DateTime should be "
                     "in 'YYYY-MM-DDTHH:MM:SS.SSS' (UTC) format for input: {}.".format(input_name))
        return False

    jupiterone_account = helper.get_arg('jupiterone_account')
    if not jupiterone_account:
        logger.error("JupiterOne Validation Error: Account not found "
                     "for input: {}.".format(input_name))
        return False

    if interval < 60:
        logger.error("JupiterOne Validation Error: Minimum value of interval should be 60"
                     " for input: {}.".format(input_name))
        return False

    now = datetime.datetime.utcnow()
    if start_datetime is not None and input_date > now:
        logger.error("JupiterOne Validation Error: Start DateTime should not be in future"
                     " for input: {}.".format(input_name))
        return False
    return True


def collect_events(helper, ew):
    """To collct the J1 alerts data collection logic will be start from here."""
    script_start_time = time.time()
    event_count = 0
    logger.info("JupiterOne Info: Script invoked for input : {}.".format(helper.get_arg('name')))

    # validate input params
    validate = validate_input_params(helper)
    if not validate:
        return

    # initialize the object
    jupiterone_alert_obj = JupiterOneAlerts(helper, ew)

    # check the host is available or not
    if not jupiterone_alert_obj.host:
        logger.info("JupiterOne Info: Finished the script execution due to not able to get host details.")
        return

    # get checkpoint time
    start_time, cursor = jupiterone_alert_obj.get_checkpoint_time()

    # get alert data
    response = jupiterone_alert_obj.get_alert_data(cursor)

    # if cursor exists and response will not get then collect data from last checkpoint time
    if cursor and (not response):
        logger.info("JupiterOne Info: Started data collection from previous checkpoint time.")
        cursor = None
        response = jupiterone_alert_obj.get_alert_data(cursor)

    # check the response and no. of events in response
    if response and len(response['data']['listAlertInstances']['instances']) > 0:
        logger.info("JupiterOne Info: Received the Alert data "
                    "for input: {}.".format(jupiterone_alert_obj.input_name))
        no_of_events, cursor = jupiterone_alert_obj.write_events(response, start_time)
        event_count += no_of_events

    # pagination
    while cursor:
        logger.debug("JupiterOne Debug: Started the pagination to get more alert data "
                     "for input: {}.".format(jupiterone_alert_obj.input_name))
        response = jupiterone_alert_obj.get_alert_data(cursor)
        if response and len(response['data']['listAlertInstances']['instances']) > 0:
            logger.info("JupiterOne Info: Received the Alert data while pagination "
                        "for input: {}.".format(jupiterone_alert_obj.input_name))
            no_of_events, cursor = jupiterone_alert_obj.write_events(response, start_time)
            event_count += no_of_events
        else:
            logger.debug("JupiterOne Debug: While pagination error occured in fetching alert data "
                         "for input: {}.".format(jupiterone_alert_obj.input_name))
            break

    jupiterone_alert_obj.threads.wait_completion()

    logger.info("JupiterOne Info: Total no. of collected events = {} where alerts = {} & alert related entities = {}"
                " for input: {} ".format(
                    event_count + jupiterone_alert_obj.entities_count,
                    event_count,
                    jupiterone_alert_obj.entities_count,
                    jupiterone_alert_obj.input_name))
    logger.info(
        "JupiterOne Info: Execution of the script is finished for input: {}. Time taken: {} "
        "minutes.".format(jupiterone_alert_obj.input_name, (time.time() - script_start_time) / 60))
