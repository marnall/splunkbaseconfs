# encoding = utf-8

import os
import sys
import time
import datetime
from base64 import b64encode
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
    # ip = definition.parameters.get('ip', None)
    # password = definition.parameters.get('password', None)
    pass


def get_next_events(helper, opt_ip, opt_password):
    key = "cynerio_marker"
    user_and_pass = f"splunk_user:{opt_password}"
    user_and_pass = b64encode(user_and_pass.encode()).decode("ascii")
    headers = {'Authorization': 'Basic %s' % user_and_pass,
               'Content-type': 'application/json'}
    state = helper.get_check_point(key) or 0
    url = f"https://{opt_ip}/api/v1/external/alerts?marker={state}"
    response = helper.send_http_request(url, "POST", parameters=None, payload=None, headers=headers, cookies=None,
                                        verify=False, cert=None, timeout=None)
    response.raise_for_status()
    r_json = response.json()
    marker = r_json["marker"]
    helper.save_check_point(key, marker)
    return r_json["items"]


def collect_events(helper, ew):
    opt_ip = helper.get_arg('ip')
    opt_password = helper.get_arg('password')
    l = 1
    events = get_next_events(helper, opt_ip, opt_password)
    while True:
        for event in events:
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(), data=json.dumps(event))
            ew.write_event(event)
        l += 1
        if l > 10:
            break
        events = get_next_events(helper, opt_ip, opt_password)
        if not events:
            break

