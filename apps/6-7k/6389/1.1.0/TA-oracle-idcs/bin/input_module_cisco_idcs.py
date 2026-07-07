# encoding = utf-8
# Developer Name: Shahrukh Salahudeen
# Developer Email: Shahrukhvp@outlook.com
# Developer LinkedIn: https://linkedin.com/IAmShahrukh


import json
import time
import csv
import os
import sys
import time
import datetime
import json
import requests
from requests.structures import CaseInsensitiveDict
from six.moves.configparser import SafeConfigParser

global environment
environment = "Splunk"
#environment = "Windows"

def printf(helper, ew, my_string):
    # To create a splunk event
    # event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)

    from datetime import datetime
    now = datetime.now()
    event = helper.new_event(data=str(my_string),
                             time=now, host=None,
                             source=helper.get_input_type(),
                             index="test",
                             sourcetype=helper.get_sourcetype(),
                             done=True, unbroken=True)
    # Save and Index:
    ew.write_event(event)


class my_values:
    def get_app_root():
        global environment
        if environment == "Splunk":
            app_root = os.path.dirname(os.path.realpath(__file__))
        elif environment == "Windows":
            app_root = r"C:\Users\ssalahudeen\Documents\Oracle_IDCS_test"
        else:
            app_root = "Error"
        return app_root

    def get_access_token_path():
        global environment
        if environment == "Splunk":
            path = '/temp/access_token.conf'
        elif environment == "Windows":
            path = r'\temp\access_token.conf.txt'
        else:
            path = "Error"
        return path

    def get_refresh_token_path():
        global environment
        if environment == "Splunk":
            path = '/temp/refresh_token.conf'
        elif environment == "Windows":
            path = r'\temp\refresh_token.conf.txt'
        else:
            path = "Error"
        return path

    def get_initial_pull_flag_path():
        global environment
        if environment == "Splunk":
            path = '/temp/initial_pull_flag.conf'
        elif environment == "Windows":
            path = r'\temp\initial_pull_flag.conf.txt'
        else:
            path = "Error"
        return path

    def get_old_access_token_path():
        global environment
        if environment == "Splunk":
            path = '/temp/old_entries/access_token'
        elif environment == "Windows":
            path = r'\temp\old_entries\access_token'
        else:
            path = "Error"
        return path

    def get_old_refresh_token_path():
        global environment
        if environment == "Splunk":
            path = '/temp/old_entries/refresh_token'
        elif environment == "Windows":
            path = r'\temp\old_entries\refresh_token'
        else:
            path = "Error"
        return path


def read_file(helper, file_path):
    try:
        f = open(file_path, "r")
        file_content_line_by_line = f.readline()
        file_content_whole = f.read()
        f.close()
        return str(file_content_line_by_line)
    except Exception as e:
        helper.log_info(str(e))
        return "Failed"


def write_file(helper, file_path, file_content):
    # WRITE MODE, NOT APPEND
    try:
        f = open(file_path, "w")
        f.write(str(file_content))
        f.close()
        return "Success"
    except Exception as e:
        helper.log_info(str(e))
        return "Failed"


def validate_input(helper, definition):
    # This example accesses the modular input variable
    # text1 = definition.parameters.get('text1', None)

    helper.log_info("Validate Input: START validate_input")
    update_existing_tokens = definition.parameters.get('update_existing_tokens', None)
    helper.log_info("update_existing_tokens: {}".format(update_existing_tokens))

    if update_existing_tokens == "NO":
        helper.log_info("Validate Input: update_existing_tokens is FALSE")

    elif update_existing_tokens == "YES":
        helper.log_info("Validate Input: update_existing_tokens is TRUE")
        # set TOKEN file paths:
        APP_ROOT = my_values.get_app_root()
        # temp_directory = APP_ROOT + '/temp'
        config_file_access_token = APP_ROOT + my_values.get_access_token_path()
        config_file_refresh_token = APP_ROOT + my_values.get_refresh_token_path()

        # Write tokens to respective files:
        oauth_2_access_token = definition.parameters.get('oauth_2_access_token', None)
        oauth_2_refresh_token = definition.parameters.get('oauth_2_refresh_token', None)
        try:
            write_file(helper, config_file_access_token, oauth_2_access_token)
            write_file(helper, config_file_refresh_token, oauth_2_refresh_token)
            helper.log_info("Validate Input: Successfully updated TOKEN VALUES ")
        except Exception as e:
            helper.log_info(str(e))
            helper.log_info("Validate Input: Failed to update TOKEN VALUES ")

    # Write INITIAL PULL FLAG to file:
    initial_pull_flag = definition.parameters.get('initial_pull_flag', None)
    helper.log_info("initial_pull_flag: {}".format(initial_pull_flag))
    helper.log_info("Validate Input: initial_pull_flag is  {}".format(initial_pull_flag))
    APP_ROOT = my_values.get_app_root()
    config_file_initial_pull_flag = APP_ROOT + my_values.get_initial_pull_flag_path()
    try:
        write_file(helper, config_file_initial_pull_flag, initial_pull_flag)
        helper.log_info("Validate Input: Successfully updated Initial Pull Flag ")
    except Exception as e:
        helper.log_info(str(e))
        helper.log_info("Validate Input: Failed to update Initial Pull Flag")
    pass


def update_initial_pull_flag(helper, my_values, value):
    APP_ROOT = my_values.get_app_root()
    config_file_initial_pull_flag = APP_ROOT + my_values.get_initial_pull_flag_path()
    try:
        write_file(helper, config_file_initial_pull_flag, value)
        helper.log_info("Validate Input: Successfully updated Initial Pull Flag to {}".format(value))
    except Exception as e:
        helper.log_info(str(e))
        helper.log_info("Validate Input: Failed to update Initial Pull Flag")


def get_utc_date_time():
    from datetime import datetime
    now = datetime.utcnow()
    current_time = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    # print("Current Time =", current_time)
    return current_time


def get_utc_date_time_x_seconds_ago(X):
    import datetime
    now = datetime.datetime.utcnow()
    x_seconds_ago = now - datetime.timedelta(seconds=X)
    time_now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    time_x_seconds_ago = x_seconds_ago.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    # print("Current UTC Time       = {}".format(time_now))
    # print("UTC Time X Seconds Ago = {}".format(time_x_seconds_ago))
    return time_x_seconds_ago, time_now


def get_utc_date_time_x_minutes_ago(X):
    import datetime
    now = datetime.datetime.utcnow()
    x_minutes_ago = now - datetime.timedelta(minutes=X)
    time_now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    time_x_minutes_ago = x_minutes_ago.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    # print("Current UTC Time       = {}".format(time_now))
    # print("UTC Time X Seconds Ago = {}".format(time_x_minutes_ago))
    return time_x_minutes_ago, time_now


def get_date_time():
    from datetime import datetime
    now = datetime.now()
    current_time = now.strftime("%c")
    # print("Current Time =", current_time)
    return current_time


def get_date_time_2():
    # 20_032022_17-51-11
    from datetime import datetime
    now = datetime.now()
    current_time = now.strftime("%d_%m%Y_%H-%M-%S")
    # print("Current Time =", current_time)
    return current_time


def write_to_splunk_index(helper, ew, data, index):
    # To create a splunk event
    # event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)

    from datetime import datetime
    now = datetime.now()

    try:
        event_timestamp = data['timestamp']
    except Exception as e:
        helper.log_info("Could Not parse timestamp value from event")
        event_timestamp = now

    event = helper.new_event(data=json.dumps(data),
                             time=event_timestamp, host=None,
                             source=helper.get_input_type(),
                             index=helper.get_output_index(),
                             sourcetype=helper.get_sourcetype(),
                             done=True, unbroken=True)

    # helper.log_info("INDEXING Data:\n{}".format(data))
    # helper.log_info("INDEXING Data now")
    # Save and Index:
    ew.write_event(event)


def convert_to_base64(message):
    import base64
    message = message
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')
    # print(base64_message)
    return base64_message


def read_input(helper):
    global environment
    # READS values from stanza and assign to DICT object

    # Misc values:
    app_name = helper.get_app_name()
    index = helper.get_output_index()
    source_type = helper.get_sourcetype()
    source = helper.get_input_type()
    source_stanza_name = helper.get_input_stanza_names()
    # loglevel = helper.get_log_level()
    proxy_settings = helper.get_proxy()
    # is_proxy_enabled = bool(proxy_settings)

    # Assign input values to DICT object:
    definition = dict()

    definition['your_cisco_idcs_url'] = helper.get_arg('your_cisco_idcs_url')
    definition['polling_interval'] = helper.get_arg('polling_interval')
    # definition['endpoint_url'] = helper.get_arg('endpoint_url')
    # definition['request_payload'] = helper.get_arg('request_payload')
    definition['oauth_2_grant_type'] = helper.get_arg('oauth_2_grant_type')
    # definition['oauth_2_access_token'] = helper.get_arg('oauth_2_access_token')
    # definition['oauth_2_expires_in'] = helper.get_arg('oauth_2_expires_in')
    # definition['oauth_2_refresh_token'] = helper.get_arg('oauth_2_refresh_token')
    definition['oauth_2_token_refresh_url'] = helper.get_arg('oauth_2_token_refresh_url')
    definition['oauth_2_client_id'] = helper.get_arg('oauth_2_client_id')
    definition['oauth_2_client_secret'] = helper.get_arg('oauth_2_client_secret')
    # definition['http_header_properties'] = helper.get_arg('http_header_properties')
    # definition['response_type'] = helper.get_arg('response_type')
    definition['update_existing_tokens'] = helper.get_arg('update_existing_tokens')
    # definition['initial_pull_flag'] = helper.get_arg('initial_pull_flag')
    definition['initial_pull_time'] = helper.get_arg('initial_pull_time')
    definition['proxyDict'] = {}

    definition['log_level'] = helper.get_log_level()
    definition['app_name'] = helper.get_app_name()
    definition['index'] = helper.get_output_index()
    definition['source_type'] = helper.get_sourcetype()
    definition['source'] = helper.get_input_type()
    definition['source_stanza_name'] = helper.get_input_stanza_names()
    # definition['loglevel'] = helper.get_log_level()
    definition['proxy_settings'] = helper.get_proxy()
    definition['is_proxy_enabled'] = bool(helper.get_proxy())

    # READ access token values from internal_files:
    APP_ROOT = my_values.get_app_root()
    '''
    if environment == "Windows":
        config_file_access_token = APP_ROOT + r'\\temp\\access_token.conf.txt'
        config_file_refresh_token = APP_ROOT + r'\\temp\\refresh_token.conf.txt'
        config_file_initial_pull = APP_ROOT + r'\\temp\\initial_pull_flag.conf.txt'
    elif environment == "Splunk":
        config_file_access_token = APP_ROOT + '/temp/access_token.conf'
        config_file_refresh_token = APP_ROOT + '/temp/refresh_token.conf'
        config_file_initial_pull = APP_ROOT + '/temp/initial_pull_flag.conf'
    '''

    config_file_access_token = APP_ROOT + my_values.get_access_token_path()
    config_file_refresh_token = APP_ROOT + my_values.get_refresh_token_path()
    config_file_initial_pull = APP_ROOT + my_values.get_initial_pull_flag_path()

    # READ from file and update DICT obj:
    definition['oauth_2_access_token'] = read_file(helper, config_file_access_token)
    definition['oauth_2_refresh_token'] = read_file(helper, config_file_refresh_token)
    definition['initial_pull_flag'] = read_file(helper, config_file_initial_pull)

    # Convert proxy value to fit with REQUESTS library:
    try:
        my_proxy = helper.get_proxy()
        definition['proxyDict'] = {my_proxy['proxy_type']: my_proxy['proxy_url'] + ":" + my_proxy['proxy_port']}
        # format: { 'https' : 'user:password@https://abcd.com:8089' }
    except Exception as e:
        helper.log_info("Exception on converting proxy value")
        pass
    # Return all values in DICT format:
    return definition


def get_report_data_success_login_get_count(helper, input_data, start_time, end_time):
    import requests
    from requests.structures import CaseInsensitiveDict

    my_idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_access_token = input_data['oauth_2_access_token']
    # polling_interval = input_data['polling_interval']
    proxyDict = input_data['proxyDict']

    # Set POST Request parameters - headers and data:
    my_headers = CaseInsensitiveDict()
    my_headers["Content-Type"] = "application/scim+json"
    my_headers["Authorization"] = "Bearer " + str(oauth_2_access_token)

    report_url = my_idcs_base_url + r"/report/v1/Reports"

    # Send HTTP POST request to get JSON data of logs:

    my_filter = "(timestamp ge \"{}\") and (timestamp lt \"{}\")".format(start_time, end_time)
    # print(my_filter)
    # "filter":  "(timestamp ge \"2022-03-15T06:14:45.191Z\") and (timestamp lt \"2022-04-03T06:14:45.191Z\")"

    # Payload for Successful login:
    my_data = {"schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:Report"],
               "outputFormat": "json",
               "reports": [{"name": "userLogin",
                            "type": "count",
                            "correlationId": "userLoginReport",
                            "filter": my_filter
                            }]}

    # Send HTTP POST request to get JSON data of logs:
    try:
        response = requests.post(report_url, headers=my_headers, data=json.dumps(my_data), proxies=proxyDict)
        # print(response.status_code)
        # print(response.text)
        # helper.log_info("SUCCESS LOGIN REPORT DATA COUNT QUERY - Response Text:\n{}".format(response.text))
        helper.log_info(
            "SUCCESS LOGIN REPORT DATA COUNT QUERY - Response Status Code: {}".format(str(response.status_code)))
    except Exception as e:
        helper.log_info("Exception occurred on making REST call - userLogin : {}".format(e))
        # helper.log_info(str(e))
        return "Failed", "SUCCESS LOGIN REPORT DATA COUNT QUERY : Message - Error occurred on API call"
    r_status_code = response.status_code
    if r_status_code == 401:
        helper.log_info("Access Token Expired")
        return "Failed", "Message - Access Token Expired"

    elif r_status_code == 201:
        helper.log_info(
            "SUCCESS LOGIN REPORT DATA COUNT QUERY - Received HTTP - 201 (Expected) status for Report-data query")
        resp_json = ""
        try:
            resp_json = response.json()
            resp_json_count = resp_json["reports"][0]['totalResults']
            # print(resp_json_count)
            helper.log_info("SUCCESS LOGIN REPORT DATA COUNT QUERY - Received {} events".format(resp_json_count))
            return "Success", resp_json_count
        except Exception as e:
            helper.log_info(
                "SUCCESS LOGIN REPORT DATA COUNT QUERY - Exception occurred on parsing received data: {}".format(e))
            return "Failed", "Exception during json parsing"

    elif r_status_code != 201 and r_status_code != 401:
        # response.raise_for_status()
        print("SUCCESS LOGIN REPORT DATA COUNT QUERY - Error On Report-data query - {}".format(r_status_code))
        print("SUCCESS LOGIN REPORT DATA COUNT QUERY - Error Text {}".format(r_status_code))
        return "Failed", "RESPONSE Error"

    else:
        return "Failed", "Unknown Error"


def get_report_data_success_login(helper, ew, input_data, my_startIndex, start_time, end_time):
    import requests
    from requests.structures import CaseInsensitiveDict
    # global oauth_2_refresh_token
    # global oauth_2_access_token
    # global expires_in

    my_idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_access_token = input_data['oauth_2_access_token']
    # polling_interval = input_data['polling_interval']
    index = input_data['index']
    proxyDict = input_data['proxyDict']

    # Set POST Request parameters - headers and data:
    my_headers = CaseInsensitiveDict()
    my_headers["Content-Type"] = "application/scim+json"
    my_headers["Authorization"] = "Bearer " + str(oauth_2_access_token)

    report_url = my_idcs_base_url + r"/report/v1/Reports"

    # Send HTTP POST request to get JSON data of logs:

    my_filter = "(timestamp ge \"{}\") and (timestamp lt \"{}\")".format(start_time, end_time)
    attributesToGet = "actorName, timestamp, ssoIdentityProvider, message"
    attributesToGet = "eventID, actorName, actorDisplayName, actorId, actorType, " \
                      "ssoSessionId, ssoIdentityProvider, ssoAuthFactor, ssoApplicationId, " \
                      "ssoApplicationType, clientIp, ssoUserAgent, ssoPlatform, " \
                      "ssoProtectedResource, ssoMatchedSignOnPolicy, Message, Timestamp"
    # helper.log_info(my_filter)

    # "filter":  "(timestamp ge \"2022-03-15T06:14:45.191Z\") and (timestamp lt \"2022-04-03T06:14:45.191Z\")"

    my_data = {"schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:Report"],
               "outputFormat": "json",
               "reports": [{
                   "name": "userLogin",
                   "type": "detail",
                   "correlationId": "userLoginReport",
                   "attributesToGet": attributesToGet,
                   "filter": my_filter,
                   "count": 50,
                   "sortBy": "timestamp",
                   "sortOrder": "ascending",
                   "startIndex": my_startIndex
               }]}

    # Send HTTP POST request to get JSON data of logs:
    try:
        response = requests.post(report_url, headers=my_headers, data=json.dumps(my_data), proxies=proxyDict)
        # helper.log_info(response.status_code)
        # helper.log_debug(response.text)
        # helper.log_info("SUCCESS LOGIN REPORT DATA QUERY - Response Text:\n{}".format(response.text))
        helper.log_info("SUCCESS LOGIN REPORT DATA QUERY - Response Status Code: {}".format(str(response.status_code)))
    except Exception as e:
        helper.log_info("SUCCESS LOGIN REPORT DATA QUERY - Exception :{}".format(e))
        return "Failed", "Message - Exception occurred on making REST call"
    r_status_code = response.status_code

    if r_status_code == 401:
        helper.log_info("SUCCESS LOGIN REPORT DATA QUERY - Access Token Expired")
        return "Failed", "Message - Access Token Expired"

    elif r_status_code == 201:
        helper.log_info("SUCCESS LOGIN REPORT DATA QUERY - Received HTTP - 201 (Expected) status for Report-data query")
        resp_json = ""
        try:
            resp_json = response.json()
            reports_data = resp_json["reports"][0]
            # print(reports_data)
            # print(resp_json["reports"][0]["name"])
            # print(resp_json["reports"][0]["startIndex"])

            reports_data2 = resp_json["reports"][0]["Resources"]
            i = 1
            for item in reports_data2:
                write_to_splunk_index(helper, ew, item, index)
                i = i + 1
            return "Success", "Indexing Success"
        except Exception as e:
            helper.log_info("SUCCESS LOGIN REPORT DATA QUERY - Exception occurred with status code 201: {}".format(e))
            return "Failed", "Exception during json parsing or indexing"

    elif r_status_code != 201 and r_status_code != 401:
        # response.raise_for_status()
        helper.log_info("SUCCESS LOGIN REPORT DATA QUERY() - - Error On Report-data query - {}".format(r_status_code))
        helper.log_info("SUCCESS LOGIN REPORT DATA QUERY() - Error Text {}".format(r_status_code))
        return "Failed", "RESPONSE Error"
    else:
        return "Failed", "Unknown Error"


def get_report_data_failed_login_get_count(helper, input_data, start_time, end_time):
    import requests
    from requests.structures import CaseInsensitiveDict

    my_idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_access_token = input_data['oauth_2_access_token']
    polling_interval = input_data['polling_interval']
    proxyDict = input_data['proxyDict']

    # Set POST Request parameters - headers and data:
    my_headers = CaseInsensitiveDict()
    my_headers["Content-Type"] = "application/scim+json"
    my_headers["Authorization"] = "Bearer " + str(oauth_2_access_token)

    report_url = my_idcs_base_url + r"/report/v1/Reports"

    # Send HTTP POST request to get JSON data of logs:

    my_filter = "(timestamp ge \"{}\") and (timestamp lt \"{}\")".format(start_time, end_time)
    # print(my_filter)
    # "filter":  "(timestamp ge \"2022-03-15T06:14:45.191Z\") and (timestamp lt \"2022-04-03T06:14:45.191Z\")"

    # Payload for Successful login:
    my_data = {"schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:Report"],
               "outputFormat": "json",
               "reports": [{"name": "suspiciousEvents",
                            "type": "count",
                            "correlationId": "suspiciousEvents",
                            "filter": my_filter
                            }]}

    # Send HTTP POST request to get JSON data of logs:
    try:
        response = requests.post(report_url, headers=my_headers, data=json.dumps(my_data),
                                 proxies=proxyDict)  # ADD PROXY
        # print(response.status_code)
        # print(response.text)
        # helper.log_info("FAILED LOGIN REPORT DATA COUNT QUERY - Response Text:\n{}".format(response.text))
        helper.log_info(
            "FAILED LOGIN REPORT DATA COUNT QUERY - Response Status Code: {}".format(str(response.status_code)))
    except Exception as e:
        helper.log_info("Exception occurred on making REST call - FAILED LOGIN COUNT : {}".format(e))
        # helper.log_info(str(e))
        return "Failed", "Message - FAILED LOGIN REPORT DATA COUNT QUERY: Error occurred on API call "
    r_status_code = response.status_code
    if r_status_code == 401:
        helper.log_info("Access Token Expired")
        return "Failed", "Message - Access Token Expired"

    elif r_status_code == 201:
        helper.log_info(
            "FAILED LOGIN REPORT DATA COUNT QUERY - Received HTTP - 201 (Expected) status for Report-data query")
        resp_json = ""
        try:
            resp_json = response.json()
            resp_json_count = resp_json["reports"][0]['totalResults']
            # print(resp_json_count)
            helper.log_info("FAILED LOGIN REPORT DATA COUNT QUERY - Received {} events".format(resp_json_count))
            return "Success", resp_json_count
        except Exception as e:
            helper.log_info(
                "FAILED LOGIN REPORT DATA COUNT QUERY - Exception occurred on parsing received data: {}".format(e))
            return "Failed", "Exception during json parsing"

    elif r_status_code != 201 and r_status_code != 401:
        # response.raise_for_status()
        print("FAILED LOGIN REPORT DATA COUNT QUERY - Error On Report-data query - {}".format(r_status_code))
        print("FAILED LOGIN REPORT DATA COUNT QUERY - Error Text {}".format(r_status_code))
        return "Failed", "RESPONSE Error"

    else:
        return "Failed", "Unknown Error"


def get_report_data_failed_login(helper, ew, input_data, my_startIndex, start_time, end_time):
    import requests
    from requests.structures import CaseInsensitiveDict
    # global oauth_2_refresh_token
    # global oauth_2_access_token
    # global expires_in

    my_idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_access_token = input_data['oauth_2_access_token']
    polling_interval = input_data['polling_interval']
    index = input_data['index']
    proxyDict = input_data['proxyDict']

    # Set POST Request parameters - headers and data:
    my_headers = CaseInsensitiveDict()
    my_headers["Content-Type"] = "application/scim+json"
    my_headers["Authorization"] = "Bearer " + str(oauth_2_access_token)

    report_url = my_idcs_base_url + r"/report/v1/Reports"

    # Send HTTP POST request to get JSON data of logs:

    my_filter = "(timestamp ge \"{}\") and (timestamp lt \"{}\")".format(start_time, end_time)
    attributesToGet = "actorName, timestamp, ssoIdentityProvider, message"
    attributesToGet = "eventID, actorName, actorDisplayName, actorId, actorType, " \
                      "ssoSessionId, ssoIdentityProvider, ssoAuthFactor, ssoApplicationId, " \
                      "ssoApplicationType, clientIp, ssoUserAgent, ssoPlatform, " \
                      "ssoProtectedResource, ssoMatchedSignOnPolicy, Message, Timestamp"
    # helper.log_info(my_filter)

    # "filter":  "(timestamp ge \"2022-03-15T06:14:45.191Z\") and (timestamp lt \"2022-04-03T06:14:45.191Z\")"

    my_data = {"schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:Report"],
               "outputFormat": "json",
               "reports": [{
                   "name": "suspiciousEvents",
                   "type": "detail",
                   "correlationId": "suspiciousEvents",
                   "attributesToGet": attributesToGet,
                   "filter": my_filter,
                   "count": 50,
                   "sortBy": "timestamp",
                   "sortOrder": "ascending",
                   "startIndex": my_startIndex
               }]}

    # Send HTTP POST request to get JSON data of logs:
    try:
        response = requests.post(report_url, headers=my_headers, data=json.dumps(my_data), proxies=proxyDict)
        # helper.log_info(response.status_code)
        # helper.log_debug(response.text)
        # helper.log_info("FAILED LOGIN REPORT DATA QUERY - Response Text:\n{}".format(response.text))
        helper.log_info("FAILED LOGIN REPORT DATA QUERY - Response Status Code: {}".format(str(response.status_code)))
    except Exception as e:
        helper.log_info("FAILED LOGIN REPORT DATA QUERY - Exception :{}".format(e))
        return "Failed", "Message - Exception occurred on making REST call"
    r_status_code = response.status_code

    if r_status_code == 401:
        helper.log_info("FAILED LOGIN REPORT DATA QUERY - Access Token Expired")
        return "Failed", "Message - Access Token Expired"

    elif r_status_code == 201:
        helper.log_info("FAILED LOGIN REPORT DATA QUERY - Received HTTP - 201 (Expected) status for Report-data query")
        resp_json = ""
        try:
            resp_json = response.json()
            reports_data = resp_json["reports"][0]

            reports_data2 = resp_json["reports"][0]["Resources"]
            i = 1
            for item in reports_data2:
                write_to_splunk_index(helper, ew, item, index)
                i = i + 1
            return "Success", "Indexing Success"
        except Exception as e:
            helper.log_info("FAILED LOGIN REPORT DATA QUERY - Exception occurred with status code 201: {}".format(e))
            return "Failed", "Exception during json parsing"

    elif r_status_code != 201 and r_status_code != 401:
        # response.raise_for_status()
        helper.log_info("FAILED LOGIN REPORT DATA QUERY() - - Error On Report-data query - {}".format(r_status_code))
        helper.log_info("FAILED LOGIN REPORT DATA QUERY() - Error Text {}".format(r_status_code))
        return "Failed", "RESPONSE Error"
    else:
        return "Failed", "Unknown Error"


def get_report_data_applicationAccess(helper, ew, input_data, my_startIndex, start_time, end_time):
    import requests
    from requests.structures import CaseInsensitiveDict
    # global oauth_2_refresh_token
    # global oauth_2_access_token
    # global expires_in

    my_idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_access_token = input_data['oauth_2_access_token']
    polling_interval = input_data['polling_interval']
    index = input_data['index']
    proxyDict = input_data['proxyDict']

    # Set POST Request parameters - headers and data:
    my_headers = CaseInsensitiveDict()
    my_headers["Content-Type"] = "application/scim+json"
    my_headers["Authorization"] = "Bearer " + str(oauth_2_access_token)

    report_url = my_idcs_base_url + r"/report/v1/Reports"

    # Send HTTP POST request to get JSON data of logs:

    my_filter = "(timestamp ge \"{}\") and (timestamp lt \"{}\")".format(start_time, end_time)
    # attributesToGet = "actorName, timestamp, ssoIdentityProvider, message"
    attributesToGet = "eventID, actorName, actorDisplayName, actorId, actorType, " \
                      "ssoSessionId, ssoIdentityProvider, ssoAuthFactor, ssoApplicationId, " \
                      "ssoApplicationType, clientIp, ssoUserAgent, ssoPlatform, " \
                      "ssoProtectedResource, ssoMatchedSignOnPolicy, Message, Timestamp"
    report_name = "applicationAccess"
    # helper.log_info(my_filter)

    # "filter":  "(timestamp ge \"2022-03-15T06:14:45.191Z\") and (timestamp lt \"2022-04-03T06:14:45.191Z\")"

    my_data = {"schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:Report"],
               "outputFormat": "json",
               "reports": [{
                   "name": report_name,
                   "type": "detail",
                   "correlationId": report_name,
                   "attributesToGet": attributesToGet,
                   "filter": my_filter,
                   "count": 50,
                   "sortBy": "timestamp",
                   "sortOrder": "ascending",
                   "startIndex": my_startIndex
               }]}

    # Send HTTP POST request to get JSON data of logs:
    try:
        response = requests.post(report_url, headers=my_headers, data=json.dumps(my_data), proxies=proxyDict)
        # helper.log_info(response.status_code)
        # helper.log_debug(response.text)
        # helper.log_info("FAILED LOGIN REPORT DATA QUERY - Response Text:\n{}".format(response.text))
        helper.log_info("{} - Response Status Code: {}".format(report_name, str(response.status_code)))
    except Exception as e:
        helper.log_info("{} - Exception :{}".format(report_name, str(e)))
        return "Failed", "Message - Exception occurred on making REST call"
    r_status_code = response.status_code

    if r_status_code == 401:
        helper.log_info("{} - Access Token Expired".format(report_name))
        return "Failed", "Message - Access Token Expired"

    elif r_status_code == 201:
        helper.log_info("{} - Received HTTP - 201 (Expected) status for Report-data query".format(report_name))
        resp_json = ""
        try:
            resp_json = response.json()
            reports_data = resp_json["reports"][0]

            reports_data2 = resp_json["reports"][0]["Resources"]
            i = 1
            for item in reports_data2:
                write_to_splunk_index(helper, ew, item, index)
                i = i + 1
            return "Success", "Indexing Success"
        except Exception as e:
            helper.log_info("{} - Exception occurred with status code 201: {}".format(report_name, str(e)))
            return "Failed", "Exception during json parsing"

    elif r_status_code != 201 and r_status_code != 401:
        # response.raise_for_status()
        helper.log_info("{} QUERY() - - Error On Report-data query - {}".format(report_name, r_status_code))
        helper.log_info("{} QUERY() - Error Text {}".format(report_name, r_status_code))
        return "Failed", "RESPONSE Error"
    else:
        return "Failed", "Unknown Error"


def get_report_data_generic_get_count(helper, input_data, start_time, end_time, report_name):
    import requests
    from requests.structures import CaseInsensitiveDict

    my_idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_access_token = input_data['oauth_2_access_token']
    proxyDict = input_data['proxyDict']

    # Set POST Request parameters - headers and data:
    my_headers = CaseInsensitiveDict()
    my_headers["Content-Type"] = "application/scim+json"
    my_headers["Authorization"] = "Bearer " + str(oauth_2_access_token)

    # REST ENDPOINT URL:
    report_url = my_idcs_base_url + r"/report/v1/Reports"

    # Send HTTP POST request to get JSON data of logs:
    # "filter":  "(timestamp ge \"2022-03-15T06:14:45.191Z\") and (timestamp lt \"2022-04-03T06:14:45.191Z\")"
    my_filter = "(timestamp ge \"{}\") and (timestamp lt \"{}\")".format(start_time, end_time)

    # Payload for POST:
    my_data = {"schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:Report"],
               "outputFormat": "json",
               "reports": [{"name": report_name,
                            "type": "count",
                            "correlationId": report_name,
                            "filter": my_filter
                            }]}

    # Send HTTP POST request to get JSON data of logs:
    try:
        response = requests.post(report_url, headers=my_headers, data=json.dumps(my_data), proxies=proxyDict)
        helper.log_info("{} REPORT DATA COUNT QUERY - Response Status Code: {}".format(report_name,
                                                                                       str(response.status_code)))
    except Exception as e:
        helper.log_info("Exception occurred on making REST call - {} : {}".format(report_name, str(e)))
        return "Failed", "Message - {} COUNT QUERY: Error occurred on API call".format(report_name)
    r_status_code = response.status_code
    if r_status_code == 401:
        helper.log_info("Access Token Expired")
        return "Failed", "Message - Access Token Expired"

    elif r_status_code == 201:
        helper.log_info(
            "{} REPORT DATA COUNT QUERY - Received HTTP - 201 (Expected) status for Report-data query".format(
                report_name))
        resp_json = ""
        try:
            resp_json = response.json()
            resp_json_count = resp_json["reports"][0]['totalResults']
            helper.log_info("{} REPORT DATA COUNT QUERY - Received {} events".format(report_name, resp_json_count))
            return "Success", resp_json_count
        except Exception as e:
            helper.log_info(
                "{} REPORT DATA COUNT QUERY - Exception occurred on parsing received data: {}".format(report_name,
                                                                                                      str(e)))
            return "Failed", "Exception during json parsing"

    elif r_status_code != 201 and r_status_code != 401:
        # response.raise_for_status()
        print("{} REPORT DATA COUNT QUERY - Error On Report-data query - {}".format(report_name, r_status_code))
        print("{} FAILED LOGIN REPORT DATA COUNT QUERY - Error Text {}".format(report_name, r_status_code))
        return "Failed", "RESPONSE Error"

    else:
        return "Failed", "Unknown Error"


def get_report_data_generic(helper, ew, input_data, my_startIndex, start_time, end_time, report_name):
    import requests
    from requests.structures import CaseInsensitiveDict

    my_idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_access_token = input_data['oauth_2_access_token']
    index = input_data['index']
    proxyDict = input_data['proxyDict']

    # Set POST Request parameters - headers and data:
    my_headers = CaseInsensitiveDict()
    my_headers["Content-Type"] = "application/scim+json"
    my_headers["Authorization"] = "Bearer " + str(oauth_2_access_token)

    # REST Endpoint:
    report_url = my_idcs_base_url + r"/report/v1/Reports"

    # Send HTTP POST request to get JSON data of logs:
    my_filter = "(timestamp ge \"{}\") and (timestamp lt \"{}\")".format(start_time, end_time)
    # "filter":  "(timestamp ge \"2022-03-15T06:14:45.191Z\") and (timestamp lt \"2022-04-03T06:14:45.191Z\")"
    attributesToGet = "eventID, actorName, actorDisplayName, actorId, actorType, " \
                      "ssoSessionId, ssoIdentityProvider, ssoAuthFactor, ssoApplicationId, " \
                      "ssoApplicationType, clientIp, ssoUserAgent, ssoPlatform, " \
                      "ssoProtectedResource, ssoMatchedSignOnPolicy, Message, Timestamp"
    report_name = report_name

    # Payload to pass with POST request:
    my_data = {"schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:Report"],
               "outputFormat": "json",
               "reports": [{
                   "name": report_name,
                   "type": "detail",
                   "correlationId": report_name,
                   "attributesToGet": attributesToGet,
                   "filter": my_filter,
                   "count": 50,
                   "sortBy": "timestamp",
                   "sortOrder": "ascending",
                   "startIndex": my_startIndex
               }]}

    # Send HTTP POST request to get JSON data of logs:
    try:
        response = requests.post(report_url, headers=my_headers, data=json.dumps(my_data), proxies=proxyDict)
        # helper.log_info(response.status_code)
        # helper.log_debug(response.text)
        # helper.log_info("FAILED LOGIN REPORT DATA QUERY - Response Text:\n{}".format(response.text))
        helper.log_info("{} - Response Status Code: {}".format(report_name, str(response.status_code)))
    except Exception as e:
        helper.log_info("{} - Exception :{}".format(report_name, str(e)))
        return "Failed", "Message - Exception occurred on making REST call"
    r_status_code = response.status_code

    if r_status_code == 401:
        helper.log_info("{} - Access Token Expired".format(report_name))
        return "Failed", "Message - Access Token Expired"

    elif r_status_code == 201:
        helper.log_info("{} - Received HTTP - 201 (Expected) status for Report-data query".format(report_name))
        resp_json = ""
        try:
            resp_json = response.json()
            reports_data = resp_json["reports"][0]
            reports_data2 = resp_json["reports"][0]["Resources"]
            i = 1
            for item in reports_data2:
                write_to_splunk_index(helper, ew, item, index)
                i = i + 1
            return "Success", "Indexing Success"
        except Exception as e:
            helper.log_info("{} - Exception occurred with status code 201: {}".format(report_name, str(e)))
            return "Failed", "Exception during json parsing"

    elif r_status_code != 201 and r_status_code != 401:
        # response.raise_for_status()
        helper.log_info("{} QUERY() - - Error On Report-data query - {}".format(report_name, r_status_code))
        helper.log_info("{} QUERY() - Error Text {}".format(report_name, r_status_code))
        return "Failed", "RESPONSE Error"
    else:
        return "Failed", "Unknown Error"


def get_new_tokens(helper, definition):
    import requests
    from requests.structures import CaseInsensitiveDict
    # Gather STANZA values:
    oauth_url = definition['oauth_2_token_refresh_url']
    oauth_2_refresh_token = definition['oauth_2_refresh_token']
    oauth_2_grant_type = definition['oauth_2_grant_type']
    oauth_2_client_id = definition['oauth_2_client_id']
    oauth_2_client_secret = definition['oauth_2_client_secret']
    proxyDict = definition['proxyDict']

    # helper.log_debug("REFRESH TOKEN QUERY - Existing Access Token    : {}".format(oauth_2_access_token))  #debug
    # helper.log_debug("REFRESH TOKEN QUERY - Existing Refresh Token   : {}".format(oauth_2_refresh_token)) #debug

    # Encode client_id and secret to base64:
    oauth_2_client_id_plus_secret = str(oauth_2_client_id) + ":" + str(oauth_2_client_secret)
    oauth_2_client_id_plus_secret_base64 = convert_to_base64(oauth_2_client_id_plus_secret)

    # Set POST Request parameters:
    my_headers = CaseInsensitiveDict()
    # my_data = CaseInsensitiveDict()
    my_data = dict()
    my_headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
    my_headers["Authorization"] = "Basic " + str(oauth_2_client_id_plus_secret_base64)
    my_data["grant_type"] = oauth_2_grant_type
    my_data["refresh_token"] = oauth_2_refresh_token

    # helper.log_info(my_headers) #Remove later
    # helper.log_info(my_data)    #Remove later

    # Send HTTP POST request to obtain new access token and oauth_2_refresh_token:
    try:
        response = requests.post(oauth_url, headers=my_headers, data=my_data, proxies=proxyDict)
        ''' REPLACED send_http_request with requests.post above
        timeout = 60
        response = helper.send_http_request(url=oauth_url, 
                                        method="POST", 
                                        parameters=my_data, 
                                        payload=None,
                                        headers=my_headers, 
                                        cookies=None, 
                                        verify=False, 
                                        cert=None,
                                        timeout=timeout, 
                                        use_proxy=True)
        '''
        # helper.log_info("REFRESH TOKEN QUERY - Response Text:\n{}".format(response.text)) #debug
        # helper.log_info("REFRESH TOKEN QUERY - Response Status Code: {}".format(str(response.status_code))) #debug

    except Exception as e:
        helper.log_info("REFRESH TOKEN QUERY  - Exception occurred on making API call - {}".format(e))
        return "Failed", "Exception occurred on making API call", "Failed", "Failed"
    r_status_code = response.status_code

    #############
    # IF Success:
    if r_status_code == 200:
        helper.log_info("REFRESH TOKEN QUERY - SUCCESS. returned 200 status")
        resp_json = ""
        try:
            resp_json = response.json()
        except Exception as e:
            helper.log_debug(str(e))
        r_access_token = resp_json["access_token"]
        r_refresh_token = resp_json["refresh_token"]
        # r_token_type = resp_json["token_type"]
        r_expires_in = resp_json["expires_in"]

        helper.log_info("REFRESH TOKEN QUERY - NEW Access Token    : {}".format(r_access_token))  # debug
        helper.log_info("REFRESH TOKEN QUERY - NEW Refresh Token   : {}".format(r_refresh_token))  # debug
        helper.log_info("REFRESH TOKEN QUERY - NEW Token Expires in: {}".format(r_expires_in))  # debug

        # printf(helper, ew, r_refresh_token) # remove later
        # printf(helper, ew, r_access_token) # remove later

        return "Success", r_access_token, r_refresh_token, r_expires_in
    else:
        # response.raise_for_status()
        helper.log_info("REFRESH TOKEN QUERY - failed. returned non-200 status")
        try:
            helper.log_info("REFRESH TOKEN QUERY - Status Code is {}".format(r_status_code))
            helper.log_info("REFRESH TOKEN QUERY - Response Text is {}".format(str(response.text)))
        except Exception as e:
            helper.log_info("REFRESH TOKEN QUERY - Exception occurred: {}".format(str(e)))
        return "Failed", "Unknown Error", "Failed", "Failed"
    # END OF get_refresh_token


def get_new_tokens_test(helper, definition):
    return "Success", "newly_obtained_access_token", "newly_obtained_refresh_token", 6000
    # return "Failed", "Unknown Error", "Failed", "Failed"


def get_new_tokens_and_update_values(helper, definition):
    # Read existing token values:
    oauth_2_access_token = definition['oauth_2_access_token']
    oauth_2_refresh_token = definition['oauth_2_refresh_token']

    helper.log_info("Current access_token is expired. Getting a new one")
    # helper.log_info("Current Access Token    : {}".format(oauth_2_access_token))
    # helper.log_info("Current Refresh Token   : {}".format(oauth_2_refresh_token))

    # helper.log_info("Refresh access_token")
    status, new_oauth_2_access_token, new_oauth_2_refresh_token, new_oauth_2_expires_in = get_new_tokens(helper,
                                                                                                         definition)
    if status == "Success":
        # UPDATE OLD VALUES to FILE with timestamp:
        old_oauth_2_access_token = definition['oauth_2_access_token']
        old_oauth_2_refresh_token = definition['oauth_2_refresh_token']
        my_time = get_date_time_2()
        APP_ROOT = my_values.get_app_root()
        config_file_access_token_backup = APP_ROOT + str(my_values.get_old_access_token_path()) + '_temp_' + str(
            my_time) + '.txt'
        config_file_refresh_token_backup = APP_ROOT + str(my_values.get_old_refresh_token_path()) + '_temp_' + str(
            my_time) + '.txt'
        # write_file(helper, config_file_access_token_backup,  old_oauth_2_access_token)
        write_file(helper, config_file_refresh_token_backup, old_oauth_2_refresh_token)

        # UPDATE NEW VALUES to DICT obj:
        definition['oauth_2_access_token'] = new_oauth_2_access_token
        definition['oauth_2_refresh_token'] = new_oauth_2_refresh_token

        # UPDATE NEW VALUES to FILE:
        APP_ROOT = my_values.get_app_root()
        config_file_access_token = APP_ROOT + str(my_values.get_access_token_path())
        config_file_refresh_token = APP_ROOT + str(my_values.get_refresh_token_path())
        write_file(helper, config_file_access_token, new_oauth_2_access_token)
        write_file(helper, config_file_refresh_token, new_oauth_2_refresh_token)

        helper.log_info("handle_failed_401_get_report_data - NEW ACCESS TOKEN Received")
        helper.log_info("handle_failed_401_get_report_data - NEW REFRESH TOKEN Received")

        return "Success", definition
    elif status == "Failed":
        helper.log_info("Refresh attempt failed - {}".format(new_oauth_2_access_token))
        return "Failed", definition  # return old values
    else:
        helper.log_info("Refresh attempt failed.")
        return "Failed", definition  # return old values


def collect_events(helper, ew):
    # Get input parameter values:
    helper.log_info("STARTING collect_events(). Collecting Input values from stanza")
    input_data = read_input(helper)

    idcs_base_url = input_data['your_cisco_idcs_url']
    oauth_2_refresh_token = input_data["oauth_2_refresh_token"]
    oauth_2_access_token = input_data["oauth_2_access_token"]
    polling_interval = int(input_data["polling_interval"])
    oauth_2_client_id = input_data["oauth_2_client_id"]
    oauth_2_client_secret = input_data["oauth_2_client_secret"]
    oauth_url = input_data["oauth_2_token_refresh_url"]
    initial_pull_flag = input_data["initial_pull_flag"]
    initial_pull_time = input_data["initial_pull_time"]

    # start_time = "2022-03-15T06:14:45.191Z"
    # end_time   = "2022-04-03T06:14:45.191Z"
    # end_time > start_time

    # Check if Access Token is Valid:
    okay_to_query = ""
    start_time, end_time = get_utc_date_time_x_minutes_ago(5)  # returns time_x_minutes_ago, time_now
    test_status, test_message = get_report_data_success_login_get_count(helper, input_data, start_time, end_time)
    if test_status == "Success":
        # SUCCESS:
        okay_to_query = True
        helper.log_info("Access Token is valid. Continue.")
    elif test_status == "Failed" and test_message == "Message - Access Token Expired":
        # FAILED. GET NEW TOKENS:
        helper.log_info("Access Token is NOT valid. Attempting to get new set of tokens.")

        '''
        # SAVE EXISTING TOKEN VALUES before the attempt to refresh:
        my_time = get_date_time_2()
        APP_ROOT = my_values.get_app_root()
        config_file_access_token_backup = APP_ROOT + str(my_values.get_access_token_path()) + '_temp_' + str(my_time) + '.txt'
        config_file_refresh_token_backup = APP_ROOT + str(my_values.get_refresh_token_path()) + '_temp_' + str(my_time) + '.txt'
        write_file(helper, config_file_access_token_backup, input_data['oauth_2_access_token'])
        write_file(helper, config_file_refresh_token_backup, input_data['oauth_2_refresh_token'])
        '''

        # REFRESH ATTEMPT:
        refresh_status, input_data = get_new_tokens_and_update_values(helper, input_data)
        helper.log_info("get_new_tokens_and_update_values - Status: {}".format(refresh_status))
        if refresh_status == "Success":
            okay_to_query = True
        else:
            okay_to_query = False
    else:
        helper.log_info("Unknown Error Occurred - Message: {}".format(test_message))
        helper.log_info("Unknown Error Occurred - Stopped collect_events()")
        okay_to_query = False
        return

    if okay_to_query == True:
        # Get time period for query:
        start_time, end_time = get_utc_date_time_x_minutes_ago(polling_interval)  # returns time_x_minutes_ago, time_now
        if initial_pull_flag == "YES":
            helper.log_info("INITIAL PULL flag is true")
            helper.log_info("INITIAL PULL time starts from :{}".format(start_time))
            start_time = initial_pull_time
        #################################################
        try:
            # Report 1: userLogin (SUCCESS Logins)
            report_name = "userLogin"
            g_status, g_log_count = get_report_data_generic_get_count(helper, input_data, start_time, end_time, report_name)
            helper.log_info("{} - Status:{} - Count:{}".format(report_name, g_status, g_log_count))
            if g_status == "Success" and g_log_count > 0:
                # GET logs:
                startIndex = 0
                while startIndex < g_log_count:
                    # helper.log_info("{} is < {}".format(startIndex, success_log_count))
                    # GET 50 records starting at startIndex
                    g2_status, message = get_report_data_generic(helper, ew, input_data, startIndex, start_time,
                                                             end_time, report_name)
                    helper.log_info("{} REPORT - {}".format(report_name, g2_status))
                    # print("My Status - {}".format(s2_status))
                    # helper.log_info("startIndex - {}".format(startIndex))
                    startIndex = startIndex + 50
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
            elif g_status == "Success" and g_log_count == 0:
                helper.log_info("{} REPORT count is zero".format(report_name))
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
            elif g_status == "Failed":
                helper.log_info("{} REPORT count FAILED".format(report_name))
            else:
                helper.log_info("{} count - Unknown ERROR".format(report_name))
        except Exception as e:
            helper.log_info("{}  - Exception occurred".format(report_name))
        # END OF userLogin
        #####################################################

        try:
            # Report 2: suspiciousEvents (Failed Logins)
            report_name = "suspiciousEvents"
            g_status, g_log_count = get_report_data_generic_get_count(helper, input_data, start_time, end_time, report_name)
            helper.log_info("{} - Status:{} - Count:{}".format(report_name, g_status, g_log_count))
            if g_status == "Success" and g_log_count > 0:
                # GET logs:
                startIndex = 0
                while startIndex < g_log_count:
                    # helper.log_info("{} is < {}".format(startIndex, success_log_count))
                    # GET 50 records starting at startIndex
                    g2_status, message = get_report_data_generic(helper, ew, input_data, startIndex, start_time,
                                                             end_time, report_name)
                    helper.log_info("{} REPORT - {}".format(report_name, g2_status))
                    # print("My Status - {}".format(s2_status))
                    # helper.log_info("startIndex - {}".format(startIndex))
                    startIndex = startIndex + 50
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
            elif g_status == "Success" and g_log_count == 0:
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
                helper.log_info("{} REPORT count is zero".format(report_name))
            elif g_status == "Failed":
                helper.log_info("{} REPORT count FAILED".format(report_name))
            else:
                helper.log_info("{} count - Unknown ERROR".format(report_name))
        except Exception as e:
            helper.log_info("{}  - Exception occurred".format(report_name))
        # END OF suspiciousEvents
        #####################################################

        try:
            # Report 3: applicationAccess (Application access)
            report_name = "applicationAccess"
            g_status, g_log_count = get_report_data_generic_get_count(helper, input_data, start_time, end_time, report_name)
            helper.log_info("{} - Status:{} - Count:{}".format(report_name, g_status, g_log_count))
            if g_status == "Success" and g_log_count > 0:
                # GET logs:
                startIndex = 0
                while startIndex < g_log_count:
                    # helper.log_info("{} is < {}".format(startIndex, success_log_count))
                    # GET 50 records starting at startIndex
                    g2_status, message = get_report_data_generic(helper, ew, input_data, startIndex, start_time,
                                                             end_time, report_name)
                    helper.log_info("{} REPORT - {}".format(report_name, g2_status))
                    # print("My Status - {}".format(s2_status))
                    # helper.log_info("startIndex - {}".format(startIndex))
                    startIndex = startIndex + 50
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
            elif g_status == "Success" and g_log_count == 0:
                helper.log_info("{} REPORT count is zero".format(report_name))
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
            elif g_status == "Failed":
                helper.log_info("{} REPORT count FAILED".format(report_name))
            else:
                helper.log_info("{} count - Unknown ERROR".format(report_name))
        except Exception as e:
            helper.log_info("{}  - Exception occurred".format(report_name))
        # END OF applicationAccess
        #####################################################

        try:
            # Report 4: appRoleAssignment
            report_name = "appRoleAssignment"
            g_status, g_log_count = get_report_data_generic_get_count(helper, input_data, start_time, end_time, report_name)
            helper.log_info("{} - Status:{} - Count:{}".format(report_name, g_status, g_log_count))
            if g_status == "Success" and g_log_count > 0:
                # GET logs:
                startIndex = 0
                while startIndex < g_log_count:
                    # helper.log_info("{} is < {}".format(startIndex, success_log_count))
                    # GET 50 records starting at startIndex
                    g2_status, message = get_report_data_generic(helper, ew, input_data, startIndex, start_time,
                                                             end_time, report_name)
                    helper.log_info("{} REPORT - {}".format(report_name, g2_status))
                    # print("My Status - {}".format(s2_status))
                    # helper.log_info("startIndex - {}".format(startIndex))
                    startIndex = startIndex + 50
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
            elif g_status == "Success" and g_log_count == 0:
                #Update initial_pull_flag to NO:
                update_initial_pull_flag(helper, my_values, "NO")
                helper.log_info("{} REPORT count is zero".format(report_name))
            elif g_status == "Failed":
                helper.log_info("{} REPORT count FAILED".format(report_name))
            else:
                helper.log_info("{} count - Unknown ERROR".format(report_name))
        except Exception as e:
            helper.log_info("{}  - Exception occurred".format(report_name))
        # END OF appRoleAssignment
        #####################################################
    else:
        helper.log_info("Error - Stopped data pull as okay_to_query was not True")
        #################################################
    # END OF collect_events()









