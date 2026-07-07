
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



def is_valid_date(date_str, date_format):
    try:
        datetime.datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False



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
    first_fetch = helper.get_arg('first_fetch')
    
    

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
    helper.set_log_level("critical")


    # get global variable configuration
    helper.log_info("Retrieving Cybelangel Credentials")
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
        
        # raise TypeError(token)    
                                            
    except Exception as e:
        helper.log_critical("Error fetching Token")
        raise e
        
    
    
    
  
    
    
    # REPORTS REQUEST
    parameters = {'end-date': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")}
    
    last_run = helper.get_check_point('last_run')
    
    if last_run and is_valid_date(last_run,"%Y-%m-%dT%H:%M"):
        helper.log_info("Retrieving last_request date from checkpoint")
        
        parameters['start-date'] = last_run
        helper.save_check_point('last_run', datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M"))
    
    else:
        helper.log_info("Using first fetch date to retrieve historical reports")
        parameters['start-date'] = first_fetch
        helper.save_check_point('last_run', datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M"))
            
    # raise TypeError(parameters)
    

    
   # REQUESTING REPORTS FROM CYBELANGEL 
    helper.log_info("Requesting Reports from CybelAngel")
    platform_url = "https://platform.cybelangel.com/api/v2/reports"
    headers = {'Content-Type': "application/json",
                  'Authorization': token}
    try:
        response = helper.send_http_request(platform_url, 'GET', 
        parameters=parameters, payload=None,headers=headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=False).json()
        # raise TypeError(response)
        
    except Exception as e:
        helper.log_critical("Failure to request reports endpoint")
        raise e
        
        
    
    

    for report in response.get('reports'):
        helper.log_info(f"Writing new event - {report.get('id')}")
        event =  helper.new_event(json.dumps(report), time=report.get('created_at'), host=None, index=None, source=None, sourcetype='cybelangelreports', done=True, unbroken=True)
        ew.write_event(event)                                
                                        
                                        
    helper.save_check_point('last_run', datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M"))

