
# encoding = utf-8

import os
import sys
import time
import datetime


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
    # text = definition.parameters.get('text', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_text = helper.get_arg('text')
    # In single instance mode, to get arguments of a particular input, use
    opt_text = helper.get_arg('text', stanza_name)

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
    global_api_key = helper.get_global_setting("api_key")

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
    import json
    from functools import wraps
    
    def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
        def deco_retry(f):
    
            @wraps(f)
            def f_retry(*args, **kwargs):
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return f(*args, **kwargs)
                    except ExceptionToCheck as e:
                        time.sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                return f(*args, **kwargs)
    
            return f_retry  # true decorator
    
        return deco_retry
    
    @retry(Exception)
    def get(url, params = None, headers = None):
        if not params:
            params = {}
        if not headers:
            headers = {}
        res = helper.send_http_request(url, "get",parameters = params, headers=headers, use_proxy=True)
        res.raise_for_status()
        return res
    
    TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    
    global_api_key = helper.get_global_setting("api_key")
    headers = {"Authorization": f"token {global_api_key}"}
    accounts_url = "https://api.adaptive-shield.com/api/v1/accounts"
    accounts_res = get(accounts_url, headers=headers)
    accounts = accounts_res.json()["data"]
    
    for account in accounts:
        
        # for each account, fetch alerts
        helper.log_info("----------------------------------------------")
        helper.log_info(json.dumps(account))
        account_id = account["id"]
        account_name = account["name"]
        alerts_timestamp_key = f"alerts timestamp {account_id}"
        alerts_id_key = f"alerts id {account_id}"
        
        # use checkpoint to only fetch alerts generated after last alert
        checkpoint_timestamp = helper.get_check_point(alerts_timestamp_key)
        checkpoint_datetime = None
        checkpoint_id = helper.get_check_point(alerts_id_key)
        
        params = {"limit":1}

        if checkpoint_timestamp:
            params["from_date"] = checkpoint_timestamp
            datetime.datetime.strptime(checkpoint_timestamp, TIME_FORMAT)
        
        alerts_url = f"https://api.adaptive-shield.com/api/v1/accounts/{account_id}/alerts"
        alerts_res = get(alerts_url, headers=headers, params=params)
        alerts = alerts_res.json()["data"]
        next_page_uri = alerts_res.json().get("next_page_uri",None)
        most_recent_timestamp = checkpoint_timestamp
        most_recent_datetime = checkpoint_datetime
        most_recent_id = checkpoint_id
        def create_event(alert):
            if alert["id"] == checkpoint_id:
                return
            alert_datetime = datetime.datetime.strptime(alert["timestamp"], TIME_FORMAT)
            if not checkpoint_datetime or alert_datetime > checkpoint_datetime:
                most_recent_timestamp = alert["timestamp"]
                most_recent_datetime = alert_datetime
                most_recent_id = alert["id"]
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(alert))
            ew.write_event(event)
        page = 0
        for alert in alerts:
            create_event(alert)
        while next_page_uri:
            page +=1
            if page == 500:
                break
            alerts_res = get(next_page_uri, headers=headers)
            alerts = alerts_res.json()["data"]
            next_page_uri = alerts_res.json().get("next_page_uri",None)
            for alert in alerts:
                create_event(alert)
        account_name = account["name"]
        helper.log_info(f"finished with {account_name}")
        helper.save_check_point(alerts_timestamp_key, checkpoint_timestamp)
        helper.save_check_point(alerts_id_key, checkpoint_id)
        
    
    
    
    
    
    
    
    
    
    
    
    
