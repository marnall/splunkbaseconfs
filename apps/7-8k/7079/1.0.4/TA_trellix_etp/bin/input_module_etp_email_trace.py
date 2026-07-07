
# encoding = utf-8

import os
import sys
import time
import datetime
import json 
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

CHECKPOINT_KEY = "last_modified_datetime"
MAX_SIZE = 300

IN_FILTER = ('in', 'not in')
STATUS_LIST = ("accepted", "deleted", "delivered", "delivered (retroactive)", "dropped", "dropped oob", "dropped (oob retroactive)", "permanent failure", "processing", "quarantined", "rejected", "temporary failure")

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # etp_service_region = definition.parameters.get('etp_service_region', None)
    
    last_modified_datetime = definition.parameters.get('last_modified_datetime', None)
    if last_modified_datetime is not None:
        result = re.match("20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d.\d\d\d", last_modified_datetime)
        if result is None:
            raise ValueError('Format must be ISO format (yyyy-mm-ddTHH:MM:SS.fff)')
        else:
            pass
        try:
            res = datetime.datetime.fromisoformat(last_modified_datetime)
        except Exception as e:
            raise e


def _show_tmp(helper, ew, data):
    
    event = helper.new_event(
        data = json.dumps(data), 
        #time = data.get('attributes').get('acceptedDateTime'), 
        index = helper.get_output_index(), 
        sourcetype = helper.get_sourcetype()
    )
    ew.write_event(event)
    

def collect_events(helper, ew):
    
    start = time.perf_counter()
    interval = helper.get_arg('interval')
    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    """
    
    opt_has_attachment = helper.get_arg('has_attachment')
    opt_last_modified_datetime = helper.get_arg('last_modified_datetime')
    opt_from_email = helper.get_arg('from_email')
    opt_from_email_filter = helper.get_arg('from_email_filter')
    opt_status = helper.get_arg('status')
    opt_status_filter = helper.get_arg('status_filter')
    opt_time_lag_guard = helper.get_arg('time_lag_guard')
    
    # get input type
    input_type = helper.get_input_type()
    
    # get all detailed input stanzas
    all_input_stanza = helper.get_input_stanza()

    # get the loglevel from the setup page
    log_level = helper.get_log_level()
    
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

    # get proxy setting configuration
    # proxy_settings = helper.get_proxy()

    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    if opt_time_lag_guard:
        opt_time_lag_guard = int(opt_time_lag_guard)
    else:
        opt_time_lag_guard = 5      
     
    headers = {
        'Content-Type': 'application/json',
        'x-fireeye-api-key': global_api_key
    }

    url = f'https://{global_etp_service_region}/api/v1/messages/trace'
    method = 'POST'

    payload = {
        'size': MAX_SIZE,
        'attributes': {}
    }
    
    if opt_has_attachment is True:
        payload['attributes']['hasAttachment'] = {"value": True}
    
    if opt_from_email is not None and len(opt_from_email) > 0:
        if opt_from_email_filter not in IN_FILTER:
            opt_from_email_filter = 'in'
        
        from_email_list = [email.strip() for email in opt_from_email.split(';')]
        payload['attributes']['fromEmail'] = { 
            'value': from_email_list,
            'filter': opt_from_email_filter,
            'includes': ["SMTP", "HEADER"],
        }
    
    if '[]' in opt_status:
        opt_status.remove('[]')
        
    if len(opt_status) > 0:
        if opt_status_filter not in IN_FILTER:
            opt_status_filter = 'in'
        payload['attributes']['status'] = { 
            'value': opt_status,
            'filter': opt_status_filter
        }
    
    # helper.delete_check_point(CHECKPOINT_KEY)
    state = helper.get_check_point(CHECKPOINT_KEY)

    # first run time
    if state is None:
        if opt_last_modified_datetime: # option exists
            state = opt_last_modified_datetime
        else: # no option 
            state = datetime.datetime.now(datetime.timezone.utc)
            state = f'{state:%Y-%m-%dT%H:%M:%S.%f}'[:-3]

        helper.save_check_point(CHECKPOINT_KEY, state)
    
    #_show_tmp(helper, ew, payload)

    # current_time is the time before starting a loop
    # state_dt is fromLastModifiedOn
    current_time = datetime.datetime.now(datetime.timezone.utc)
    state_dt = datetime.datetime.fromisoformat(state.replace('Z', '')+'+00:00')
    if utils.check_within_timedelta(helper, current_time, state_dt, opt_time_lag_guard):
        helper.log_info({
              'message': 'Skipped this interval because of time_lag_guard', 
              'state': state 
            })
        return

    loop_flag = True
    while loop_flag:

        state.replace('Z', '')
        payload['attributes']['lastModifiedDateTime'] = {
            'value': state,
            'filter': '>'
        }
        
        response = helper.send_http_request(url, method, payload=payload,
                                          headers=headers, use_proxy=True, 
                                          verify=global_ssl_verify)
        
        # check the response status, if the status is not sucessful, raise requests.HTTPError
        response.raise_for_status()
        
        # get response body as json. If the body text is not a json string, raise a ValueError
        r_json = response.json()
        
        #_show_tmp(helper, ew, r_json.get('meta'))
        helper.log_info(r_json.get('meta'))
        
        total = r_json.get('meta').get('total')
        size = r_json.get('meta').get('size')
        if size == 0:
            break
        
        # state = r_json.get('meta').get('fromLastModifiedOn').get('end')

        sorted_data = sorted(r_json.get('data'), key=lambda x: x['attributes']['lastModifiedDateTime'])
        
        for data in sorted_data:
            datetime_str_gmt = f"{data.get('attributes').get('acceptedDateTime')}+00:00"
            _time_epoch = datetime.datetime.fromisoformat(datetime_str_gmt).timestamp()

            # check lastModifiedDateTime of every data and if not opt_time_lag_guard then break
            data_last_modified_datetime = datetime.datetime.fromisoformat(data.get('attributes').get('lastModifiedDateTime')+'+00:00')

            if utils.check_within_timedelta(helper, current_time, data_last_modified_datetime, opt_time_lag_guard):
              loop_flag = False
              helper.log_info({
                'message': 'Stopped importing email trace data in the middle of the process because of time_lag_guard.', 
                'data.attributes.lastModifiedDateTime': state 
              })
              break
            
            state = data.get('attributes').get('lastModifiedDateTime')
            event = helper.new_event(
                data = json.dumps(data, ensure_ascii=False), 
                time = _time_epoch, 
                index = helper.get_output_index(), 
                sourcetype = helper.get_sourcetype()
            )
            ew.write_event(event)
        
        if r_json.get('meta').get('total') <= r_json.get('meta').get('size'):
            helper.log_info({'message': 'No more data'})
            break
        
        # when next interval starts within 5 second, stop to fetch this time.
        if (time.perf_counter() - start + 5) > int(interval):
            helper.log_info({'message': 'Stop to fetch the email trace because it close to next interval time.'})
            break

    # save checkpoint
    helper.save_check_point(CHECKPOINT_KEY, state)
    
    end = time.perf_counter()
    time_diff = {
        'state': state,
        'start': start,
        'end': end,
        'diff': end - start,
        'interval': interval
    }
    #_show_tmp(helper, ew, time_diff)
    helper.log_info(time_diff)
