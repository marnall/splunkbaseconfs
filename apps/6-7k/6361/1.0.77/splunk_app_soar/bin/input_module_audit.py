# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.
# encoding = utf-8

import os
import json
import dateutil.parser as dp
import requests
from datetime import datetime, timedelta
from urllib.parse import quote

import splunk
import splunk.rest

from soar_imports import (APP_NAME, SOAR_CONF_PROPS)

SOAR_CONF_FILE_LOCAL = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_NAME, 'local', 'soar.conf')
SOAR_CONF_FILE_DEFAULT = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_NAME, 'default', 'soar.conf')
CERT_FILE_LOCATION_DEFAULT = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_NAME, 'default', 'cert_bundle.pem')
CERT_FILE_LOCATION_LOCAL = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_NAME, 'local', 'cert_bundle.pem')

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
    # start = definition.parameters.get('start', None)
    # global_account = definition.parameters.get('global_account', None)
    pass

def _get_time(iso_time):
    parsed_time = dp.parse(iso_time)
    time_in_seconds = parsed_time.strftime('%s')
    milliseconds = iso_time[19:-4]
    float_time = f"{time_in_seconds}{milliseconds}"
    return float(float_time)

def _set_proxy(proxy):
    if proxy is None:
        return None
    else:
        if isinstance(proxy, dict):
            for key, value in proxy.items():
                return { key: value }
            else:
                return { 'https': proxy }
        if isinstance(proxy, str):
            return { 'https': proxy }
    return None

def check_is_shclustered(helper):
    session = helper.get_session()
    unused_response, content = splunk.rest.simpleRequest('/shcluster/config', 
            sessionKey=session, 
            getargs={'output_mode': 'json'})
    
    mode = json.loads(content)['entry'][0]['content']['mode']
    
    if mode == 'disabled':
        return False
    
    is_victoria = check_is_victoria(helper)
    if is_victoria is True:
        return False

    return True

def check_is_victoria(helper):
    session = helper.get_session()

    try:
        unused_response, content = splunk.rest.simpleRequest('/services/search/distributed/bucketmap', 
                sessionKey=session, 
                getargs={'output_mode': 'json'})
        try:
            result = json.loads(content.decode('utf-8'))
            if result.get('messages') == []:
                return True

            if result.get('messages', [])[0].get('type') == 'ERROR' or 'Noah is not enabled on this machine.' in result.get('messages', [])[0].get('text', ''):
                return False
        except:
            return True
    except splunk.ResourceNotFound:
        return False
    except:
        return False
    

def check_is_captain(helper):
    session = helper.get_session()
    unused_response, content = splunk.rest.simpleRequest('/server/info/server-info', 
            sessionKey=session, 
            getargs={'output_mode': 'json'})
    
    server_roles = json.loads(content)['entry'][0]['content']['server_roles']

    if 'shc_captain' in server_roles:
        return True
    return False

def is_correct_node(helper):
    # if this is a standalone instance, script should run
    # if this is a SHC, check if this is the captain
    #    if this is the captain, script should run. else, do not run

    is_clustered = check_is_shclustered(helper)
    if is_clustered:
        is_captain = check_is_captain(helper)
        if is_captain:
            return True
        return False
    else:
        return True

def check_cert(helper):
    session = helper.get_session()
    path = quote(f"{SOAR_CONF_PROPS}/verify_certs")
    args = {
        'method': 'GET',
        'sessionKey': session,
        'getargs': {'output_mode': 'json'}
    }
    unused_response, content = splunk.rest.simpleRequest(path, **args)
    value = json.loads(content)['entry'][0].get('content', 1)
    if value in [1, "1", True, "true"]:
        return True
    return False

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_start = helper.get_arg('start')
    opt_global_account = helper.get_arg('global_account')
    # In single instance mode, to get arguments of a particular input, use
    opt_start = helper.get_arg('start', stanza_name)
    opt_global_account = helper.get_arg('global_account', stanza_name)

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
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

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
    # check the response status, if the status is not successful, raise requests.HTTPError
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

    should_write_events = is_correct_node(helper)

    opt_start = helper.get_arg('start')
    opt_index = helper.get_arg('index')
    opt_name = helper.get_arg('name')
    opt_global_account = helper.get_arg('global_account')
    helper.log_info(f"Querying {opt_global_account.get('custom_name')} for audit logs and posting to {opt_index} index...")

    # Use checkpoint file to avoid duplicates
    file_name = f"{opt_global_account.get('name')}_{opt_name}"
    checkpoint_location = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'lib', 'splunk', 'modinputs', 'audit', file_name)

    if os.path.isfile(checkpoint_location):
        helper.log_info(f"Checkpoint file exists")
        with open(checkpoint_location, "r") as f:
            f_content = json.load(f)
        checkpoint_start_time = f_content.get('last_time')
        if checkpoint_start_time:
            opt_start = checkpoint_start_time
            helper.log_info(f"Using checkpoint last_time. Starting at {checkpoint_start_time}")
    else:
        helper.log_info(f"Checkpoint file does not yet exist")


    custom_name = opt_global_account.get('custom_name')
    server = opt_global_account.get('server')
    auth_token = opt_global_account.get('password')
    soar_proxy = opt_global_account.get('soar_proxy')
    proxy = _set_proxy(soar_proxy)

    if not server.lower().startswith('https://'):
        raise Exception("SOAR only supports https, please update your server config.")

    url = f"{server}/rest/audit?start={opt_start}"
    auth_headers = { 'ph-auth-token': auth_token }

    verify = check_cert(helper)
    if verify and os.path.isfile(CERT_FILE_LOCATION_LOCAL):
        verify = CERT_FILE_LOCATION_LOCAL
    elif verify and os.path.isfile(CERT_FILE_LOCATION_DEFAULT):
        verify = CERT_FILE_LOCATION_DEFAULT

    last_time = None
    try:
        response = requests.get(url, headers=auth_headers, verify=verify, proxies=proxy)
        if response.status_code == 200:
            json_response = response.json()
            # helper.log_debug(f"DEBUG: last event time: {json_response[-1].get('TIME')}")
            
            # Find where to cut results so that no dup events
            stop_at = len(json_response)
            for item in range(len(json_response) -1, -1, -1):
                t1 = json_response[item].get('TIME')
                t2 = json_response[item-1].get('TIME')
                t1 = datetime.strptime(json_response[item].get('TIME'), "%Y-%m-%dT%H:%M:%S.%fZ")
                t2 = datetime.strptime(json_response[item-1].get('TIME'), "%Y-%m-%dT%H:%M:%S.%fZ")
                if t1.minute != t2.minute:
                    stop_at = item
                    break

            helper.log_info(f"{stop_at} new items found for {opt_global_account.get('custom_name')}")
            for item in json_response[0:stop_at]:
                if should_write_events is True:
                    data = json.dumps(item)
                    iso_time = item.get('TIME', '')
                    time = _get_time(iso_time)
                    index = None if opt_index == 'default' else opt_index
                    event = helper.new_event(data, time=time, host=server, index=index, source=custom_name, sourcetype="soar", done=True, unbroken=True)
                    ew.write_event(event)

                last_time = item.get('TIME')
                # helper.log_debug(f"TIME: {last_time}")

            if last_time:
                last_time = datetime.strptime(last_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                last_time += timedelta(minutes=1)
                # last_time = last_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                last_time = last_time.strftime("%Y-%m-%dT%H:%M:00.000000Z")
            
            if last_time is not None:
                helper.log_info(f"Saving checkpoint time: {last_time}")
                with open(checkpoint_location, "w") as f:
                    f.write(json.dumps({"last_time": last_time}))

        else:
            json_response = response.json()
            helper.log_info(f"Error retrieving data from SOAR: Status Code: {response.status_code} Message: {json_response.get('message')}")
    except Exception as e:
        if "check_hostname requires server_hostname" in str(e):
            helper.log_error(f"Error retrieving data from SOAR: Please verify connection to SOAR, including proxy")
        else:
            helper.log_error(f"Error retrieving data from SOAR: {e}")
