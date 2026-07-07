
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
    # cybelangel_reports = definition.parameters.get('cybelangel_reports', None)
    pass

def collect_events(helper, ew):
   

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    # opt_cybelangel_reports = helper.get_arg('cybelangel_reports')
    # In single instance mode, to get arguments of a particular input, use
    # opt_cybelangel_reports = helper.get_arg('cybelangel_reports', first_fetch)
    status = helper.get_arg('status')
    
    

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    # helper.get_input_stanza()
    # get specific input stanza with stanza name
    # helper.get_input_stanza(stanza_name)
    # get all stanza names
    # helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    # proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    # account = helper.get_user_credential_by_username("username")
    # account = helper.get_user_credential_by_id("account id")
    

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(1)


    # get global variable configuration
    helper.log_info("Retrieving Cybelangel Domains")
    global_cybelangel_client_id = helper.get_global_setting("cybelangel_client_id")
    global_cybelangel_client_secret = helper.get_global_setting("cybelangel_client_secret")

    # The following examples send rest requests to some endpoint.
    
    
    
    
    
    #AUTHENTICATE 
    helper.log_info("Authenticating to CybelAngel")
    auth_url = 'https://auth.cybelangel.com/oauth/token'
    
    auth_params = {'content-type': 'application/json'}
    
    auth_payload = payload = {'client_id': global_cybelangel_client_id,'client_secret': global_cybelangel_client_secret,'audience': "https://platform.cybelangel.com/",'grant_type': "client_credentials"}
    

    
    try:
        auth_response = helper.send_http_request(auth_url, 'POST', parameters=auth_params, payload=auth_payload,
                                            headers=None, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=False).json()
        token = 'Bearer ' + auth_response.get('access_token')
                                            
    except Exception as e:
        raise e
        helper.log_critical("Error fetching Token")
    
    
    
  
    
    platform_url = "https://platform.cybelangel.com/api/v1/domains"
    # DOMAINS REQUEST
    
    parameters = {} 
    if status == "monitored":
        helper.log_info("Status is monitored")
        parameters['status'] = 'monitored'
    elif status == "reported":
        parameters['status'] = 'reported'

            
            
    
    
    helper.log_info("Requesting Domains Watchlist from CybelAngel")
    
    headers = {'Content-Type': "application/json",
                  'Authorization': token}
    try:
        response = helper.send_http_request(platform_url, 'GET', 
        parameters=parameters, payload=None,headers=headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=False).json()
    except Exception as e:
        raise e
        helper.log_critical("Failure to request domains endpoint")
        

    
    for domain in response.get('results'):
        event =  helper.new_event(json.dumps(domain), time=domain.get('detection_date'), host=None, index=None, source=None, sourcetype='cybelangeldomains', done=True, unbroken=True)
        ew.write_event(event)                                
                                        
                                        
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
