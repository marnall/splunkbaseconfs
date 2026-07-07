
# encoding = utf-8

import os
import sys
import time
import datetime
import time as mytime
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
    # organization_id = definition.parameters.get('organization_id', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_organization_id = helper.get_arg('organization_id')
    # In single instance mode, to get arguments of a particular input, use
    opt_organization_id = helper.get_arg('organization_id', stanza_name)

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
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    global_refresh_token = helper.get_global_setting("refresh_token")

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
    
    loglevel ="debug"
    
    proxy_settings = helper.get_proxy()

    index = helper.get_output_index()
    source = helper.get_input_type() + "://" + helper.get_input_stanza_names()
    sourcetype = helper.get_sourcetype()
    host = "api.ciscospark.com"
    organization_id = helper.get_arg("organization_id")

    client_id = helper.get_global_setting('client_id')
    client_secret = helper.get_global_setting('client_secret')
    refresh_token_name = helper.get_arg('refresh_token')
    refresh_token = helper.get_global_setting(refresh_token_name)
    certificate_verification = True if (helper.get_global_setting('certificate_verification') == 1) else False
    
    helper.log_debug("certificate_verification: {}".format(certificate_verification))
    
    helper.log_debug("client_id: {}".format(client_id))
    helper.log_debug("refresh_token_name: {}".format(refresh_token_name))
    
    checkpoint_name = "last_run_" + client_id + "_" + helper.get_input_stanza_names()
    access_token_name = "access_token_" + client_id + "_" + refresh_token_name
    access_token_expiration_time_name = "access_token_expiration_time_" + client_id + "_" + refresh_token_name
    
    helper.log_debug("checkpoint_name: {}".format(checkpoint_name))
    helper.log_debug("access_token_expiration_time_name (checkpoint): {}".format(access_token_expiration_time_name))

    access_token_url = "https://api.ciscospark.com/v1/access_token" 

    access_token_expiration_time =  helper.get_check_point(access_token_expiration_time_name)
    access_token =  helper.get_check_point(access_token_name)

    helper.log_debug("access_token_expiration_time (checkpoint): {}".format(access_token_expiration_time))
    
    # Used for access token expiry
    current_run_epoch =  int(mytime.time())*1000
    
    # Used for checkpointing
    current_run = datetime.datetime.utcnow().isoformat()[:-3] + 'Z'
    
    last_run =  helper.get_check_point(checkpoint_name)
    # Overrride once to get old events
    #last_run = '2020-07-10T09:34:00.000Z'
    
    if last_run is None:
        last_run = current_run
        # We need a small offset as API does not allow this to be the same
        current_run_epoch =  int(mytime.time())*1000
        current_run = datetime.datetime.utcnow().isoformat()[:-3] + 'Z'
    
    # Access Token Management

    if access_token is None or access_token_expiration_time is None or access_token_expiration_time<=current_run_epoch:
        helper.log_info("Refreshing access_token")
        helper.log_debug("access_token_expiration_time: {}".format(access_token_expiration_time))

        headers = {
        'Content-Type' : 'application/x-www-form-urlencoded',
        'Accept' : 'application/json',
        'cache-control' : 'no-cache'
        }
        
        payload = 'grant_type=refresh_token&client_id={}&client_secret={}&refresh_token={}'.format(client_id,client_secret,refresh_token)
    
        method = "POST"

        helper.log_debug("payload: {}".format(payload))

        response = helper.send_http_request(access_token_url, method, parameters=None, payload=payload, headers=headers, cookies=None, verify=certificate_verification, cert=None, timeout=None, use_proxy=True)
       
        response_dict = response.json()

        if response.status_code != 200:
            helper.log_error("status_code: {}. Exiting.".format(response.status_code))
            helper.log_error("response: {}".format(response_dict))
    
            sys.exit()
        else:
            helper.log_info("status_code: {}.".format(response.status_code))
            helper.log_debug("response: {}".format(response_dict))
            
            access_token = response_dict.get("access_token")
            access_token_expires_in = response_dict.get("expires_in")
            
            helper.log_debug("access_token: {}".format(access_token))
    
            access_token_expiration_time = current_run_epoch + access_token_expires_in*1000
            helper.log_debug("current_run_epoch: {}".format(current_run_epoch))
            helper.log_debug("access_token_expires_in: {}".format(access_token_expires_in))
            helper.log_debug("access_token_expiration_time: {}".format(access_token_expiration_time))
            
            helper.log_info("Storing news access_token_expiration_time")
            helper.save_check_point(access_token_expiration_time_name, access_token_expiration_time)
            helper.log_info("Storing new access_token")
            helper.save_check_point(access_token_name, access_token)
            
    else:
            helper.log_info("Current access_token still valid.")

        
    # Fetching Events:
    
    #last_run = '2020-03-24T09:34:00.000Z'
    #current_run = '2020-03-25T10:34:00.000Z'
    
    
    events_url = 'https://api.ciscospark.com/v1/adminAudit/events?orgId='+organization_id+'&from={}&to={}'.format(last_run, current_run)
    
    headers = {
        'Content-Type' : 'application/x-www-form-urlencoded',
        'Accept' : 'application/json',
        'cache-control' : 'no-cache',
        'Authorization' : 'Bearer {}'.format(access_token)
        }
    
    method = "GET"
    
    helper.log_debug("headers: {}".format(headers))
    helper.log_debug("events_url: {}".format(events_url))
    
    
    paging = True
    
    while paging == True:

        response = helper.send_http_request(events_url, method, parameters=None, payload=None, headers=headers, cookies=None, verify=certificate_verification, cert=None, timeout=None, use_proxy=True)
           
        response_dict = response.json()
    
        if response.status_code != 200:
            helper.log_error("status_code: {}. Exiting.".format(response.status_code))
            helper.log_error("response: {}".format(response_dict))
        
            sys.exit()
            
        else:
            helper.log_info("status_code: {}.".format(response.status_code))

            response_headers = response.headers
            helper.log_debug("response_headers: {}.".format(response_headers))

            for data in response_dict.get("items"):
                #helper.log_debug("data: {}".format(json.dumps(data)))
                event = helper.new_event(data=json.dumps(data), host=host, index=index, source=source, sourcetype=sourcetype)
                ew.write_event(event)

            # Handle Paging
            
            link = json.dumps(response_headers.get("Link"))
            
            if link is not None and link is not "null":
                
                helper.log_debug("link (next): {}.".format(link))
            
                events_url = link[2:].replace(r'>; rel=\"next\""','')
                helper.log_debug("events_url (next): {}.".format(events_url))
            
            else:
                paging = False
            

            
    helper.save_check_point(checkpoint_name, current_run)
    helper.log_info("Storing new checkpoint")
    
    helper.log_info("Finished.")
    
            
    
