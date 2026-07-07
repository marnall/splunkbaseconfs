
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests

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
    #type = definition.parameters.get('type', None)

    # connector_type = definition.parameters.get('connector_type', None)
    
    
    feye_auth_key = definition.parameters.get('feye_auth_key', None)
    url_health = "https://feapi.marketplace.apps.fireeye.com/health"
    headers = {"feye-auth-key": feye_auth_key}
    try:
        response = helper.send_http_request(url=url_health, method='GET',headers=headers, use_proxy=False, timeout=10,verify=False)
        r_status = response.status_code
        if r_status not in (200, 401, 403):
            # check the response status, if the status is not sucessful, raise requests.HTTPError
            raise ValueError(r_status)
        
    
        r_json = response.json()
        status_response = (json.dumps(r_json["status"]))
        if 'failed' in str(status_response):
            message_response = json.dumps(r_json["message"])
            raise ValueError(message_response)
            
    except requests.exceptions.HTTPError as err:
        raise requests.exceptions.HTTPError(
            "An HTTP Error occured while trygin to access the Octopus Deploy API: " + str(err))
            
    
    expiry = definition.parameters.get('expiry', None)
    if (int(expiry)<1) or (int(expiry)>8760):
        raise ValueError("Expiry Value - Minimum is 1 hour, and maximum is 8760 hours")
        
    pass

def collect_events(helper, ew):
    

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    
    opt_type = helper.get_arg('type')
    opt_connector_type = helper.get_arg('connector_type')
    opt_feye_auth_key = helper.get_arg("feye_auth_key")
    opt_expiry = helper.get_arg("expiry")
    
    # In single instance mode, to get arguments of a particular input, use
    #opt_type = helper.get_arg('type', stanza_name)
    #opt_connector_type = helper.get_arg('connector_type', stanza_name)

    # get input type
    #helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    #helper.get_input_stanza()
    # get specific input stanza with stanza name
    #helper.get_input_stanza(stanza_name)
    # get all stanza names
    #helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    #loglevel = helper.get_log_level()
    # get proxy setting configuration
    #proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    #account = helper.get_user_credential_by_username("username")
    #account = helper.get_user_credential_by_id("account id")
    
    
    
    stanza_name = helper.get_input_stanza_names()
    args = helper.get_input_stanza()
    interval = args[stanza_name]["interval"] 
    #interval = 700
    
    # send rest requests to DOD
    url = "https://feapi.marketplace.apps.fireeye.com/telemetry"
    end_time = int(time.time())
    start_time = end_time - int(interval) - 100
    parameters = {"type":opt_type,"start_time":start_time,"end_time":end_time,"connector_type":opt_connector_type}
    headers = {"feye-auth-key":opt_feye_auth_key}
    response = helper.send_http_request(url, 'GET', parameters=parameters, payload=None,headers=headers, cookies=None, verify=False, cert=None,timeout=None, use_proxy=True)
    r_json = response.json()
   
   
    r_status = response.status_code
    if r_status != 200:
        # check the response status, if the status is not sucessful, raise requests.HTTPError
        response.raise_for_status()
    
    
    #Total number of Alert count 
    count = (json.dumps(r_json["count"]))
    
    
    #Grabbing Alerts in batch of 1000 alerts per rest request call from DOD
    start = 0
    size = 1000
    count1 = int(count)
    
    while(count1 > 0):
        parameters = {"type":opt_type,"start_time":start_time,"end_time":end_time,"size":size,"from":start,"connector_type":opt_connector_type}
        headers = {"feye-auth-key":opt_feye_auth_key}
        response = helper.send_http_request(url, 'GET', parameters=parameters, payload=None,headers=headers, cookies=None, verify=True, cert=None,timeout=None, use_proxy=True)
        
        r_status = response.status_code
        if r_status != 200:
        # check the response status, if the status is not sucessful, raise requests.HTTPError
            response.raise_for_status()
            
        r_json = response.json()
        
        #Final alert list removing duplicates based on "report_id"
        final_alert_list=[]
        
        #Creating checkpoint to remove duplicates
        for alert in r_json["data"]:
            state = helper.get_check_point(str(alert["report_id"]))
            if state is None:
        
                final_alert_list.append(alert)
                helper.save_check_point(str(alert["report_id"]), "Indexed")
            #helper.delete_check_point(alert["report_id"]) #only required when testing script
        
        #Index Data into splunk
        event = helper.new_event(json.dumps(final_alert_list), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)
        
        start = start + size   
        count1 = count1 - size
    

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
