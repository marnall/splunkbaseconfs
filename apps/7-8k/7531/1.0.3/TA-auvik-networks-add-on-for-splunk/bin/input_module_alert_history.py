

# encoding = utf-8



import requests

import base64

import json

import time

from datetime import datetime

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

    # This example accesses the modular input variable

    # account = definition.parameters.get('account', None)

    pass



def collect_events(helper, ew):

    """Implement your data collection logic here"""

    

    global_account = helper.get_arg('account')

    opt_region = global_account['region']

    opt_username = global_account['username']

    opt_apikey = global_account['password']

    

    base_url = "https://auvikapi." + opt_region + ".my.auvik.com/v1/alert/history/info"

    text = opt_username + ":" + opt_apikey

    key = base64.b64encode(text.encode()).decode()



    headers = {'Authorization': 'Basic ' + key}

    timestamp2 = helper.get_check_point('last_alert')

    if timestamp2 is not None:

        helper.log_info(f"Using Saved Checkpoint: {timestamp2}")

        dt2 = datetime.strptime(timestamp2, "%Y-%m-%dT%H:%M:%S.%fZ")

    next_url = base_url

    checkpoint = None

    event_count = 0

    while next_url:

        try:

            response = requests.get(next_url, headers=headers, timeout=10)  # Set a timeout to avoid hanging

            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)

            r_text = response.json()  # Use .json() directly to parse JSON response

            if timestamp2 is None:

                for log in r_text.get('data', []):

                    event = helper.new_event(

                        data=json.dumps(log),

                        source=helper.get_input_type(),

                        index=helper.get_output_index(),

                        sourcetype=helper.get_sourcetype())

                    ew.write_event(event)

                    event_count = event_count + 1

            else:

                for log in r_text.get('data', []):  # Safely handle missing 'data' key

                    timestamp1 = log['attributes']['detectedOn']

                    dt1 = datetime.strptime(timestamp1, "%Y-%m-%dT%H:%M:%S.%fZ")
                    
                    if dt1 > dt2:

                        event = helper.new_event(

                            data=json.dumps(log),

                            source=helper.get_input_type(),

                            index=helper.get_output_index(),

                            sourcetype=helper.get_sourcetype())

                        ew.write_event(event)

                        event_count = event_count + 1

            

            # Safely handle the 'links' key and pagination

            next_url = r_text.get('links', {}).get('next')

            checkpoint = r_text['data'][-1]['attributes']['detectedOn']

        except requests.exceptions.Timeout:

            helper.log_warning("Request timed out. Retrying...")

            time.sleep(5)  # Wait before retrying

            continue



        except requests.exceptions.RequestException as e:

            helper.log_error(f"Request failed: {e}")

            break  # Exit the loop on request failures



        except json.JSONDecodeError:

            helper.log_error("Failed to parse JSON response.")

            break  # Exit the loop if the response is not valid JSON



        except KeyError as e:

            helper.log_error(f"Missing expected key in response: {e}")

            break  # Exit the loop if an expected key is missing



        except Exception as e:

            helper.log_error(f"An unexpected error occurred: {e}")

            break  # Exit the loop on any other unexpected errors

    
    helper.save_check_point('last_alert', checkpoint)
    
    helper.log_info(f"{event_count} Event/s Ingested")

    """

    # The following examples get the arguments of this input.

    # Note, for single instance mod input, args will be returned as a dict.

    # For multi instance mod input, args will be returned as a single value.

    opt_account = helper.get_arg('account')

    # In single instance mode, to get arguments of a particular input, use

    opt_account = helper.get_arg('account', stanza_name)



    # get input type

    helper.get_input_type()



    # The following examples get input stanzas.

    # get all detailed input stanzas

    helper.get_input_stanza()

    # get specific input stanza with stanza name

    helper.get_input_stanza(stanza_name)

    # get all stanza names

    helper.get_input_stanza_names()



    # The following examples get options from setup page configuration.

    # get the loglevel from the setup page

    loglevel = helper.get_log_level()

    # get proxy setting configuration

    proxy_settings = helper.get_proxy()

    # get account credentials as dictionary

    account = helper.get_user_credential_by_username("username")

    account = helper.get_user_credential_by_id("account id")

    # get global variable configuration

    global_region = helper.get_global_setting("region")



    # The following examples show usage of logging related helper functions.

    # write to the log for this modular input using configured global log level or INFO as default

    helper.log("log message")

    # write to the log using specified log level

    helper.log_debug("log message")

    helper.log_info("log message")

    helper.log_warning("log message")

    helper.log_error("log message")

    helper.log_critical("log message")

    # set the log level for this modular input

    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)

    helper.set_log_level(log_level)



    # The following examples send rest requests to some endpoint.

    response = helper.send_http_request(url, method, parameters=None, payload=None,

                                        headers=None, cookies=None, verify=True, cert=None,

                                        timeout=None, use_proxy=True)

    # get the response headers

    r_headers = response.headers

    # get the response body as text

    r_text = response.text

    # get response body as json. If the body text is not a json string, raise a ValueError

    r_json = response.json()

    # get response cookies

    r_cookies = response.cookies

    # get redirect history

    historical_responses = response.history

    # get response status code

    r_status = response.status_code

    # check the response status, if the status is not sucessful, raise requests.HTTPError

    response.raise_for_status()



    # The following examples show usage of check pointing related helper functions.

    # save checkpoint

    helper.save_check_point(key, state)

    # delete checkpoint

    helper.delete_check_point(key)

    # get checkpoint

    state = helper.get_check_point(key)



    # To create a splunk event

    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)

    """



    '''

    # The following example writes a random number as an event. (Multi Instance Mode)

    # Use this code template by default.

    import random

    data = str(random.randint(0,100))

    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)

    ew.write_event(event)

    '''



    '''

    # The following example writes a random number as an event for each input config. (Single Instance Mode)

    # For advanced users, if you want to create single instance mod input, please use this code template.

    # Also, you need to uncomment use_single_instance_mode() above.

    import random

    input_type = helper.get_input_type()

    for stanza_name in helper.get_input_stanza_names():

        data = str(random.randint(0,100))

        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)

        ew.write_event(event)

    '''

