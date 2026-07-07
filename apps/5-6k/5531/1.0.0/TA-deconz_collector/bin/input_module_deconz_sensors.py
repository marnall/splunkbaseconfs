
# encoding = utf-8

import os
import sys
import time
import datetime
import json


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    
    proxy_settings = helper.get_proxy()
    
    
    
    key = helper.get_arg('api_key')
    host = helper.get_arg('deconz_url')
    
    helper.log_info("Retrieveing info of: %s" % host)
    
    response = helper.send_http_request("%s/api/%s/sensors" % (host, key), "GET", parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
                                        
    r_status = response.status_code
    helper.log_info(response.text)
    
    r_cookies = response.cookies
    r_json = response.json()
    helper.log_info(r_status)
    response.raise_for_status()
    
    #helper.log_info(str(r_json.keys()))
    for i in r_json.keys():
        #data = str(r_json[i]).replace('u', '').replace("'", '"')
        #helper.log_info(data)
        #helper.log_info(json.dumps(r_json[i]))
        event = helper.new_event(json.dumps(r_json[i]), time=None, host=host, index=helper.get_output_index(), source="deconz", sourcetype="deconz:sensors", done=True, unbroken=True)
        ew.write_event(event)
    
