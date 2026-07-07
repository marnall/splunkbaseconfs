
# encoding = utf-8

import time
import datetime
import json
from calendar import timegm

import cloudknox_consts
from log_manager import setup_logging
from cloudknox_collect import CloudKnoxCollect

_LOGGER = setup_logging("cloudknox_auditlogs_mod_input")

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
        _LOGGER.error("Audit Trail: Unexpected error while indexing data: {}".format(str(e)))


def collect_events(helper, ew):
    """Collect Cloudknox auditlog data."""
    # Initialize event counter to 0
    event_counter = 0
    # Get input name
    input_name = helper.get_input_stanza_names()
    # Get app name
    app_name = helper.get_app_name()
    # Get Splunk session key
    session_key = helper.context_meta["session_key"]
    # Initialize CloudKnoxCollect Object
    collect_obj = CloudKnoxCollect(session_key, app_name)
    # Check the configurations
    try:
        collect_obj.check_credentials()
    except Exception as e:
        _LOGGER.error(str(e))
        exit()

    _LOGGER.info("Auditlogs: Starting data collection process for {} input.".format(input_name))

    # Fetch last stored checkpoint time
    start_time = helper.get_check_point(input_name)
    # Calculate current UTC time
    current_utc_dto = datetime.datetime.utcnow()
    # Calculate current epoch seconds for end time
    end_time = int(time.time())

    # Read start time provided by user or use default value (current UTC - 24 hours)
    if not start_time:
        _LOGGER.info("Auditlogs: Start time not found in checkpoint for {} input.".format(input_name))
        start_time_str = helper.get_arg('start_datetime')

        if not start_time_str:
            _LOGGER.info(
                "Auditlogs: Start time not configured for {} input, calculating default value".format(
                    input_name))
            start_time_str = current_utc_dto - datetime.timedelta(1)
            start_time_str = datetime.datetime.strftime(start_time_str, cloudknox_consts.UTC_FORMAT)
        try:
            start_datetime_dto = datetime.datetime.strptime(start_time_str.upper(), cloudknox_consts.UTC_FORMAT)
        except Exception as e:
            _LOGGER.error("Please enter valid Start DateTime: {}".format(str(e)))
            raise ValueError(e)
        _LOGGER.info("Auditlogs: Validating start time for {} input.".format(input_name))

        # Validate start time is not more than current UTC time
        if start_datetime_dto > current_utc_dto:
            _LOGGER.error("Auditlogs: Provided start time exceeds current UTC time. Exiting data collection process")
            _LOGGER.info("Auditlogs: Data collection process is completed for {}.".format(input_name))
            exit()

        # Validate start time is not older than max backfill days allowed
        if (current_utc_dto - start_datetime_dto) > datetime.timedelta(days=cloudknox_consts.START_DATETIME_LAST_DAYS):
            _LOGGER.error(
                "Auditlogs: Provided start time is older than last {} days. Exiting data collection process".format(
                    cloudknox_consts.START_DATETIME_LAST_DAYS
                ))
            _LOGGER.info("Auditlogs: Data collection process is completed for {}.".format(input_name))
            exit()

        # Converting start time into epoch
        start_time = int(timegm(time.strptime(start_time_str, cloudknox_consts.UTC_FORMAT)))
    else:
        # Adding 1 second to timestamp stored in checkpoint to avoid duplication of event.
        # This is needed since both the parameters are inclusive
        # i.e. API provides response of events in time range:  ">=from and <=to"
        start_time = start_time + 1

    _LOGGER.info(
        "Auditlogs: Started data collection for {} input. Time Range: {} to {}.".format(
            input_name, start_time, end_time
        ))

    # Collect audit data
    data = collect_obj.cloudknox_collect_audit_trail_data(start_time, input_name, end_time)

    # Iterate over the response and index it in Splunk
    for each_data in data:

        for events in each_data:

            for each_event in events:
                timestamp = each_event['timestamp']
                date_started = each_event['dateStartedOn']
                res = each_event['resourceInfo']
                del each_event['resourceInfo'], each_event['timestamp']

                for resource_data in res:
                    each_event['resourceInfo'] = resource_data
                    each_event['eventTimestamp'] = timestamp
                    splunk_create_event(each_event, "cloudknox:audit_trail:platform", helper, ew)
                    event_counter += 1

            # Store checkpoint time
            helper.save_check_point(input_name, int(date_started / 1000))
            _LOGGER.info("Auditlogs: Checkpoint updated to {} for {} input.".format(
                int(date_started / 1000), input_name))

    _LOGGER.info("Auditlogs: Total {} events indexed for {} input.".format(event_counter, input_name))
    _LOGGER.info("Auditlogs: Data collection process is completed for {}.".format(input_name))
