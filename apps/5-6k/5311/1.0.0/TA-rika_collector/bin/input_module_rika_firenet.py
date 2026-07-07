
# encoding = utf-8

import os
import sys
import time
import datetime


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    # POST https://www.rika-firenet.com/web/login
    # email=&password=
    
    
    proxy_settings = helper.get_proxy()
    
    stove = helper.get_arg('stoveid')
    helper.log_info("Retrieveing info of: %s" % stove)
    
    payload ={}
    payload["email"] = helper.get_global_setting('email')
    payload["password"] = helper.get_global_setting('password')
    
    helper.log_info("Login to Firenet")
    response = helper.send_http_request("https://www.rika-firenet.com/web/login", "POST", parameters=None, payload=payload,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
                                        
    r_status = response.status_code
    r_cookies = response.cookies
    helper.log_info(r_status)
    response.raise_for_status()
    
    helper.log_info("Get Stove Status")
    response = helper.send_http_request("https://www.rika-firenet.com/api/client/%s/status" % stove, "GET", parameters=None, payload=None,
                                        headers=None, cookies=r_cookies, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    
    r_json = response.json()
    r_cookies = response.cookies
    r_text = response.text
    r_status = response.status_code
    response.raise_for_status()
    
    event = helper.new_event(r_text, time=None, host="Firenet", index=helper.get_output_index(), source="firenet", sourcetype="rika:firenet", done=True, unbroken=True)
    ew.write_event(event)
    
