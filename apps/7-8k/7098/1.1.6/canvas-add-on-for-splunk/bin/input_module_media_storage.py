
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
    # subdomain = definition.parameters.get('subdomain', None)
    # access_token = definition.parameters.get('access_token', None)
    pass

def collect_events(helper, ew):

    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_add_on_setup_parameter_setting = helper.get_arg('add_on_setup_parameter_setting')
    opt_override = helper.get_arg('override')
    opt_subdomain = helper.get_arg('subdomain')
    opt_access_token = helper.get_arg('access_token')
    # get global variable configuration
    global_subdomain_1 = helper.get_global_setting("subdomain_1")
    global_access_token_1 = helper.get_global_setting("access_token_1")
    global_subdomain_2 = helper.get_global_setting("subdomain_2")
    global_access_token_2 = helper.get_global_setting("access_token_2")
    global_subdomain_3 = helper.get_global_setting("subdomain_3")
    global_access_token_3 = helper.get_global_setting("access_token_3")
    global_subdomain_4 = helper.get_global_setting("subdomain_4")
    global_access_token_4 = helper.get_global_setting("access_token_4")
    
    
    if(opt_override==True):
        # User needs to have an access token as Data Input Parameter.
        # Access token should have been generated in canvas account.
        # User needs to provide API endpoint subdomain as Data Input Parameter.
        access_token = f"{opt_access_token}"
        subdomain = f"{opt_subdomain}"
        
    else:
        if(opt_add_on_setup_parameter_setting=='subdomain 2'):
            # User needs to have an access token as Data Input Parameter.
            # Access token should have been generated in canvas account.
            # User needs to provide API endpoint subdomain as Data Input Parameter.
            access_token = f"{global_access_token_2}"
            subdomain = f"{global_subdomain_2}"
            
        elif(opt_add_on_setup_parameter_setting=='subdomain 3'):
            # User needs to have an access token as Data Input Parameter.
            # Access token should have been generated in canvas account.
            # User needs to provide API endpoint subdomain as Data Input Parameter.
            access_token = f"{global_access_token_3}"
            subdomain = f"{global_subdomain_3}"
            
            global_subdomain = global_subdomain_3
        elif(opt_add_on_setup_parameter_setting=='subdomain 4'):
            # User needs to have an access token as Data Input Parameter.
            # Access token should have been generated in canvas account.
            # User needs to provide API endpoint subdomain as Data Input Parameter.
            access_token = f"{global_access_token_4}"
            subdomain = f"{global_subdomain_4}"
        else:
            # User needs to have an access token as Data Input Parameter.
            # Access token should have been generated in canvas account.
            # User needs to provide API endpoint subdomain as Data Input Parameter.
            access_token = f"{global_access_token_1}"
            subdomain = f"{global_subdomain_1}"
    #Replace with required endpoint.
    opt_url_endpoint = "media_objects"
    
    url = f"https://{subdomain}.instructure.com/api/v1/{opt_url_endpoint}"
    
    parameters = {}
    headers = {'Authorization': 'Bearer ' + access_token}
    
    # The following example sends a GET requests to the defined endpoint.
    response = helper.send_http_request(url, "get", parameters=parameters, headers=headers)
    
    response.raise_for_status()
    data = response.json()
    
    try:
        for item in data:
            
        # Check if id is already ingested
            event_id = str(item["id"])
            key_state = helper.get_check_point(event_id)
            if key_state is not None:
                helper.log_debug("Already ingested key '{0}', skipping.".format(event_id))
                continue

            stanza_name = helper.get_input_stanza_names()
            
            
            event = helper.new_event(json.dumps(item), source=helper.get_input_type(), 
                                    index=helper.get_output_index(stanza_name), 
                                    sourcetype=helper.get_sourcetype())
            ew.write_event(event)
            helper.log_debug("Just indexed event with id {0}".format(event_id))
            helper.save_check_point(event_id, "ingested")    
        helper.log_debug("Done with event list")
    
    except KeyError as key_e:
        helper.log_critical("Key {0} not found at data parsing".format(key_e))
        