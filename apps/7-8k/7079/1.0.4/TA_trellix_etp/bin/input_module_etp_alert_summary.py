
# encoding = utf-8

import os
import sys
import time
import json 
import datetime
import re

import utils

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

CHECK_POINT_KEY = "from_last_modified_on"
STATUS_LIST = ("quarantined", "released", "deleted", "bcc:dropped", "delivered (retroactive)", "dropped (oob retroactive)")

def _show_tmp(helper, ew, data):
    event = helper.new_event(
            data = json.dumps(data), 
            index = helper.get_output_index(), 
            sourcetype = helper.get_sourcetype()
        )
    ew.write_event(event)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # etp_service_region = definition.parameters.get('etp_service_region', None)
    # email_status = definition.parameters.get('email_status', None)
    from_last_modified_on = definition.parameters.get('from_last_modified_on', None)
    if from_last_modified_on is not None:
        result = re.match("20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d.\d\d\d", from_last_modified_on)
        if result is None:
            raise ValueError('Format must be ISO format (yyyy-mm-ddTHH:MM:SS.fff)')
        else:
            pass
        try:
            res = datetime.datetime.fromisoformat(from_last_modified_on)
        except Exception as e:
            raise e
        

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    """
    opt_email_status = helper.get_arg('email_status')
    opt_from_last_modified_on = helper.get_arg('from_last_modified_on')
    opt_time_lag_guard = helper.get_arg('time_lag_guard')

    helper.log_info( { 'opt_time_lag_guard': opt_time_lag_guard } )
    
    # get all detailed input stanzas
    input_all_stanza =  helper.get_input_stanza()
    
    # get global variable configuration
    global_api_key = helper.get_global_setting("api_key")
    global_etp_service_region = helper.get_global_setting("etp_service_region")
    global_ssl_verify = True if helper.get_global_setting("ssl_verify") == '1' else False

    # in Splunk cloud, it should be forced to set ssl verify true.
    try:
      server_info = utils.get_server_info(helper.service.token)
      if server_info.is_cloud_instance():
          global_ssl_verify = True
    except Exception as e: 
      helper.log_error(e)

    # get the loglevel from the setup page
    log_level = helper.get_log_level()
    
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)
    
    # delete checkpoint 
    # helper.delete_check_point(CHECK_POINT_KEY)

    # get checkpoint
    state = helper.get_check_point(CHECK_POINT_KEY)

    # first run time
    if state is None:
      if opt_from_last_modified_on is not None:
        state = opt_from_last_modified_on

      if opt_from_last_modified_on is None:
        state = datetime.datetime.now(datetime.timezone.utc)
        state = f'{state:%Y-%m-%dT%H:%M:%S.%f}'[:-3]

      helper.save_check_point(CHECK_POINT_KEY, state)
   
    if opt_time_lag_guard:
      opt_time_lag_guard = int(opt_time_lag_guard)
    else:
      opt_time_lag_guard = 5      

    headers = {
        'Content-Type': 'application/json',
        'x-fireeye-api-key': global_api_key
    }

    url = f'https://{global_etp_service_region}/api/v1/alerts'
    method = 'POST'

    payload = {
        'size': 100,
        'fromLastModifiedOn': state,
        #'attributes': {}
    }

    if '[]' in opt_email_status:
        opt_email_status.remove('[]')
    
    if len(opt_email_status) > 0:
        payload['attributes'] = {
            'email_status': opt_email_status
        }

    current_time = datetime.datetime.now(datetime.timezone.utc)
    state_dt = datetime.datetime.fromisoformat(state.replace('Z', '')+'+00:00')
    if utils.check_within_timedelta(helper, current_time, state_dt, opt_time_lag_guard):
        helper.log_info({
              'message': 'Skipped this interval because of time_lag_guard', 
              'state': state 
            })
        return 
        
    #_show_tmp(helper, ew, payload)
    response = helper.send_http_request(url, method, payload=payload,
                                        headers=headers, use_proxy=True, 
                                        verify=global_ssl_verify)
    
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()
    
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()

    total = r_json.get('meta').get('total')
    size = r_json.get('meta').get('size')
    
    helper.log_info(r_json.get('meta'))
    #_show_tmp(helper, ew, r_json.get('meta'))
    
    fromLastModifiedOn_end = r_json.get('meta').get('fromLastModifiedOn').get('end')
    if fromLastModifiedOn_end is None or size == 0:
        return

    sorted_data = sorted(r_json.get('data'), key=lambda x: x['attributes']['meta']['last_modified_on'])

    # To create a splunk event
    for data in sorted_data:
        datetime_str_gmt = f"{data.get('attributes').get('alert').get('timestamp')}+00:00"
        _time_epoch = datetime.datetime.fromisoformat(datetime_str_gmt).timestamp()
        
        # check lastModifiedDateTime of every data and if not opt_time_lag_guard then break
        data_last_modified_datetime = datetime.datetime.fromisoformat(data.get('attributes').get('meta').get('last_modified_on')+'+00:00')
        if utils.check_within_timedelta(helper, current_time, data_last_modified_datetime, opt_time_lag_guard):
            helper.log_info({
              'message': 'Stopped importing alert data in the middle of the process because of time_lag_guard.', 
              'data.attributes.meta.last_modified_on': state 
            })
            break

        state = data.get('attributes').get('meta').get('last_modified_on')
        event = helper.new_event(
            data = json.dumps(data, ensure_ascii=False), 
            time = _time_epoch, 
            index = helper.get_output_index(), 
            sourcetype = helper.get_sourcetype()
        )
        ew.write_event(event)
        
    helper.save_check_point(CHECK_POINT_KEY, state)
  
