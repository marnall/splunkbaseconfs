
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
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
   

    opt_api_key = helper.get_arg('api_key')

    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()

    # The following examples send rest requests to some endpoint.
    url = 'https://api.nsone.net/v1/stats/qps'
    page_number = 1
    headers = {
    'X-NSONE-Key': opt_api_key,
    'accept': "application/json"
    }
    response = helper.send_http_request(url, 'GET', parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    r_json = response.json()
    
    r_status = response.status_code
    if r_status !=200:
        response.raise_for_status()

    event = helper.new_event(json.dumps(r_json), time=None, host="NS1", index=None, source=None, sourcetype=None, done=True, unbroken=True)
    ew.write_event(event)
