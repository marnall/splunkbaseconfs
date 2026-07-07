
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json


def get_host(api_key,org):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get(f'https://api.meraki.com/api/v1/organizations/{org}', headers=headers)
    response_dict=json.loads(response.text)
    url = response_dict['url']
    host=url.split("/")[2:][0]
    return(host)

def get_devices(api_key,org):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get(f'https://api.meraki.com/api/v1/organizations/{org}/networks', headers=headers)
    data = json.loads(response.text)
    my_length=len(data)
    list_of_networks=[]
    for i in range(my_length):
        list_of_networks.append(data[i]["id"])
    return(list_of_networks)

def get_data(api_key,org,network_list):
    final_list=[]
    for network in network_list:
        headers = {'X-Cisco-Meraki-API-Key': api_key}
        network_name=requests.get(f'https://api.meraki.com/api/v1/networks/{network}/', headers=headers)
        nname_json=json.loads(network_name.text)
        network_name=nname_json['name']
        add_json={"NetworkName":network_name}
        response = requests.get(f'https://api.meraki.com/api/v1/networks/{network}/devices', headers=headers)
        all_data=json.loads(response.text)
        length=len(all_data)
        for x in range(length):
            mydict=all_data[x]
            mydict.update({"NetworkName":network_name})
            final_list.append(mydict)
    return(final_list)

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
    # enable = definition.parameters.get('enable', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_enable = helper.get_arg('enable')
    # In single instance mode, to get arguments of a particular input, use
    #opt_enable = helper.get_arg('enable', stanza_name)

    # get input type
#    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
#    helper.get_input_stanza()
    # get specific input stanza with stanza name
#    helper.get_input_stanza(stanza_name)
    # get all stanza names
#    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
#    loglevel = helper.get_log_level()
    # get proxy setting configuration
#    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
#    account = helper.get_user_credential_by_username("username")
#    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_account = helper.get_arg('organization')
    global_organization_id = global_account['username']
    global_api_key= global_account['password']
    #global_api_key = helper.get_global_setting("api_key")
    #global_endpoint_url = helper.get_global_setting("endpoint_url")
    #global_organization_id = helper.get_global_setting("organization_id")
    my_host = get_host(global_api_key,global_organization_id)
    my_network_list = get_devices(global_api_key,global_organization_id)
    all_data = get_data(global_api_key,global_organization_id,my_network_list)
    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
#    helper.log("log message")
    # write to the log using specified log level
#    helper.log_debug("log message")
#    helper.log_info("log message")
#    helper.log_warning("log message")
#    helper.log_error("log message")
#    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
#    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    #response = helper.send_http_request(url, method, parameters=None, payload=None,
    #                                    headers=None, cookies=None, verify=True, cert=None,
    #                                    timeout=None, use_proxy=True)
    # get the response headers
#    r_headers = response.headers
    # get the response body as text
#    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
#    r_json = response.json()
    # get response cookies
#    r_cookies = response.cookies
    # get redirect history
#    historical_responses = response.history
    # get response status code
#    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
#    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
#    helper.save_check_point(key, state)
    # delete checkpoint
#    helper.delete_check_point(key)
    # get checkpoint
#    state = helper.get_check_point(key)

    # To create a splunk event
#    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)

    
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    #import random
    #data = str(random.randint(0,100))
    #event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    event = helper.new_event(json.dumps(all_data), time=None, host=my_host, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    ew.write_event(event)


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