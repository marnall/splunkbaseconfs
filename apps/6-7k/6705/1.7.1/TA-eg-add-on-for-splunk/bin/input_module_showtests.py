
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import re
import traceback
import base64

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # hostname_ip_address = definition.parameters.get('hostname_ip_address', None)
    # port = definition.parameters.get('port', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # component_type = definition.parameters.get('component_type', None)
    # category = definition.parameters.get('category', None)
    # test_type = definition.parameters.get('test_type', None)
    pass

def collect_events(helper, ew):
    global_account = helper.get_arg('global_account')
    username = global_account['username']
    password = global_account['password']
    password_base64 = base64.b64encode(bytes(f"{password}", "utf-8")).decode("ascii")
    opt_hostname_ip_address = helper.get_arg('hostname_ip_address')
    opt_port = helper.get_arg('port')
    # opt_username = helper.get_arg('username')
    # opt_password = helper.get_arg('password')
    opt_component_type = helper.get_arg('component_type')
    opt_category = helper.get_arg('category')
    opt_test_type = helper.get_arg('test_type')
    # --------------------------------------------------------------------------------------------------------
    source1 = helper.get_input_stanza_names()
    index1 = helper.get_output_index()
    sourcetype1 = helper.get_sourcetype()
    # --------------------------------------------------------------------------------------------------------
    url = "https://" + opt_hostname_ip_address + ":" + opt_port + "/api/eg/orchestration/showtests"
    method = "POST"
    managerurl = "https://" + opt_hostname_ip_address + ":" + opt_port
    header1 = {
        "managerurl":managerurl,
        "user":username,
        "pwd":password_base64
        }
    body1 = {
        "componenttype":opt_component_type,
        "category":opt_category,
        "testtype":opt_test_type
        }
    # --------------------------------------------------------------------------------------------------------
    try:
        response = helper.send_http_request(url, method, parameters=None, payload=body1,
                                            headers=header1, cookies=None, verify=False, cert=None,
                                            timeout=None, use_proxy=False)
        r_status = response.status_code
        if r_status != 200:
            response.raise_for_status()
        else:
            r_json = response.json()
            output = json.dumps(r_json)
            event = helper.new_event(host=opt_hostname_ip_address, source=source1, index=index1, sourcetype=sourcetype1, data=output)
            ew.write_event(event)
    except Exception as e:
        message1 = "Exception= " + "\"" + str(e) + "\""
        helper.log_debug(message1)
