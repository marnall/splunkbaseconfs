
# encoding = utf-8

import os
import sys
import time
import datetime
import json

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
    # base_url = definition.parameters.get('base_url', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_base_url = helper.get_arg('base_url')
    # In single instance mode, to get arguments of a particular input, use
    opt_base_url = helper.get_arg('base_url', stanza_name)

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
    
    loglevel = helper.get_log_level()
    strInputName=helper.get_input_type()

    # Build the timestamp to use in the API request URL
    dtNow = datetime.datetime.now()
    strNow = dtNow.strftime("%Y-%m-%dT%H:%MZ")

    strURLBase = "https://api.carbonintensity.org.uk/"
    strURLPath = helper.get_arg('url_path')
    strURLPath = strURLPath.replace("{from}", strNow)
    
    strURL = strURLBase+strURLPath
      
    method = "GET"
    headers = {'Accept': 'application/json'}
    
    helper.log_info("Input="+strInputName+", State=Making HTTP Request, Request_URL= "+strURL)

    # Make the request
    response = helper.send_http_request(strURL, method, parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=False)
    
    # Extract required details from the response
    strData = response.text
    strStatusCode=str(response.status_code)
    
    helper.log_debug("Input="+strInputName+", State=HTTP Request Complete, status_code="+strStatusCode+", text="+strData)

    
    if response.status_code!=200:
        helper.log_error("Input="+strInputName+", State=HTTP Response is not 200 so exiting, status_code="+strStatusCode)
    else:
        objData=json.loads(strData) 
        if "data" not in objData:
            helper.log_error("Input="+strInputName+", State=JSON response does not include 'data' so exiting, text="+strData)
        else:
            # Count the events found, for logging purposes
            intEventCount=0
            for objEvent in objData['data']:
                # Iterate through each of the returned records
                strEvent=json.dumps(objEvent)
                helper.log_debug("Input="+strInputName+", State=Found event, text="+strEvent)
                intEventCount+=1
                
                # Create event in Splunk
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=strEvent)
                ew.write_event(event)
                
            helper.log_info("Input="+strInputName+", State=Saved "+str(intEventCount)+" events with _time="+dtNow.strftime("%Y-%m-%d %H:%M:%S"))
