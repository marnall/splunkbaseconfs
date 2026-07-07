
"""
Generates events from the Confluence Audit Log endpoint

    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.

"""

# encoding = utf-8

import os # pylint: disable=unused-import
import sys  # pylint: disable=unused-import
import time
import datetime  # pylint: disable=unused-import

# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    """
    For advanced users, if you want to create single instance mod input,
    uncomment this method.
    """
    return True

def validate_input(helper, definition): # pylint: disable=unused-argument
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # org_id = definition.parameters.get('org_id', None)
    # api_key = definition.parameters.get('api_key', None)
    pass # pylint: disable=unnecessary-pass

def collect_events(helper, ew): # pylint: disable=unused-argument,too-many-locals,too-many-statements
    """collect_events

    Args:
        helper (class): Add-on Builder class to import helper functions
        ew (class): Add-on Builder class to write Splunk events

    Returns:
        None
    """

    import json # pylint: disable=import-outside-toplevel
    import requests # pylint: disable=import-outside-toplevel

    # get all inputs we need to run
    stanzas = helper.get_input_stanza_names()

    class RetriesExceededError(Exception):
        """Exception for too many retries"""
        pass  # pylint: disable=unnecessary-pass

    # retry requests if timeout hit
    def send_request_with_backoff(req_url, req_headers, req_params, req_timeout=60,
                                  max_retries=10):
        retry_count = 0
        wait_time = 1.0

        while retry_count < max_retries:
            response = requests.get(url=req_url, headers=req_headers,
                                    params=req_params, timeout=req_timeout)

            if response.status_code == 429:
                helper.log_info(f"Rate limit exceeded. Waiting {wait_time} seconds before retrying")
                time.sleep(wait_time)
                wait_time *= 2  # Double the wait time for the next retry
                retry_count += 1
            else:
                return response  # Return the successful response

        # If we're here, it means all retries have been exhausted
        raise RetriesExceededError(f"Failed to send request after maximum retries: {max_retries}.") # pylint: disable=broad-exception-raised

    # write events to splunk
    def write_data(events):
        for event in events:
            event = helper.new_event(source=input_type,
                                     index=helper.get_output_index(stanza_name),
                                     sourcetype=helper.get_sourcetype(stanza_name),
                                     data=json.dumps(event), time=event["attributes"]["time"])
            ew.write_event(event)
        helper.log_debug(f"All data written from {stanza_name}")

    for stanza_name in stanzas:

        # The following examples get the arguments of this input.
        # Note, for single instance mod input, args will be returned as a dict.
        # In single instance mode, to get arguments of a particular input, use
        opt_org_id = helper.get_arg('org_id', stanza_name)
        opt_api_key = helper.get_arg('api_key', stanza_name)
        opt_org_url = helper.get_arg('org_url', stanza_name)

        # get input type
        input_type = helper.get_input_type()

        # get specific input stanza with stanza name
        # stanza_details = helper.get_input_stanza(stanza_name)

        # The following examples get options from setup page configuration.
        # get the loglevel from the setup page
        loglevel = helper.get_log_level()
        # get proxy setting configuration
        # proxy_settings = helper.get_proxy()

        # set the log level for this modular input
        # (loglevel can be "debug", "info", "warning", "error" or "critical", case insensitive)
        helper.set_log_level(loglevel)

        key = str(stanza_name)

        try:
            last_run = helper.get_check_point(key)
            last_run = int(last_run)
        except Exception as e: # pylint: disable=broad-except,unused-variable
            # get events starting 1 hour ago if this is the first run
            last_run = int(time.time() - 3600) * 1000

        current_time = int(time.time()) * 1000

        headers = {'Authorization': 'Bearer ' + str(opt_api_key),
                   'Accept': 'application/json'}

        params = {"from": last_run,
                  "to": current_time}

        url = "https://" + str(opt_org_url) + "/admin/v1/orgs/" + str(opt_org_id) + "/events"

        helper.log_debug("Running first API request")

        try:
            response = requests.get(url=url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
        except requests.HTTPError as http_error:
            helper.log_error(f"Received HTTPError: {str(http_error)}")
            helper.log_error(f"Status: {response.status_code}")
            helper.log_error(f"Response text: {response.text}")
        except Exception as e: # pylint: disable=broad-except
            helper.log_error(f"Caught unhandled exception: {str(e)}")

        helper.log_debug("First API request completed successfully")

        response_json = json.loads(response.text)
        json_loop_response = response_json # set this initially so we can do loop
        return_entry = response_json["data"]
        helper.log_debug("Writing first return")
        try:
            write_data(return_entry)
        except Exception as e: # pylint: disable=broad-except
            helper.log_error(f"Encountered error while writing first set of data: {e}")
        loop_var = True
        # get the rest of the events
        while loop_var:
            if json_loop_response["meta"]["next"] is not None:
                next_params = {"cursor":json_loop_response["meta"]["next"],
                               "from": last_run,
                               "to": current_time}
                try:
                    loop_response = send_request_with_backoff(url, headers, next_params)
                except RetriesExceededError as rte:
                    loop_var = False
                    # checkpoint time, we'll retry again from this point on next script run
                    time_to_save = current_time
                    helper.save_check_point(key, time_to_save)
                    helper.log_error(f"Too many retries while paginating: {rte}")
                except Exception as e: # pylint: disable=broad-except
                    helper.log_error(f"Encountered unhandled error while paginating: {e}")
                json_loop_response = json.loads(loop_response.text)
                helper.log_debug(f"Return: {json_loop_response}")
                try:
                    write_data(json_loop_response["data"])
                except RetriesExceededError as e: # pylint: disable=broad-except
                    helper.log_error(f"Encountered error while writing looped set of data: {e}")
            else:
                helper.log_debug("All results retrieved, checkpointing...")
                loop_var = False

    # save checkpoint
    time_to_save = current_time
    helper.save_check_point(key, time_to_save)
