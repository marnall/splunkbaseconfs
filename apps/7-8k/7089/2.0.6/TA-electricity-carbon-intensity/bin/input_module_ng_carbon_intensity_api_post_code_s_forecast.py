
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

    time_now = datetime.datetime.now()
    time_now_string = time_now.strftime("%Y-%m-%dT%H:%MZ")
    
    opt_uk_postcodes = helper.get_arg("uk_post_code_s_")
    
    base_url = f"https://api.carbonintensity.org.uk/regional/intensity/{time_now_string}/fw48h"
    headers = {"Accept": "appliaction/json"}

    post_codes = opt_uk_postcodes.split(",")
    for code in post_codes:
        url = base_url + f"/postcode/{code.strip()}"

        response = ut.make_api_call(url=url, params=None, headers=headers, continue_after_failure=True, helper=helper)
        if (response is None):
            helper.log_debug(f"API Call to {url} made but 'None' received.")
            continue

        data = response.get("data")
        if(data is None):
            helper.log_debug(f"API Call to {url} made but 'None' received.")
            continue
        
        ut.write_event_to_splunk(ew, json.dumps(data), None, helper)