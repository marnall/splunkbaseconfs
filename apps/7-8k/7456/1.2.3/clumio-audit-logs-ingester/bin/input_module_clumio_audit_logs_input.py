# encoding = utf-8
"""
--READ ME--
CLUMIO Audit Trails logs retriever for Splunk. This is a technical add-on
component developed to fetch Clumio Audit logs with a frequency of 5 minutes.
For the initial release:
    -Proxy is disabled
    -Maximum fetch records per REST API call is maximum of 100.
"""

import datetime
import json
import requests

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


# Getting the Audit Trails header function-
def get_audit_trails_header(api_key):
    # Forming the Bearer token
    bearer_token = "Bearer " + api_key.strip()
    # Forming the Header for Audit Logs REST API call
    headers_clumio_audit = {
        "Accept": "application/api.clumio.*=v1&aws-connections=v0+json",
        "Content-Type": "application/json",
        "cache-control": "no-cache",
        "Authorization": bearer_token
    }
    return headers_clumio_audit


# Forming the Clumio End Point for Audit trails:
def form_clumio_end_point(api_url):
    if api_url[-1] == "/":
        clumio_end_point = api_url.strip() + "audit-trails"
    else:
        clumio_end_point = api_url.strip() + "/audit-trails"
    return clumio_end_point


# Getting the Run State Check and Forming the Filter and Parameters based on it using check pointing in Splunk
def get_run_state_check(helper, run_state_check, opt_start_days, opt_limit_records):
    if run_state_check is None:  # This is an Initial Fetch for Audit Logs
        # Going back based on the Start days value:
        go_back = 86400 * int(opt_start_days)
        helper.log_info("Initial Fetch: " + str(go_back))
        # Forming the Filter for the Initial Fetch
        filter_string = '{\"start_timestamp\":{\"$eq\":' + str(go_back) + '}}'
        helper.log_info("Initial Fetch Filter for REST API: " + filter_string)
        run_state = "INITIAL"
    else:  # This is an Delta Fetch
        helper.log_info("Delta Fetch based on interval: " + run_state_check)
        # Getting the most recent Date time for the previous fetch
        datetime_obj = datetime.datetime.strptime(run_state_check, '%Y-%m-%dT%H:%M:%SZ')
        # Going back 10 minutes and will check for duplicate records using UUIDs
        datetime_obj -= datetime.timedelta(seconds=600)
        str_time = datetime_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        # Forming the Filter for the Delta Fetches
        helper.log_info("Date time" + str(type(str_time)) + "-" + str_time)
        filter_string = '{\"start_timestamp\":{\"$gte\":\"' + str_time + '\"}}'
        run_state = "DELTA"
    return run_state, filter_string


# Perform pruning of audit logs
def prune_audit_logs(helper, final_audit_logs_response_json):
    helper.log_info("Inside pruning function....")
    final_pruned_audit_logs = []
    # Getting the current Date time
    datetime_obj = datetime.datetime.utcnow()
    # Going back 10 minutes
    datetime_obj -= datetime.timedelta(seconds=600)
    #  loop through the final_audit_logs_response_json and check if the record is less than 10 minutes old
    for audit_log in final_audit_logs_response_json["_embedded"]["items"]:
        if datetime.datetime.strptime(audit_log["timestamp"], '%Y-%m-%dT%H:%M:%SZ') < datetime_obj:
            final_pruned_audit_logs.append(audit_log)
        else:
            helper.log_info("Pruning the latest audit logs")
    return final_pruned_audit_logs


# Perform and check the response of audit logs checkpoint'ed
def perform_checkpoint(helper, final_audit_logs_response, run_state):
    # Initializing the results for the audit logs which are not checkpoint'ed
    final_unchecked_audit_logs = []
    if run_state == "INITIAL":
        # loop through the final_audit_logs_response_json and checkpoint all of them
        for audit_log in final_audit_logs_response:
            #  Saving the Audit Log UUID in the KVStore...
            helper.save_check_point(audit_log["id"], "CHECK")
            final_unchecked_audit_logs.append(audit_log)
    else:
        #  loop through the final_audit_logs_response_json and check against checkpoint
        for audit_log in final_audit_logs_response:
            audit_log_state = helper.get_check_point(audit_log["id"])
            # If not checkpoint'ed then we include in the audit log
            if not audit_log_state:
                final_unchecked_audit_logs.append(audit_log)
            else:
                helper.log_info("Already checkpointed")
            # Then checkpoint the audit log...
            helper.save_check_point(audit_log["id"], "CHECK")
    return final_unchecked_audit_logs


""" 
This function will validate the input stanza configurations
Following checks are performed:
    1. Limits the records to 100 per REST API Call
    2. Validates the API URL and API key 
    3. Limits the Interval to 300 seconds or more
"""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # Accesses to the Clumio End Point to validate the inputs
    helper.log_info("Validating the Input Stanza Configurations...")
    # Getting the input stanza configurations.
    api_key = definition.parameters.get('api_key', None)
    api_url = definition.parameters.get('clumio_api_url', None)
    limit_records = definition.parameters.get('limit_records_per_call')
    refresh_seconds = definition.parameters.get('interval')

    # Validating the API End point and API key by making a REST Call to Clumio
    helper.log_info("Validating the API End point and API key by making a REST Call to Clumio")
    parameters_audit_call = {'limit': 5, 'start': '1'}
    clumio_end_point = form_clumio_end_point(api_url)
    headers_clumio_audit = get_audit_trails_header(api_key)
    method = 'GET'
    try:
        helper.log_info("Performing a Validation REST Call to audit logs...")
        audit_log_response = helper.send_http_request(clumio_end_point, method, parameters=parameters_audit_call,
                                                      headers=headers_clumio_audit, use_proxy=False)
        # check the response status, if the status is not successful, raise requests.HTTPError
        helper.log_info("Performing a Validation REST Call to audit logs..." + str(audit_log_response))
        audit_log_response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        helper.log_error("Validation Error API URL and API Key:" + str(error))
        raise requests.exceptions.HTTPError(
            "HTTP Error occurred when trying to access Clumio Audit Logs Trails REST API:" + str(error))

    # Limit the interval to 300 seconds or more...
    try:
        helper.log_info("Limiting the Splunk call interval...")
        if int(refresh_seconds) < 300:
            raise ValueError("Audit logs fetch interval >= 300 seconds")
    except ValueError as error:
        helper.log_error("Audit logs fetch interval >= 300 seconds")
        raise ValueError("Audit logs fetch interval >= 300 seconds")

    # Limit the records for each REST CALL...
    try:
        if int(limit_records) < 0 or int(limit_records) > 100:
            raise ValueError("Limit records per call to less than equal to 100")
    except ValueError as error:
        helper.log_error("Limit records " + str(error))
        raise ValueError("Limit records per call to less than equal to 100")


def collect_events(helper, ew):
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.

    helper.log_info("Inside the Collect Events function call")
    # Getting the Data Input Parameters:
    helper.log_info("Inside the Collect Events function call")
    opt_api_key = helper.get_arg('api_key')
    opt_api_url = helper.get_arg('clumio_api_url')
    opt_start_days = helper.get_arg('audit_logs_start_days')
    opt_limit_records = helper.get_arg('limit_records_per_call')

    # Getting the data for the Audit Trails REST API call:
    method = 'GET'
    audit_pages = 1
    clumio_end_point = form_clumio_end_point(opt_api_url)
    headers_clumio_audit = get_audit_trails_header(opt_api_key)
    helper.log_info("Got the information for the Audit Trails REST API call")

    # Checking whether the call is Initial Fetch or Delta Fetches
    helper.log_info("Checking whether the call is Initial Fetch or Delta Fetches")
    run_statekey = "INITIAL_FETCH"
    run_state_check = helper.get_check_point(run_statekey)
    run_state, filter_string = get_run_state_check(helper, run_state_check, opt_start_days, opt_limit_records)
    # Building parameters based on Initial or Delta fetch for Audit logs REST API Call
    if run_state == "INITIAL":
        # Forming the Parameters for Initial REST API call
        parameters_audit_call = {'limit': int(opt_limit_records), 'start': '1', 'filter': filter_string}
        helper.log_info("Parameters for the Initial REST API call: " + str(parameters_audit_call))
    else:
        # Forming the Parameters for the Delta REST API call
        parameters_audit_call = {'limit': int(opt_limit_records), 'start': '1', 'filter': filter_string}
        helper.log_info("Parameters for Delta Fetch REST API call: " + str(parameters_audit_call))

    # Performing the Discovery call for getting the audit pages...
    discovery_response = helper.send_http_request(clumio_end_point, method, parameters=parameters_audit_call,
                                                  payload=None, headers=headers_clumio_audit, use_proxy=False)
    # Get Discovery call response status code
    discovery_status = discovery_response.status_code
    # If Discovery call response status is successful
    if discovery_status == 200:
        audit_pages = int(json.loads(discovery_response.text)["total_pages_count"])
        helper.log_info("Discovery call Audit pages: " + str(json.loads(discovery_response.text)["total_pages_count"]))
    else:
        helper.log_error("Discovery call Error Code: " + str(discovery_status))
        discovery_response.raise_for_status()

    # Making REST calls to get all the audit pages...
    checkpoint_time_0 = False
    for page in range(1, audit_pages + 1):
        # Building parameters based on Initial or Delta fetch for Audit logs REST API Call
        if run_state == "INITIAL":
            # Forming the Parameters for Initial REST API call
            parameters_audit_call = {'limit': int(opt_limit_records), 'start': str(page), 'filter': filter_string}
            helper.log_info("Parameters for the Initial REST API call: " + str(parameters_audit_call))
        else:
            # Forming the Parameters for the Delta REST API call
            parameters_audit_call = {'limit': int(opt_limit_records), 'start': str(page), 'filter': filter_string}
            helper.log_info("Parameters for Delta Fetch REST API call: " + str(parameters_audit_call))

        # Making the final REST API call for each page and to create an Splunk Event
        helper.log_info("Final REST API call for each page: " + str(page))
        final_audit_page_response = helper.send_http_request(clumio_end_point, method, parameters=parameters_audit_call,
                                                             payload=None, headers=headers_clumio_audit, use_proxy=False)

        # Perform pruning of last audit logs before creating events
        final_audit_page_response_pruned = prune_audit_logs(helper, final_audit_page_response.json())
        # Get response status code
        audit_page_status = final_audit_page_response.status_code
        if audit_page_status == 200 and len(final_audit_page_response_pruned) > 0:
            if checkpoint_time_0 is False:  # Only for page 1
                helper.log_info("FINAL CHECKPOINT CHECK " + str(len(final_audit_page_response_pruned)))
                helper.save_check_point(run_statekey,
                                        str((final_audit_page_response_pruned[0])["timestamp"]))
                checkpoint_time_0 = True
            #  Start doing the Checkpoint and filter them if the UUID is already present
            final_audit_page_response_unchecked = perform_checkpoint(helper, final_audit_page_response_pruned, run_state)

            # Creating a Splunk event
            helper.log_info("Final RESULTS..." + str(len(final_audit_page_response_unchecked)))
            event = helper.new_event(json.dumps(final_audit_page_response_unchecked), time=None,
                                     host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
            ew.write_event(event)
        else:
            helper.log_error("Call to the Audit Log Trails REST API failed with code: " + str(audit_page_status))
            final_audit_page_response.raise_for_status()


