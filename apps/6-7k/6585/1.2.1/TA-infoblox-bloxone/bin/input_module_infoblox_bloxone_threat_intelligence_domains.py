
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import base64
import requests

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
    # first_run_get_past_iocs = definition.parameters.get('first_run_get_past_iocs', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    interval = helper.get_arg('interval')
    first_run_get_past_iocs = helper.get_arg('first_run_get_past_iocs')

    helper.set_log_level("debug")
    helper.log_debug("Interval is " + str(interval))
    helper.get_input_type()
    loglevel = helper.get_log_level()
    proxy_settings = helper.get_proxy()

    global_apikey = helper.get_global_setting("apikey")
    
    helper.log_info("Start download for Infoblox Threatlist")
    
    url = "https://csp.infoblox.com/tide/api/data/threats/state/host?data_format=ndjson"

    # Get checkpoint is first run - if yes acquire everything, else only last hour.
    if helper.get_check_point('first-run-performed-FQDN') or not first_run_get_past_iocs:
        if interval:
            period = int(int(interval)/3600)
            url = url + "&period=" + str(period) + "%20hours"
        else:
            url = url +"&period=1%20hours"

    # Set checkpoint first-run-performed
    helper.save_check_point('first-run-performed-FQDN', True)

    method="GET"
    
    headers = {
       'Authorization':'Token %s' % global_apikey,
       'Content-Type':'application/json',
       'Cache-Control': 'no-cache'
        }

    if not proxy_settings:
        response = requests.get(url, headers=headers, cookies=None, verify=True, timeout=(600,600), stream=True)
    else:
        response = requests.get(url, headers=headers, cookies=None, verify=True, timeout=(600,600), proxies=proxy_settings, stream=True)

    if response.encoding is None:
        response.encoding = 'utf-8'

    for line in response.iter_lines(decode_unicode=True):
        if line:
            line = line.replace('"host":"','"hostname":"')
            try:
                r_json=json.loads(line)
            except:
                raise Exception("Unable to load into a json format")

            data = json.dumps(r_json)
            #data = data.replace('"host":"','"hostname":"')
            #data = data.replace("\"{","{")
            #data = data.replace("}\"","}")
            #data = data.replace("\\\"","\"")

            helper.log_info(data)

            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
            ew.write_event(event)

    helper.log_info("Infoblox TIDE download completed")