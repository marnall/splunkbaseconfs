
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

    opt_electricity_maps_account = helper.get_arg("electricity_maps_account")
    opt_alternative_base_url = opt_electricity_maps_account.get("username") # Electricity Maps Product Base URL is used as username
    opt_zones = helper.get_arg("zone_s_")
    
    url = "https://api.electricitymap.org/v3/carbon-intensity/forecast"
    
    if (opt_alternative_base_url and len(opt_alternative_base_url) != 0):
        opt_alternative_base_url = ut.validate_electricity_maps_base_url(opt_alternative_base_url, helper)
        url = opt_alternative_base_url + "/carbon-intensity/forecast"
    
    zones = opt_zones.split(",")

    headers = {
        "X-BLOBR-KEY": opt_electricity_maps_account.get("password")  # Electricity Maps API Key is used as password
    }
    params = {}

    for zone in zones:
        params["zone"] = zone.strip()
        forecast = ut.make_api_call(url=url, params=params, headers=headers, continue_after_failure=True, helper=helper)
        if (forecast is None):
            helper.log_debug(f"API Call to {url} made but 'None' received.")
            continue

        if (ut.electricity_maps_response_is_valid(forecast, helper)):
            if forecast is None:
                helper.log_debug(f"API Call to {url} made but 'None' received.")
                continue
            ut.write_event_to_splunk(ew, json.dumps(forecast), None, helper)