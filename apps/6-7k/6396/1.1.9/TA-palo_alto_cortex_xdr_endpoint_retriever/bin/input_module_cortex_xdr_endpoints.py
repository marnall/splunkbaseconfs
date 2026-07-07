"""
Generates events from the Coretex XDR Endpoint endpoint

    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.

"""


# encoding = utf-8
import datetime
import json
import secrets
import string
import hashlib
import time
import requests

def validate_input(helper, definition):  # pylint: disable=unused-argument,unnecessary-pass
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # enable_input = definition.parameters.get('enable_input', None)
    pass  # pylint: disable=unnecessary-pass

def collect_events(helper, ew):  # pylint: disable=too-many-locals,too-many-statements
    """collect_events

    Args:
        helper (class): Add-on Builder class to import helper functions
        ew (class): Add-on Builder class to write Splunk events

    Returns:
        None
    """

    # The following get the arguments of this input.
    # Unused
    # opt_enable_input = helper.get_arg('enable_input')

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page and set loglevel
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    # get global variable configuration
    global_fqdn = helper.get_global_setting("fqdn")
    global_org_region = helper.get_global_setting("org_region")
    global_api_key_id = helper.get_global_setting("api_key_id")
    global_api_key = helper.get_global_setting("api_key")
    global_use_advanced_authentication = helper.get_global_setting("use_advanced_authentication")

    def generate_advanced_auth_headers():
        # Generate a 64 bytes random string
        nonce = "".join([secrets.choice(string.ascii_letters + string.digits) for _ in range(64)])
        # Get the current timestamp as milliseconds.
        timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) * 1000
        # Generate the auth key:
        auth_key = "%s%s%s" % (global_api_key, nonce, timestamp)  # pylint: disable=consider-using-f-string
        # Convert to bytes object
        auth_key = auth_key.encode("utf-8")
        # Calculate sha256:
        api_key_hash = hashlib.sha256(auth_key).hexdigest()
        # Generate HTTP call headers
        headers = {
            "x-xdr-timestamp": str(timestamp),
            "x-xdr-nonce": nonce,
            "x-xdr-auth-id": str(global_api_key_id),
            "Authorization": api_key_hash,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        return headers

    def generate_simple_auth_headers():
        headers = {
            "x-xdr-auth-id": str(global_api_key_id),
            "Authorization": global_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        return headers

    def write_endpoints_to_splunk(endpoints_list):
        """Write a batch of endpoints to Splunk"""
        for entry in endpoints_list:
            event = helper.new_event(data=json.dumps(entry),
                                     time=int(time.time()),
                                     index=helper.get_output_index(),
                                     source=helper.get_input_type(),
                                     sourcetype=helper.get_sourcetype())
            ew.write_event(event)
        helper.log_debug(f"Wrote {len(endpoints_list)} endpoints to Splunk")

    url = ("https://api-" + global_fqdn +
           ".xdr." + global_org_region + 
           ".paloaltonetworks.com/public_api/v1/endpoints/get_endpoint")
    # first run will retrieve 100 results and will tell us how many more remain
    initial_json_data = {
        "request_data": {}
        }

    helper.log_debug("Running first API request")

    try:
        if global_use_advanced_authentication in ("1", 1, True, "true", "True"):
            headers = generate_advanced_auth_headers()
        else:
            headers = generate_simple_auth_headers()
        initial_response = requests.post(url=url,
                                         headers=headers,
                                         json=initial_json_data,
                                         timeout=30)
        initial_response.raise_for_status()
    except Exception as e:  # pylint: disable=broad-exception-caught
        helper.log_debug(f"Encountered error: {e}")
        helper.log_debug("API Response:" + str(initial_response))
        helper.log_debug("API Reponse Text:" + str(initial_response.text))
    helper.log_debug("First API request completed successfully")

    try:
        response_json = json.loads(initial_response.text)
    except Exception as e:  # pylint: disable=broad-exception-caught
        helper.log_debug(f"Encountered error: {e}")
        helper.log_debug(f"API Response Text: {initial_response.text}")
    total_endpoints = response_json["reply"]["total_count"]
    result_count = response_json["reply"]["result_count"]
    left_to_return = total_endpoints - result_count

    # WRITE INITIAL BATCH TO SPLUNK IMMEDIATELY
    initial_endpoints = response_json["reply"]["endpoints"]
    write_endpoints_to_splunk(initial_endpoints)

    # loop until we've collected all events, extend results to event_json list
    helper.log_debug("Beginning remaining collection loop after 1 sec sleep")
    time.sleep(0.11)
    while left_to_return > 0:
        helper.log_debug("Results left: %s" % str(left_to_return))  # pylint: disable=consider-using-f-string

        if global_use_advanced_authentication in ("1", 1, True, "true", "True"):
            headers = generate_advanced_auth_headers()
        else:
            headers = generate_simple_auth_headers()

        if left_to_return >= 100:
            iterative_json_data = {
                "request_data":{
                    # zero based list, so subtract 1
                    "search_from": total_endpoints - left_to_return - 1,
                    # zero based, so get next 100
                    "search_to": total_endpoints - left_to_return + 99
                }
            }
        else:
            iterative_json_data = {
                "request_data":{
                    # zero based list, so subtract 1
                    "search_from": total_endpoints - left_to_return - 1,
                    # get up to last
                    "search_to": total_endpoints - 1
                }
            }
        helper.log_debug("Initializing loop request")
        try:
            loop_response = requests.post(url=url,
                                          headers=headers,
                                          json=iterative_json_data,
                                          timeout=30)
            loop_response.raise_for_status()
        except Exception as e:  # pylint: disable=broad-exception-caught
            helper.log_debug(f"Encountered error: {e}")
            helper.log_debug("API Response:" + str(loop_response))
            helper.log_debug("API Reponse Text:" + str(loop_response.text))
        helper.log_debug("Request completed sucessfully, continuing after .11 sec sleep")
        try:
            loop_json = json.loads(loop_response.text)
        except Exception as e:  # pylint: disable=broad-exception-caught
            helper.log_debug(f"Encountered error: {e}")
            helper.log_debug(f"API Response Text: {loop_response.text}")
        # WRITE THIS BATCH TO SPLUNK IMMEDIATELY
        batch_endpoints = loop_json["reply"]["endpoints"]
        write_endpoints_to_splunk(batch_endpoints)

        left_to_return = left_to_return - 100
        time.sleep(0.11)

    helper.log_debug("Endpoint collection and ingestion completed")
