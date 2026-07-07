
# encoding = utf-8

import requests
import json
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
    # api_key = definition.parameters.get('api_key', None)
    # zone = definition.parameters.get('zone', None)
    pass

def collect_events(helper, ew):
    import input_module_utils as ut

    # get user args
    opt_electricity_maps_account = helper.get_arg("electricity_maps_account")
    opt_alternative_base_url = opt_electricity_maps_account.get("username")  # Electricity Maps Product Base URL is used as username
    opt_zones = helper.get_arg("zone_s_")

    zones = opt_zones.split(",")
    
    url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
    
    if (opt_alternative_base_url and len(opt_alternative_base_url) != 0):
        opt_alternative_base_url = ut.validate_electricity_maps_base_url(opt_alternative_base_url, helper)
        url = opt_alternative_base_url + "/carbon-intensity/latest"

    headers = {
        "X-BLOBR-KEY": opt_electricity_maps_account.get("password")  # Electricity Maps API Key is used as password
    }

    for zone in zones:
        params = {"zone" : zone.strip()}
        data = ut.make_api_call(url=url, params=params, headers=headers, continue_after_failure=True, helper=helper)
        if (data is None):
            helper.log_debug(f"API Call to {url} made but 'None' received.")
            continue

        if(ut.electricity_maps_response_is_valid(data, helper)):
            timestamp = ut.em_convert_event_timestamp_to_total_seconds(data["datetime"], helper)
            ut.write_event_to_splunk(ew, json.dumps(data), timestamp, helper)