
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    # token_url = definition.parameters.get('token_url', None)
    # violation_url = definition.parameters.get('violation_url', None)
    # channel_url = definition.parameters.get('channel_url', None)
    # channel_ids = definition.parameters.get('channel_ids', None)
    # statuses = definition.parameters.get('statuses', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_token_url = helper.get_arg('token_url')
    opt_violation_url = helper.get_arg('violation_url')
    opt_channel_url = helper.get_arg('channel_url')
    opt_channel_ids = helper.get_arg('channel_ids')
    opt_channel_statuses = helper.get_arg('channel_statuses')
    opt_channel_statuses1 = helper.get_arg('channel_statuses1')
    # In single instance mode, to get arguments of a particular input, use
    opt_token_url = helper.get_arg('token_url', stanza_name)
    opt_violation_url = helper.get_arg('violation_url', stanza_name)
    opt_channel_url = helper.get_arg('channel_url', stanza_name)
    opt_channel_ids = helper.get_arg('channel_ids', stanza_name)
    opt_statuses = helper.get_arg('statuses', stanza_name)

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
    global_username = helper.get_global_setting("username")
    global_password = helper.get_global_setting("password")
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")

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

    # get global variable configuration
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    global_username = helper.get_global_setting("username")
    global_password = helper.get_global_setting("password")
    opt_token_url = helper.get_arg('token_url')
    opt_violation_url = helper.get_arg('violation_url')
    opt_channel_ids = helper.get_arg('channel_ids')
    opt_statuses = helper.get_arg('statuses')
    opt_channel_url = helper.get_arg('channel_url')
    opt_statuses = helper.get_arg('statuses')
    opt_channel_statuses = helper.get_arg('channel_statuses')
    opt_channel_statuses1 = helper.get_arg('channel_statuses1')
    opt_checkpoint = helper.get_arg('checkpoint')
    helper.log_debug(global_client_id)
    inputname = helper.get_input_stanza_names()
    inputtype = helper.get_input_type()
    inputsource = inputtype + ":" + inputname
    

    # Make the request to get a token
    
    login_url = "https://uat.safeguardcyber.app/safeguard/api/oauth/token"
    
    login_params = {
        'grant_type': 'password',
        'client_id': global_client_id,
        'client_secret': global_client_secret,
        'username': global_username,
        'password': global_password 
    }
    
    r = requests.post(opt_token_url, data=login_params)
    r = r.text
    helper.log_debug('GOT TEXT: ' + str(r))
    r = json.loads(r)
    helper.log_debug("GOT TOKEN: " + str(r) + " type: " + str(type(r)))
    access_token = r['access_token']
    helper.log_debug('ACCESS TOKEN: '+ str(access_token))    
    
    headers = {
                'Authorization': 'Bearer ' + str(access_token),
                'Accept': 'application/json;odata=nometadata'
              }
              
    violation_params = {'channelIds': opt_channel_ids,
                        'statuses': opt_statuses}
    
    channel_params = {'channel_status': opt_channel_statuses1}
    
    channel_list = []
    dedup_list = []
    channel = helper.send_http_request(opt_channel_url, 'GET', parameters=channel_params, payload=None, headers=headers, verify=False, use_proxy=True, cookies=None, cert=None, timeout=None)
    channel_data = channel.json()
    
    for chnl in channel_data['channels']:
        channel_list.append(str(chnl['id']))
        
    for d in channel_list:
        if d not in dedup_list:
            dedup_list.append(d)
    number_of_elements = len(dedup_list)

    number_of_elements2 = len(opt_channel_ids.split(','))
    translation = {39: None}
    
    final_result = []
    if opt_channel_ids.upper()=='ALL':
        selected_channels = dedup_list
    elif opt_channel_ids=='':
        selected_channels = dedup_list
    elif opt_channel_ids=='*':
        selected_channels = dedup_list
    else:
        selected_channels = opt_channel_ids.split(',')
    
    length = len(selected_channels)
    #checkpoint = ""
    
    for sc in range(length):
        
        new_results = True
        istart = 0
        data = None
        
        while new_results:
            violation_params = {'channelIds': (selected_channels[sc]),
                                'statuses': opt_statuses,
                                'start': istart}
                                
            try:
                violations = helper.send_http_request(opt_violation_url, 'GET', parameters=violation_params, payload=None, headers=headers, verify=False, use_proxy=True, cookies=None, cert=None, timeout=None)
                data2 = violations.json()
                event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str(selected_channels[sc]))
                ew.write_event(event) 
                
            except Exception as exception:
                event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str('error - bad channelId'))
                ew.write_event(event)     
    
    
    
    
    
    try:
        for sc in range(length): 
            
            #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str("Inside the Try"))
            #ew.write_event(event) 
            
            new_results = True
            istart = 0
            data = None
            
            while new_results:
                violation_params = {'channelIds': (selected_channels[sc]),
                                'statuses': opt_statuses,
                                'start': istart}

                violations = helper.send_http_request(opt_violation_url, 'GET', parameters=violation_params, payload=None, headers=headers, verify=False, use_proxy=True, cookies=None, cert=None, timeout=None)
                data2 = violations.json() 
                #new_results = violations.get("values", [])
                #final_result = []
            
            
                #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=json.dumps(data2))
                #ew.write_event(event) 
            
            
                #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str(" "))
                #ew.write_event(event) 
                
                #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str(istart))
                #ew.write_event(event)
            
                istart += 20
                new_results = istart < int(str(data2['total']))
            
                if int(str(data2['count'])) > 0:
                    for vltn in data2['values']:
                        final_result = []
                        #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str("Inside the outer for loop"))
                        #ew.write_event(event) 
                    
                        final_result.append(vltn)         
                        #state = helper.get_check_point(str(vltn["threadId"]))
                        #state = helper.get_check_point(str(checkpoint))
                        vltnlength = len(vltn["violation"])
                        l = []
                        l.append(str(vltn["messageId"]))
                        for vc in range(vltnlength):
                        
                            #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str("Inside second for loop"))
                            #ew.write_event(event) 
                        
                            x = vc + 1
                            l.append(str(vltn["violation"][vc]['id']))
                            l.append(str(vltn["violation"][vc]['status']))
                        
                        
                            if x == vltnlength:
                                checkpoint = ''.join(l)
                                state = helper.get_check_point(str(checkpoint))
                                #
                                #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str(" "))
                                #ew.write_event(event) 
                                #
                                #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str(checkpoint))
                                #ew.write_event(event)  
                                #
                                #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str(" "))
                                #ew.write_event(event) 
                                #
                                #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str(state))
                                #ew.write_event(event) 
                            
                                #helper.delete_check_point(str(checkpoint))
                                #if state is None:
                                
                                    #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str("10"))
                                    #ew.write_event(event) 
                                
                                
                                    #helper.save_check_point(str(checkpoint), "Indexed")
                                    #final_result.append(vltn)
                                    #state = helper.get_check_point(str(checkpoint))

                                if opt_checkpoint == True:
                                    #pass
                                    if state is None:
                                    
                                        #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str("10"))
                                        #ew.write_event(event) 
                                        helper.save_check_point(str(checkpoint), "Indexed")
                                        final_result.append(vltn)
                                    
                                        event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=json.dumps(final_result))
                                        ew.write_event(event) 
                                else:
                                
                                    helper.delete_check_point(str(checkpoint))
                                    event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=json.dumps(final_result))
                                    ew.write_event(event) 
                                    
                                    #event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str("11"))
                                    #ew.write_event(event) 
                                    
    except:    
            event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),data=str('error - bad channelId'))
            ew.write_event(event) 

    
 
        