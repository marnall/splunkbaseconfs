
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
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
    instance_url = definition.parameters.get('instance_url', None).strip()
    if not instance_url or not instance_url.startswith("http"):
        raise ValueError("Please enter a valid url starting with http:// or https://")

def collect_events(helper, ew):
    opt_instance_url = helper.get_arg('instance_url')
    opt_api_key = helper.get_arg('api_key')

    state = helper.get_check_point("created_at")

    # The following examples send rest requests to some endpoint.
    url = opt_instance_url.strip().rstrip('/')+"/api/v3/auditlog/?ordering=created_at&start="+(state or "")
    auth_token = base64.b64encode(opt_api_key.encode("utf-8")).decode("ascii")
    while url:
        response = helper.send_http_request(url, "GET", headers={"Authorization": "bearer "+auth_token}, verify=True,use_proxy=True)
        response.raise_for_status()
        r_json = response.json()
    
        # The following examples show usage of check pointing related helper functions.
        # save checkpoint
        helper.save_check_point("created_at", r_json["results"][-1]["created_at"])
    
        # To create a splunk event
        for result in r_json["results"]:
            #tz = datetime.datetime.strptime(result["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
            tz= result["created_at"]
            data = json.dumps(result)
            evt = helper.new_event(data, time=tz,source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
            ew.write_event(evt)
        
        url = r_json["next"]
