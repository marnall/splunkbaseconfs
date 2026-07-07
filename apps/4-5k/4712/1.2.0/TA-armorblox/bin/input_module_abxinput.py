# encoding = utf-8
import os
import sys
import time
import requests
import json
from armorblox import client
from datetime import datetime, timedelta

ARMORBLOX_INCIDENT_API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ARMORBLOX_INCIDENT_API_PAGE_SIZE = 100
# The first run
ARMORBLOX_INCIDENT_API_TIME_DELTA_IN_DAYS = 1


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""

    # This example accesses the modular input variable
    # tenant_name = definition.parameters.get('tenant_name', None)
    # key = definition.parameters.get('key', None)
    # incidentid = definition.parameters.get('incidentid', None)
    pass


def collect_events(helper, ew):
    # Get the arguments of this input.
    ARMORBLOX_INSTANCE_NAME = helper.get_arg('tenantname')
    ARMORBLOX_API_TOKEN = helper.get_arg('key')

    final_result = []
    incidents_list = []

    # Create an API client for your tenant
    c = client.Client(api_key=ARMORBLOX_API_TOKEN, instance_name=ARMORBLOX_INSTANCE_NAME)
    current_time = datetime.utcnow().replace(second=0)
    last_fetch_time = helper.get_check_point("last_fetch_time")

    if last_fetch_time == None:
        last_fetch_time = (current_time - timedelta(days=ARMORBLOX_INCIDENT_API_TIME_DELTA_IN_DAYS)).strftime(
            ARMORBLOX_INCIDENT_API_TIME_FORMAT)

    current_time = current_time.strftime(ARMORBLOX_INCIDENT_API_TIME_FORMAT)

    params = {
        'from_date': last_fetch_time,
        'to_date': current_time,
        'pageSize': ARMORBLOX_INCIDENT_API_PAGE_SIZE,
        'orderBy': 'ASC'}

    next_page_token = None

    while True:
        response_json, next_page_token, total_count = c.incidents.list(page_token= next_page_token, params=params)
        incidents_list.extend(response_json)
        if not next_page_token:
            break

    # For each incident, get the details and extract the message_id
    for result in incidents_list:
        result['message_ids'] = []

        detail_response = c.incidents.get(result["id"])

        # Loop through all the events of this incident
        if 'events' in detail_response.keys():
            for event in detail_response['events']:
                result["message_ids"].append(event['message_id'])

        if 'abuse_events' in detail_response.keys():
            for event in detail_response['abuse_events']:
                result["message_ids"].append(event['message_id'])

        final_result.append(result)

    # Save the last time point
    helper.save_check_point("last_fetch_time", current_time)

    # Create a splunk event and index to splunk
    event = helper.new_event(json.dumps(final_result), time=None, host=None, index=None, source=None,
                             sourcetype=None,done=True, unbroken=True)
    ew.write_event(event)
