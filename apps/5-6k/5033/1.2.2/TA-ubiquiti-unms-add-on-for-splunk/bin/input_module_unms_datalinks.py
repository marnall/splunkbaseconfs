import os
import sys
import time
import datetime
import json
import requests

def validate_input(helper, definition):
    unms_devices = definition.parameters.get('unms_datalinks', None)
pass

def collect_events(helper, ew):
    token = helper.get_global_setting("api_token")
    unms_ip = helper.get_global_setting("unms_ip")
    unms_st = helper.get_arg("unms_datalinks")
    url = 'http://' + unms_ip + '/nms/api/v2.1/data-links?siteLinksOnly=false'
    headers = {}
    headers["x-auth-token"] = "%s" % token
    response = requests.get(url, headers=headers, verify=False)
    resp_text=response.text
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=unms_st, data=resp_text, done=True, unbroken=False)
    ew.write_event(event)