import time
from datetime import datetime, timedelta
import calendar
import json
import requests
import traceback
import re
import splunk.version as ver
from api_client import APIClient

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
    # global_account = definition.parameters.get('global_account', None)
    # start_date = definition.parameters.get('start_date', None)
    pass

def collect_events(helper, ew):
    try:
        input_name = helper.get_input_stanza_names()
        dc_starting_time = time.time()
        helper.log_info(
            "Starting data collection for input {} at {}".format(
                input_name, dc_starting_time
            )
        )
        global_account = helper.get_arg("global_account")
        if not global_account:
            helper.log_error("Invalid global_account for input '{}'.".format(input_name))
            return

        username = global_account.get("username")
        password = global_account.get("password")
        api_url = global_account.get("api_url").rstrip("/")
        stanza_name = str(helper.get_input_stanza_names())

        data = {'username': username, 'password': password, 'api_url': api_url}
        splunk_version = ver.__version__
        if not splunk_version:
            helper.log_error(
                "Splunk Error: unable to fetch splunk version."
            )
            return

        # To obtain session key
        session_key = helper.context_meta['session_key']
        apiclient_object = APIClient(session_key, data)
        endpoint = api_url + "/" + "test/secure"
        sourcetype = "PreCrime"
        source = helper.get_input_type()
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        payload= json.dumps({
            "username": username,
            "password": password
        })  

        response = apiclient_object.api_call_report(api_url + "/" + "user/login", payload, headers)
        if response.status_code == 200:
            res = response.json()
            if res.get("access_token") == False:
                helper.log_error("Please verify Credentials.")
                exit(0)
            helper.log_info("Account Validation Success...")
            res = response.json()
            helper.log_info("Account Test Connection Started...")
            access_token = res.get("access_token")
            if access_token:
                headers = {
                    'accept': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                }
                endpoint = api_url + "/" + "test/secure"
                helper.log_info(endpoint)
                response = apiclient_object.request_get(endpoint, headers)
                if response.status_code == 200:
                    helper.log_info("Account Test Connection Success...")
            else:
                helper.log_error("Please verify Credentials.")
                return False
        else:
            helper.log_error("There is some issue in API call. please try again later.")
            return False
        helper.log_info("Token Generated Successfully.")
        response = response.json()

        while(True):
            config_details = helper.get_check_point(stanza_name) or dict()
            if config_details and config_details.get('last_date'):
                helper.log_info("Found an existing checkpoint for input "
                                    "{} - {}".format(stanza_name, config_details))
                date_now = config_details.get('last_date')
            else:
                try:
                    helper.log_info("checkpoint not found")
                    start_date = helper.get_arg("start_date")
                    date_now = start_date
                except Exception as e:
                    helper.log_error('Could not connect to PreCrime account. Exception '\
                                        'occured while fetching data. Error: {}'.format(str(e)))
                    helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
                    return False

            utc_time = datetime.strptime(date_now, "%Y-%m-%d")
            epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()

            # Get time after 1 Day
            new_time = epoch_time + 86400
            end_date = datetime.utcfromtimestamp(new_time).strftime("%Y-%m-%d")
            end_time = datetime.strptime(end_date, "%Y-%m-%d")
            end_time_second = (end_time - datetime(1970, 1, 1)).total_seconds()

            # Get Current time
            current_time = datetime.utcnow().strftime("%Y-%m-%d")
            current_time = datetime.strptime(current_time, "%Y-%m-%d")
            current_time_second = (current_time - datetime(1970, 1, 1)).total_seconds()

            if(current_time_second < end_time_second):
                helper.log_info("Current time is less then the End time.")
                break
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            params = {"s": date_now, "e": end_date}
            try:
                response_data = apiclient_object.request_get(api_url + "/" + "process/domains", headers, params)
            except Exception as e:
                helper.log_error('Could not connect to PreCrime account. Exception '\
                                    'occured while fetching data. Error: {}'.format(str(e)))
                helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
                return False
            for ind_record in response_data.json().get("Domains"):
                dump_data = json.dumps(ind_record, ensure_ascii=False)
                event = helper.new_event(index=helper.get_output_index(),
                                        sourcetype=sourcetype,
                                        source=source,
                                        data=dump_data)
                ew.write_event(event)
            helper.log_info('Data ingestion into splunk completed for 1 day.')
            # Saving the checkpoint
            config_details['last_date'] = end_date
            helper.save_check_point(stanza_name, config_details)
            helper.log_info(
                "Data collection process is completed for input {}".format(input_name)
            )
            helper.log_info("Total time taken in data collection for input {} "
                            "is {}".format(input_name, (time.time() - dc_starting_time)))
        return True
    except requests.exceptions.SSLError as e:
        helper.log_error("SSL certificate verification failed. Please add a valid "\
                         "SSL Certificate or Change VERIFY_SSL flag to False "\
                         "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
    except requests.exceptions.ProxyError as e:
        helper.log_error("Please verify Proxy Configurations. "\
                         "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
    except Exception as e:
        helper.log_error(
            "PreCrime Error: Terminating the data collection unsuccessfully. "\
            "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
