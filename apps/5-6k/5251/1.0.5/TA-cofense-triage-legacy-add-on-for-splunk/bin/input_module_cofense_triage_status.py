
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
    # global_account = definition.parameters.get('global_account', None)
    # cofense_triage_url_host = definition.parameters.get('cofense_triage_url_host', None)
    pass

def collect_events(helper, ew):
    global_account = helper.get_arg('global_account')
    username = global_account['username']
    token = global_account['password']

    arg_endpoint = 'status'
    global_url_hosts = helper.get_arg('cofense_triage_url_host')
    
    source_type = helper.get_sourcetype()
    input_type = helper.get_input_type()

    api_url = global_url_hosts + '/api/public/v1/' + arg_endpoint
    api_headers = {'Authorization': 'Token token=' + username + ':' +
                                    token}
    if not helper.get_proxy():
            use_proxy = False
    else:
        use_proxy = True
    try:
        response = helper.send_http_request(api_url, 'GET', headers=api_headers, verify=False, use_proxy=use_proxy)
    except:
        helper.log_error("Unable to connect to "+api_url)
        exit(1)
    
    response_content = json.loads(response.content)

    
    event = helper.new_event(source=input_type, 
                            sourcetype=source_type,
                            host=global_url_hosts,
                            index=helper.get_output_index('main'),
                            data=json.dumps(response_content)
    )
    ew.write_event(event)
