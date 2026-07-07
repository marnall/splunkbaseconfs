
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import math
import splunk.rest as rest

from datetime import timedelta
from config_reader import ConfigReader

MAX_NUMBER_OF_ITERATIONS = 10000
app_name = __file__.split(os.sep)[-3]

'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    '''
    Validate input values entered by user.
    :param helper: object of BaseModInput class
    :param definition: object containing input parameters
    '''
    interval = definition.parameters.get('interval')
    endgame_api = definition.parameters.get('endgame_api')

    if not (int(interval) > 0):
        helper.log_error(
            "Endgame Error: Interval must be positive integer.")
        raise Exception(
            "Interval must be positive integer.")

    if endgame_api and not endgame_api.startswith('https://'):
        helper.log_error(
            "Endgame Error: Only secure URLs are supported. Use https scheme while configuring the input.")
        raise Exception(
            "Only secure URLs are supported. Use https scheme while configuring the input.")


def check_kvstore_status(session_key):
    '''
    Checks status of kvstore
    :param session_key: session key of current session
    '''
    _, content = rest.simpleRequest("/services/kvstore/status", sessionKey=session_key,
                                    method="GET", getargs={"output_mode": "json"}, raiseAllErrors=True)
    data = json.loads(content)['entry']
    if data[0]["content"]["current"].get("disabled"):
        raise Exception("Please enable it to start the data collection.")


def getToken(helper):
    helper.log_info("Calling getToken method...........")
    token = None
    response = None
    base_url = helper.get_arg('endgame_api')
    opt_username = helper.get_arg('username')
    opt_password = helper.get_arg('password')

    endgame_account = helper.get_arg('endgame_account')
    if endgame_account:
        base_url = endgame_account.get('endgame_api')
        opt_username = endgame_account.get('username')
        opt_password = endgame_account.get('password')
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    url = base_url + '/api/auth/login'

    headers = {'content-type': 'application/json'}
    payload = {"username": opt_username, "password": opt_password}
    verify_ssl = helper.get_arg('verify_ssl')
    if verify_ssl.lower() in ["yes", "true", "1"]:
        verify_ssl = True
    else:
        verify_ssl = False
    try:
        response = requests.post(url, headers=headers,
                                 data=json.dumps(payload), verify=verify_ssl)
        json_response = json.dumps(response.content)
        req_val = json.loads(json_response)
        helper.log_info(
            'Token -> HTTP Status code: {0}'.format(str(response.status_code)))
        token = json.loads(req_val.encode('utf-8'))['metadata']['token']
    except Exception as error:
        if url is None or url.strip() == '':
            helper.log_info("Error while invoking URL")
        else:
            helper.log_info("Error while invoking URL: "+str(url))

        if opt_username is None or opt_username.strip() == '':
            helper.log_info("User name is not given")
        if opt_password is None or opt_password.strip() == '':
            helper.log_info("Password is not given")
        helper.log_info('Error while getting tokens:'+(str(error)))
        sys.exit()

    if token is not None:
        helper.log_info("Got Token ...........")
    return token


def get_last_alert_timestamp():

    configreader = ConfigReader()
    lastalerttime = configreader.readConfFile('alert.conf', 'alert_data')

    return lastalerttime


def add_timedelta(timestampstr):
    try:
        datetime_object = datetime.datetime.strptime(
            timestampstr, '%Y-%m-%dT%H:%M:%S.%fZ')
        datetime_object = datetime_object + timedelta(milliseconds=1)

    # Handling upgrade scenario when created_at was used as checkpoint
    except Exception:
        datetime_object = datetime.datetime.strptime(timestampstr, '%Y-%m-%dT%H:%M:%SZ')
        datetime_object = datetime_object + timedelta(seconds=1)

    _timestampstr = datetime_object.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    return _timestampstr


def convert_to_epoch_timestamp(timestampstr):
    utc_time = datetime.datetime.strptime(timestampstr, "%Y-%m-%dT%H:%M:%S.%fZ")
    epoch_time = (utc_time - datetime.datetime(1970, 1, 1)).total_seconds()
    return epoch_time


def collect_events(helper, ew):

    session_key = helper.context_meta['session_key']
    try:
        check_kvstore_status(session_key)
    except Exception as e:
        err_msg = " Error: KV Store is disabled. " + str(e)
        helper.log_error(err_msg)
        # Display notification in Splunk messages
        postargs = {
            'severity': 'error',
            'name': app_name,
            'value': app_name + err_msg
        }
        try:
            rest.simpleRequest('/services/messages',
                               session_key, postargs=postargs)
        except:
            helper.log_error("Error: Failed to give notification message")
        exit(1)

    start_time = time.time()
    token = getToken(helper)
    input_name = str(helper.get_input_stanza_names())
    _source = helper.get_input_type()
    _index = helper.get_output_index()
    _sourcetype = helper.get_sourcetype()

    # Getting the checkpoint
    checkpoint = helper.get_check_point(input_name)
    if checkpoint is None:
        # Handling upgrade scenario
        from_time_stanza = get_last_alert_timestamp()
        if from_time_stanza is not None:
            checkpoint = from_time_stanza['last_alert_time']

    base_url = helper.get_arg('endgame_api')
    endgame_account = helper.get_arg('endgame_account')
    if endgame_account:
        base_url = endgame_account.get('endgame_api')
    if base_url.endswith('/'):
        base_url = base_url[:-1]

    base_uri = '/api/v1/alerts'
    current_UTC = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    if checkpoint is None or checkpoint == '':
        url = base_url + base_uri + \
            '?update_last_viewed=true&archived=false&order_by=indexed_at'
    else:
        # Increment by 1 millisecond to avoid duplication
        checkpoint = add_timedelta(checkpoint)
        url = base_url + base_uri + '?update_last_viewed=true&archived=false&indexed_from=' + \
            checkpoint+'&order_by=indexed_at'
    url += "&indexed_to=" + current_UTC
    next_page = 'next_page'
    header_endpoint = {'content-type': 'application/json',
                       'Authorization': 'JWT ' + token}
    new_from_time = None
    total = 0

    verify_ssl = helper.get_arg('verify_ssl')
    if verify_ssl.lower() in ["yes", "true", "1"]:
        verify_ssl = True
    else:
        verify_ssl = False

    for x in range(MAX_NUMBER_OF_ITERATIONS):

        try:
            helper.log_info("Invoking using url: "+url)
            api_start_time = time.time()
            endpoint_response = requests.get(
                url, headers=header_endpoint, verify=verify_ssl)
            api_end_time = time.time()
            api_time_taken = api_end_time - api_start_time
            helper.log_info("Alerts -> HTTP Status code:" +
                            str(endpoint_response.status_code))
            helper.log_info('Time taken to invoke api {0}: {1}'.format(
                url, str(api_time_taken)))
        except Exception as error:
            helper.log_info('Error in getting alerts: ' + url + str(error))
            sys.exit()

        response = json.loads(json.dumps(endpoint_response.content))
        metadata = json.loads(response.encode('utf-8'))['metadata']
        data = json.loads(response.encode('utf-8'))['data']
        next_page = metadata['next']

        for event_item in data:
            total = total + 1
            new_from_time = event_item['indexed_at']
            event = helper.new_event(
                source=_source, index=_index, sourcetype=_sourcetype, data=json.dumps(event_item, sort_keys=True))
            ew.write_event(event)

        if next_page == 'null' or next_page is None:
            break

        if checkpoint is None or checkpoint == '':
            url = base_url + base_uri + '?update_last_viewed=true&archived=false&page=' + \
                str(next_page)+'&order_by=indexed_at'
        else:
            url = base_url + base_uri + '?update_last_viewed=true&archived=false&indexed_from=' + \
                checkpoint+'&page='+str(next_page)+'&order_by=indexed_at'
        url += "&indexed_to=" + current_UTC

    if new_from_time is not None and new_from_time not in '':
        current_epoch = convert_to_epoch_timestamp(current_UTC)
        last_indexed_at_epoch = convert_to_epoch_timestamp(new_from_time)

        # Handle future timestamps in data
        if current_epoch < last_indexed_at_epoch:
            new_from_time = current_UTC

        helper.save_check_point(input_name, new_from_time)

    end_time = time.time()
    time_taken = end_time - start_time
    helper.log_info('Total number of alerts: {0}'.format(total))
    helper.log_info(
        'Time taken to fetch and persist alerts: {0}'.format(time_taken))
