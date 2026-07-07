
# encoding = utf-8

import requests
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
    import input_module_utils as ut
    start_date = definition.parameters.get('start_date', None)
    end_date = definition.parameters.get('end_date', None)

    ut.validate_dates(start_date=start_date, end_date=end_date, day_threshold=14)

def collect_events(helper, ew):
    import input_module_utils as ut

    opt_uk_postcodes = helper.get_arg("uk_post_code_s_")
    opt_start_date = helper.get_arg("start_date")
    opt_end_date = helper.get_arg("end_date")
    
    base_url = f"https://api.carbonintensity.org.uk/regional/intensity/{opt_start_date}/{opt_end_date}"
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
        
        regionid = data["regionid"]
        shortname = data["shortname"]
        postcode = data["postcode"]
        
        for period in data["data"]:
            period["regionid"] = regionid
            period["shortname"] = shortname
            period["postcode"] = postcode
            ut.write_event_to_splunk(ew, json.dumps(period), None, helper)