
# encoding = utf-8

from collections import OrderedDict
from datetime import datetime
import json
import time

from automoxapiclient.api.events_api import EventsAPI
from automoxapiclient.api.orgs_api import OrgsAPI
from automoxapiclient.api_client import ApiClient, OutcomeException

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
    connection = definition.parameters.get('connection', None)

    if connection is None:
        raise ValueError("An Automox Connection has not been properly defined and selected for the input")
    pass

def collect_events(helper, ew):
    EVENT_CHECKPOINT_KEY = "{}-last_event_time"

    helper.log_info("Fetching Automox console events")
    input_name = helper.get_input_stanza_names()

    # datetime of last event time
    state_key = EVENT_CHECKPOINT_KEY.format(input_name)
    last_event_time = helper.get_check_point(state_key)
    checkpoint_event_datetime = None
    try:
        checkpoint_event_datetime = datetime.fromisoformat(last_event_time)
    except TypeError:
        pass
    except Exception as e:
        helper.log_error(f"Failed to parse state key for {input_name}, review health of KV store if issue continues")

    helper.log_info(f"last_event_time checkpoint is {'not set' if last_event_time is None else last_event_time} for {input_name}")

    # Retrieve connection details used for communicating to Automox console
    automox_conn = helper.get_arg("connection")
    api_key = automox_conn.get("api_key")
    org_id = automox_conn.get("org_id")
    helper.log_info(f"For event import, connection found with api key {api_key} and org id {org_id}")

    # Set log level from global configuration
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)

    # Initialize client
    api_client = ApiClient(api_key, org_id, helper=helper)
    events_api = EventsAPI(api_client)
    orgs_api = OrgsAPI(api_client)

    # Collect and process events
    most_recent_event_datetime = checkpoint_event_datetime
    total_count = 0
    params = {}
    if checkpoint_event_datetime is not None:
        # Set startDate for filtering; only supports down to the day and
        # will need to filter out anything else for the day
        params = {"startDate": checkpoint_event_datetime.strftime("%Y-%m-%d")}
    else:
        # TODO Do we want all events or only a subset on initial import
        # Will do all events for intial load for now due to immediate visibility within events
        # Dashboard for end users
        pass

    start_time = time.time()

    orgs = orgs_api.get_orgs()

    try:
        for page, it in enumerate(events_api.get_events(params)):
            it_count = 0
            for e in it:
                # Add organization to event
                e['organization'] = orgs[e.get('organization_id', None)]
                
                # Check if event time is newer than state
                event_datetime = datetime.fromisoformat(e['create_time'])
                # Only process new data from previous checkpoint state
                if most_recent_event_datetime is None or checkpoint_event_datetime is None or event_datetime > checkpoint_event_datetime:
                    helper.log_debug(f"{event_datetime} larger than {most_recent_event_datetime}")

                    event_dict = OrderedDict()
                    event_dict["create_time"] = e["create_time"]
                    for field in e:
                        event_dict[field] = e[field]

                    try:
                        output = json.dumps(event_dict)
                    except TypeError as te:
                        helper.log_error(f"Unable to serialize event to send to splunk")
                        continue

                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=output)

                    ew.write_event(event)

                    # Update counters
                    it_count += 1
                    total_count += 1

                    # Update datetime storage for new checkpoint; not ideal
                    # because events are returned most recent to latest so really we only assign
                    # this on the first event of a pull
                    if most_recent_event_datetime is None or event_datetime > most_recent_event_datetime:
                        most_recent_event_datetime = event_datetime

            helper.log_info(f"Events processed for page {page}: {it_count}")

        helper.log_info(f"Total Events processed for {input_name} input: {total_count}")

        helper.log_info(f"Updating last_event_time checkpoint to {most_recent_event_datetime}")
        helper.save_check_point(state_key, most_recent_event_datetime.strftime("%Y-%m-%d %H:%M:%S.%f"))

        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        api_client.report_outcome("event_input", api_client.SUCCESSFUL_OUTCOME, elapsed_time)
    except OutcomeException as err:
        end_time = time.time()
        elapsed_time = int(end_time - start_time)

        api_client.report_outcome("event_input", api_client.FAILED_OUTCOME, elapsed_time, err.message)

