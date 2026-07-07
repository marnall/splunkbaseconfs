
# encoding = utf-8

import os
import sys
import time
import datetime
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
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # series_id = definition.parameters.get('series_id', None)
    # seed_date = definition.parameters.get('seed_date', None)
    # reset_checkpoint = definition.parameters.get('reset_checkpoint', None)
    
    
    
    
    
    pass

def collect_events(helper, ew):
    
    
    
    def prep_fred_data(start_date, series_id, result):
        all_records = []
        for rc in result['observations']:
            if rc['date'] > start_date:
                fred_series_data = {
                    "Date": rc['date'],
                    "SeriesID": series_id,
                    "Value": rc['value']
                }
                all_records.append(fred_series_data)

        if all_records:
            return all_records
        else:
            return 0


    # Get settings
    fred_api_key = helper.get_global_setting("fred_api_key")
    series_id = helper.get_arg('series_id')
    
    # Get input/event metadata
    evt_source = helper.get_input_type()
    evt_sourcetype = helper.get_sourcetype(input_stanza_name=None)
    evt_index = helper.get_output_index(input_stanza_name=None)
    evt_host = "FRED"

    # logging
    log_level = helper.get_log_level()

    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # get last checkpoint and use default if not exist
    chkpoint_name = series_id + '_ck_dt'
    last_checkpoint = helper.get_check_point(chkpoint_name)
    if not last_checkpoint:
        start_date = helper.get_arg('seed_date')
    else:
        start_date = last_checkpoint

    dt_today = datetime.date.today()
    end_date = dt_today.strftime('%Y-%m-%d')
    

    url = "https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json&observation_start=%s&observation_end=%s" % (
        series_id, fred_api_key, start_date, end_date)
    
    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, 'GET', parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    
    r_json = response.json()
    
    # get response status code
    r_status = response.status_code
    
    
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    if r_status > 200:
        helper.log_info("HTTP Error: {} for URL: {}".format(r_status,url))
    
    else:
        fred_series_data = prep_fred_data(start_date,series_id,r_json)

        if fred_series_data:
            for rc in fred_series_data:
                event_time = int(time.mktime(time.strptime(str(rc['Date']), "%Y-%m-%d")))
        
                # To create a splunk event
                evt_json = json.dumps(rc)
                event = helper.new_event(evt_json, time=event_time, host=evt_host, index=evt_index, source=evt_source,
                                         sourcetype=evt_sourcetype, done=True,
                                         unbroken=True)
                ew.write_event(event)
        
            helper.save_check_point(chkpoint_name, str(rc['Date']))
    
