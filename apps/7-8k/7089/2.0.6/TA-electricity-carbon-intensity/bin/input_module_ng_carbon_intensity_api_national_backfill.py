
# encoding = utf-8

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
    
    ut.validate_dates(start_date=start_date, end_date=end_date, day_threshold=30)

def collect_events(helper, ew):
    import input_module_utils as ut

    opt_start_date = helper.get_arg("start_date")
    opt_end_date = helper.get_arg("end_date")
    
    url = f"https://api.carbonintensity.org.uk/intensity/{opt_start_date}/{opt_end_date}"
    headers = {"Accept": "appliaction/json"}
    
    response = ut.make_api_call(url=url, params=None, headers=headers, continue_after_failure=False, helper=helper)
    data = response.get("data")
    if(data is None):
        helper.log_info(f"{url} called, but empty response received")
        return

    for period in data:
        ut.write_event_to_splunk(ew, json.dumps(period), None, helper)