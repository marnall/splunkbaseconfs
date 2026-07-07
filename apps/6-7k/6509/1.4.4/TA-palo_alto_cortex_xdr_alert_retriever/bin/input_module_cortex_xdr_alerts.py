"""
Generates events from the Coretex XDR Get Alerts endpoint

    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.

"""


# encoding = utf-8
import datetime
import time
import json
import secrets
import string
import hashlib
import requests
from requests.adapters import HTTPAdapter, Retry

RETRY_STRATEGY = Retry(  # pylint: disable=unexpected-keyword-arg
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"])
ADAPTER = HTTPAdapter(max_retries=RETRY_STRATEGY)
HTTP = requests.Session()
HTTP.mount("https://", ADAPTER)
HTTP.mount("http://", ADAPTER)
START_TIME = time.time()

def validate_input(helper, definition):  # pylint: disable=unused-argument,unnecessary-pass
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # enable_input = definition.parameters.get('enable_input', None)
    pass  # pylint: disable=unnecessary-pass

def collect_events(helper, ew):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
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
    global_api_key_id = helper.get_global_setting("api_key_id")
    global_api_key = helper.get_global_setting("api_key")
    global_country_code = helper.get_global_setting("country_code")
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
            "Authorization": api_key_hash
        }

        return headers

    def generate_simple_auth_headers():
        headers = {
            "x-xdr-auth-id": str(global_api_key_id),
            "Authorization": global_api_key
        }
        return headers

    # Create Splunk events
    def write_events(event_json):
        for entry in event_json:
            event = helper.new_event(data=json.dumps(entry), index=helper.get_output_index(),
                                    source=helper.get_input_type(),
                                    sourcetype=helper.get_sourcetype())
            ew.write_event(event)

    # if set, use advanced auth to get all endpoints
    # if not set, use simple auth
    if global_use_advanced_authentication in ("1", 1, True, "true", "True"):
        headers = generate_advanced_auth_headers()
    else:
        headers = generate_simple_auth_headers()

    # URL listed in docs:
    # https://stoplight.io/mocks/cortex-panw/cortex-xdr/183739843/public_api/v2/alerts/get_alerts_multi_events
    url = ("https://api-" + global_fqdn +
           ".xdr." + global_country_code +
           ".paloaltonetworks.com/public_api/v2/alerts/get_alerts_multi_events")

    key = "cortex_xdr_alerts"

    try:
        last_run = helper.get_check_point(key)
        last_run = int(last_run)
    except Exception as e:  # pylint: disable=broad-except, unused-variable
        # get events starting 1 hour ago if this is the first run
        last_run = int(time.time()) - 3600

    # first run will retrieve 100 results and will tell us how many more remain
    initial_json_data = {
        "request_data": {
            "filters":[
                {"field":"server_creation_time",
                 "operator":"gte",
                 "value": last_run}
                ]
            }
        }

    helper.log_debug("Running first API request")

    try:
        initial_response = HTTP.post(url=url,
                                     headers=headers,
                                     json=initial_json_data, timeout=600)
        response_json = json.loads(initial_response.text)
        total_endpoints = response_json["reply"]["total_count"]
        result_count = response_json["reply"]["result_count"]
    except KeyError as ke:
        helper.log_error("Error in API response: " + str(ke) +
                         "\nResponse from API: " + str(initial_response.text))
    except requests.HTTPError as http_e:
        helper.log_error("Recieved HTTP Error: " + str(http_e)
                         + "\n Additional details: " + str(initial_response.text))
    except Exception as e: # pylint: disable=broad-except
        helper.log_error("Unknown exception: " + str(e))
    helper.log_debug("First API request completed successfully")
    left_to_return = total_endpoints - result_count

    # write initial events
    event_json = response_json["reply"]["alerts"]
    write_events(event_json)

    # loop until we've collected all events, extend results to event_json list
    helper.log_debug("Beginning remaining collection loop")
    while left_to_return > 0:
        helper.log_debug("Results left: %s" % str(left_to_return))  # pylint: disable=consider-using-f-string
        if left_to_return >= 1000:
            iterative_json_data = {
                "request_data":{
                    "filters":[{"field":"server_creation_time",
                                "operator":"gte",
                                "value": int(last_run)}
                              ],
                    # zero based list, so subtract 1
                    "search_from": total_endpoints - left_to_return - 1,
                    # zero based, so get next 100
                    "search_to": total_endpoints - left_to_return + 99
                }
            }
            time.sleep(10) # sleep because of hidden request limit
        if left_to_return >= 100:
            iterative_json_data = {
                "request_data":{
                    "filters":[{"field":"server_creation_time",
                                "operator":"gte",
                                "value": int(last_run)}
                              ],
                    # zero based list, so subtract 1
                    "search_from": total_endpoints - left_to_return - 1,
                    # zero based, so get next 100
                    "search_to": total_endpoints - left_to_return + 99
                }
            }
        else:
            iterative_json_data = {
                "request_data":{
                    "filters":[{"field":"server_creation_time",
                                "operator":"gte",
                                "value": int(last_run)}
                              ],
                    # zero based list, so subtract 1
                    "search_from": total_endpoints - left_to_return - 1,
                    # get up to last
                    "search_to": total_endpoints - 1
                }
            }
        helper.log_debug("Initializing loop request")
        loop_response = HTTP.post(url=url,
                                  headers=headers,
                                  json=iterative_json_data, timeout=600)
        helper.log_debug("Request completed sucessfully, logging events")

        try:
            loop_json = json.loads(loop_response.text)
            new_entries = loop_json["reply"]["alerts"]
            write_events(new_entries)
        except KeyError as ke:
            helper.log_error("Error in API response: " + str(ke) +
                             "\nResponse from API: " + str(initial_response.text))
        except requests.HTTPError as http_e:
            helper.log_error("Recieved HTTP Error: " + str(http_e) +
                             "\n Additional details: " + str(initial_response.text))
        except Exception as e: # pylint: disable=broad-except
            helper.log_error("Unknown exception: " + str(e))

        left_to_return = left_to_return - 100

    # Write checkpoint
    time_to_save = int(time.time())
    helper.save_check_point(key, time_to_save)
