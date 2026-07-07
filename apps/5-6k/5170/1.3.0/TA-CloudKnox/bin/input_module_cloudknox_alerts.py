
# encoding = utf-8

import json
import time
import datetime
from calendar import timegm

import cloudknox_consts
from log_manager import setup_logging
from cloudknox_collect import CloudKnoxCollect
import cloudknox_upgrade_utility as utility
from ta_cloudknox_declare import ta_name
from solnlib import conf_manager

_LOGGER = setup_logging("cloudknox_alerts_mod_input")
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
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass


def splunk_create_event(record, sourcetype, helper, ew):
    """Create a event into a splunk.

    Args:
        record (dict): data dictionary
        sourcetype (str): Sourcetype
        helper (object): helper object
        ew (object): Event writer object
    """
    try:
        event = helper.new_event(
            source=cloudknox_consts.CLOUDKNOX_SOURCE,
            index=helper.get_output_index(),
            sourcetype=sourcetype,
            data=json.dumps(record),
        )
        ew.write_event(event)
    except Exception as e:
        _LOGGER.error("Alert: Unexpected error while indexing data: {}".format(str(e)))


def collect_events(helper, ew):
    """Collect Cloudknox alerts data."""
    # Initialize event counter to 0
    event_counter = 0
    # Get input name
    input_name = helper.get_input_stanza_names()
    # Get app name
    app_name = helper.get_app_name()
    # Get Splunk session key
    session_key = helper.context_meta["session_key"]

    cfm = conf_manager.ConfManager(
        session_key, ta_name, realm='__REST_CREDENTIAL__#TA-CloudKnox#configs/conf-ta_cloudknox_settings')
    has_upgraded = utility.check_has_upgraded_value(cfm, cloudknox_consts.inputs_upgradation_stanza)
    if has_upgraded == "0":
        _LOGGER.warning("Will continue data collection after the inputs are upgraded.")
        exit()

    # Initialize CloudKnoxCollect Object
    collect_obj = CloudKnoxCollect(session_key, app_name)
    # Check the configurations

    try:
        collect_obj.check_credentials()
    except Exception as e:
        _LOGGER.error(str(e))
        exit()

    _LOGGER.info("Alerts: Starting data collection process for {} input.".format(input_name))

    # Fetch last stored checkpoint time
    start_time = helper.get_check_point(input_name)
    # Calculate current UTC time
    current_utc_dto = datetime.datetime.utcnow()
    # Calculate current epoch seconds for end time
    end_time = int(time.time())

    alert_type = helper.get_arg("alert_type")

    # Read start time provided by user or use default value (current UTC - 24 hours)
    if not start_time:
        _LOGGER.info("Alerts: Start time not found in checkpoint for {} input.".format(input_name))
        start_time_str = helper.get_arg('start_datetime')

        if not start_time_str:
            _LOGGER.info("Alerts: Start time not configured for {} input, calculating default value".format(input_name))
            start_time_str = current_utc_dto - datetime.timedelta(1)
            start_time_str = datetime.datetime.strftime(start_time_str, cloudknox_consts.UTC_FORMAT)

        try:
            start_datetime_dto = datetime.datetime.strptime(start_time_str.upper(), cloudknox_consts.UTC_FORMAT)
        except Exception as e:
            _LOGGER.error("Please enter valid Start DateTime: {}".format(str(e)))
            raise ValueError(e)
        _LOGGER.info("Alerts: Validating start time for {} input.".format(input_name))

        # Validate start time is not more than current UTC time
        if start_datetime_dto > current_utc_dto:
            _LOGGER.error("Alerts: Provided start time exceeds current UTC time. Exiting data collection process")
            _LOGGER.info("Alerts: Data collection process is completed for {}.".format(input_name))
            exit()

        # Validate start time is not older than max backfill days allowed
        if (current_utc_dto - start_datetime_dto) > datetime.timedelta(days=cloudknox_consts.START_DATETIME_LAST_DAYS):
            _LOGGER.error(
                "Alerts: Provided start time is older than last {} days. Exiting data collection process".format(
                    cloudknox_consts.START_DATETIME_LAST_DAYS
                ))
            _LOGGER.info("Alerts: Data collection process is completed for {}.".format(input_name))
            exit()

        # Converting start time into epoch
        start_time = int(timegm(time.strptime(start_time_str, cloudknox_consts.UTC_FORMAT)))
    else:
        # Adding 1 second to timestamp stored in checkpoint to avoid duplication of event.
        # This is needed since both the parameters are inclusive
        # i.e. API provides response of events in time range:  ">=from and <=to"
        start_time = start_time + 1

    _LOGGER.info(
        "Alerts: Started data collection for {} input. Time Range: {} to {}.".format(
            input_name, start_time, end_time
        ))

    # Collect alert data
    alert_res = collect_obj.cloudknox_collect_alert_data(start_time, input_name, end_time, alert_type)

    # Iterate over the response and index it in Splunk
    for each_alert in alert_res:

        for events in each_alert:

            for each_event in events:
                astype = each_event['authSysType'].lower()
                each_event['alertType'] = alert_type
                sourcetype = "cloudknox:{}:alerts".format(astype)
                splunk_create_event(each_event, sourcetype, helper, ew)
                event_counter = event_counter + 1
                timestamp = each_event['dateModifiedOn']

            # Store checkpoint time
            helper.save_check_point(input_name, int(timestamp / 1000))
            _LOGGER.info("Alerts: Checkpoint updated to {} for {} input.".format(int(timestamp / 1000), input_name))

    _LOGGER.info("Alerts: Total {} events indexed for {} input.".format(event_counter, input_name))
    _LOGGER.info("Alerts: Data collection process is completed for {}.".format(input_name))
