
# encoding = utf-8

import os
import sys
import time
import datetime

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
    # placeholder = definition.parameters.get('placeholder', None)
    pass

def collect_events(helper, ew):
    import input_module_utils as ut
    import json

    url = "https://api.carbonintensity.org.uk/regional"
    response = ut.make_api_call(url=url, params=None, headers=None, continue_after_failure=False, helper=helper)

    data = response.get("data")
    if not data:
        return
    data = data.pop()

    regions_list = data["regions"]
    from_data = data["from"]
    to_data = data["to"]

    for region in regions_list:
        region["from"] = from_data
        region["to"] = to_data
        timestamp = ut.ng_convert_event_timestamp_to_total_seconds(region["from"], helper)
        ut.write_event_to_splunk(ew, json.dumps(region), timestamp, helper)