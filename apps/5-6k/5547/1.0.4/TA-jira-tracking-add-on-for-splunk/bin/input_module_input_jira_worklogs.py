
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import re
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from urllib.request import urlopen, URLError

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
    # reset_checkpoint = definition.parameters.get('reset_checkpoint', None)
    
    url_base = definition.parameters.get('url_base', None)
    
        
    if not validate_https(url_base):
        raise ValueError("Requires HTTPS")

    if not validate_web_url(url_base):
        raise ValueError("URL base error.")

    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_global_account = helper.get_arg('global_account')
    opt_reset_checkpoint = helper.get_arg('reset_checkpoint')
    # In single instance mode, to get arguments of a particular input, use
    opt_global_account = helper.get_arg('global_account', stanza_name)
    opt_reset_checkpoint = helper.get_arg('reset_checkpoint', stanza_name)

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
    global_url_base = helper.get_global_setting("url_base")
    global_user = helper.get_global_setting("user")
    global_api_token = helper.get_global_setting("api_token")

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
    
    helper.log_debug("action=start, function="+collect_events.__name__)
    
    # credentials
    global_account = helper.get_arg("global_account")
    auth = HTTPBasicAuth(global_account.get("username"), global_account.get("password"))
    
    # gets results from REST API calls
    res = get_worklogs_results(auth, helper)
    
    # write events in JSON format 
    for value in res:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(value, ensure_ascii = False))
        try:
            ew.write_event(event)
        except Exception as e:
            raise e
    
    helper.log_info("action=success")
    
    
def get_worklogs_results(auth, helper):
# Gets worklogs from JIRA REST API, and manages checkpointing
# In:  auth: authentication data
#      helper: Splunk helper
# Out: worklogs

    # init
    result = []
    opt_reset_checkpoint = helper.get_arg('reset_checkpoint')
    
    # checkpoint key
    key=helper.get_input_stanza_names()
    
    # reset checkpoint
    if (opt_reset_checkpoint): 
        helper.log_debug("action=reset_checkpoint, function="+get_worklogs_results.__name__)
        helper.delete_check_point(key)
    
    # get checkpoint
    state = helper.get_check_point(key)
    since = 0 if state == None else state
    helper.log_debug("action=get_checkpoint, checkpoint="+str(state)+", function="+get_worklogs_results.__name__)
    
    last_page=False
    while not last_page:    
        # get worklogs ids results
        res_ids = get_worklogs_ids(auth, since, helper)
        last_page=res_ids["lastPage"]
        since=res_ids["until"] + 1
        
        # append worklogs ids
        list_worklogs = []
        for worklog_id in res_ids["values"]:
            list_worklogs.append(worklog_id["worklogId"])
        
        # get worklogs
        res_worklogs = get_worklogs(auth, list_worklogs, helper)
        
        # append worklogs
        for worklog in res_worklogs:
            result.append(worklog)
    
    helper.log_debug("action=collect, total="+str(len(result))+", function="+get_worklogs_results.__name__)
        
    # set checkpoint
    state=since
    helper.save_check_point(key, state)
    helper.log_debug("action=set_checkpoint, checkpoint="+str(state)+", function="+get_worklogs_results.__name__)
    
    # return worklogs list
    return result
    
    
def get_worklogs_ids(auth, since, helper):
# get worklogs ID since 'since', gets up to 1000 ID
# In:  auth: authentication data
#      since: timestamp UNIX in ms
#      helper: Splunk helper
# Out: worklogs ID list
    
    opt_url = helper.get_arg('url_base')
    url = opt_url + "/rest/api/2/worklog/updated"

    headers = {"Accept": "application/json"}
    
    query = {
        'since': str(since)
    }
    
    response = requests.request(
       "GET",
       url,
       headers=headers,
       params=query,
       auth=auth
    )
    
    helper.log_debug("action=collect, status="+str(response.raise_for_status())+", function="+get_worklogs_ids.__name__)
    
    return json.loads(response.text)
    

def get_worklogs(auth, ids, helper):
# get worklogs by id form JIRA, gets up to 1000 worklogs
# In:  auth: authentication data
#           ids: worklog id list
#           helper: Splunk helper
# Out:   worklogs list
    
    opt_url = helper.get_arg('url_base')
    url = opt_url + "/rest/api/2/worklog/list"
    
    headers = {
       "Accept": "application/json",
       "Content-Type": "application/json"
    }

    payload = json.dumps( {
      "ids": ids
    } )

    response = requests.request(
       "POST",
       url,
       data=payload,
       headers=headers,
       auth=auth
    )
    
    helper.log_debug("action=collect, status="+str(response.raise_for_status())+", function="+get_worklogs.__name__)
    
    return json.loads(response.text)
    
    
def validate_web_url(url):
    try:
        urlopen(url)
        return True
    except URLError:
        return False

def validate_https(url):
    match = re.search("^https.*", url)
    return match is not None
    