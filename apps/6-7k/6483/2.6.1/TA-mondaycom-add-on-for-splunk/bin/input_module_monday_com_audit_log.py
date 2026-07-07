# encoding = utf-8

from datetime import date
import os
import sys
import time
import json
import requests
import date as date_service
from store import KVStore, AppStore
from monday_api_client import MondayApiClient
import constants

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
    """Implement your own validation logic to validate the input stanza configurations"""
    
    api_token = definition.parameters.get('api_token', None)
    
    if api_token and api_token.startswith('*'):
        try:
            from solnlib.credentials import CredentialManager 
            api_token = __import__('json').loads(CredentialManager(definition.metadata['session_key'], "TA-mondaycom-add-on-for-splunk", realm="__REST_CREDENTIAL__#TA-mondaycom-add-on-for-splunk#data/inputs/monday_com_audit_log").get_password(definition.metadata['name']))['api_token']
        except Exception as e:
            helper.log_error(f"Error accessing credentials during validation: {e}")
            helper.log_info("Skipping token validation due to credential access error")
            return
    
        MondayApiClient.check_api_token(api_token, helper)


# helper https://docs.splunk.com/Documentation/AddonBuilder/4.1.0/UserGuide/PythonHelperFunctions#:~:text=The%20Add%2Don%20Builder%20provides,input%20arguments%20using%20helper%20functions.
# ew - Event Writter
def collect_events(helper, ew):
    opt_api_token = helper.get_arg('api_token')

    state = AppStore(KVStore(helper))
    api_client = MondayApiClient(helper, opt_api_token)

    streamToSplunk({'helper': helper, 'ew': ew},
                   {'monday_api_client': api_client, 'state': state, 'page': constants.FIRST_PAGE})

    state.success()


def streamToSplunk(splunk_payload, request_data):
    helper = splunk_payload['helper']
    monday_api_client, state, page = request_data.values()

    try:
        data = monday_api_client.fetch_audit_logs(
            {'start_date': state.get_start_date(), 'end_date': state.get_end_date(), 'page': page})
        logs, next_page = data.values()

    except (json.decoder.JSONDecodeError, requests.exceptions.HTTPError) as error:
        helper.log_error(error)
        exit()

    sendEvent(splunk_payload, state, logs)

    if (next_page is not None):
        streamToSplunk(splunk_payload, {**request_data, 'page': next_page})


def sendEvent(splunk_payload, state, logs):
    helper, ew = splunk_payload.values()
    for log in logs:
        timestamp = log["timestamp"]
        # In case we failed in our last fetch, we skip the logs we already sent to Splunk
        if (timestamp >= state.get_current_position()):
            continue

        event = helper.new_event(json.dumps(
            log), index=helper.get_output_index(), source=helper.get_input_type(), sourcetype=helper.get_sourcetype())
        # Creates a new event. This function is used to index data in Splunk
        ew.write_event(event)

        state.set_current_position(timestamp)
