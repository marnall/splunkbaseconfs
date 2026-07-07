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

MINIMAL_INTERVAL = 30
MAXIMUM_INTERVAL = 300

MAXIMUM_BACKFILL = 90

def validate_input(helper, definition):
    # log response
    DEBUG(helper, 'validate_input')
    
    interval = int(definition.parameters.get('interval')) 
    if interval < MINIMAL_INTERVAL:
        raise ValueError("Interval must be at least {} seconds".format(MINIMAL_INTERVAL))
    if interval > MAXIMUM_INTERVAL:
        raise ValueError("Interval must be no greater than {} seconds".format(MAXIMUM_INTERVAL))
    
    days_to_backfill = int(definition.parameters.get('days_to_backfill'))
    if days_to_backfill > MAXIMUM_BACKFILL:
        raise ValueError("Days to backfill must be no greater than {} days".format(MAXIMUM_BACKFILL))
    
    get_start_time(days_to_backfill)

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    access_token = helper.get_global_setting('service_account_pat')
    asana_headers = {}
    asana_headers['Authorization'] = 'Bearer ' + access_token
    parameters = {}
    offset = get_offset(helper)
    start_at = get_start_at(helper)
    if (offset):
        parameters['offset']=offset
    elif (start_at):
        parameters['start_at']=start_at
    else:
        parameters['start_at']=get_start_time(helper.get_arg('days_to_backfill'))
    url = ("https://app.asana.com/api/1.1/workspaces/%s/audit_log_events" % (helper.get_global_setting('workspace_id')))
    response = helper.send_http_request(url, 
                                        method='GET', 
                                        parameters=parameters,
                                        payload=None,
                                        headers=asana_headers, 
                                        cookies=None, 
                                        verify=True, 
                                        cert=None,
                                        timeout=None, 
                                        use_proxy=True)

    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
                        
    # log response
    DEBUG(helper, r_json)

    # check status code
    if response.status_code != 200:
        error = r_json['errors'][0]
        error_message = error['message'].lower()
        if (
            'pagination token' in error_message and
            ('expired' in error_message or 'invalid' in error_message)
        ):
            INFO(helper, "Asana Offset token expired, trying again with start_at time. Error: %s" % (response._content))
            save_offset(helper, None)
            return
        else:
            response.raise_for_status()

        ERROR(helper, "%s %s" % (response.status_code, response._content))

    # parse response
    asana_events = r_json['data']
    next_page = r_json['next_page']
    
    input_name = helper.get_input_stanza_names()
    index=helper.get_output_index()
    source_type=helper.get_sourcetype()
    for asana_event in asana_events:
        data = json.dumps(asana_event)
        splunk_event = helper.new_event(
            source=input_name, 
            index=index, 
            sourcetype=source_type, 
            data=data,
        )
        ew.write_event(splunk_event)

    save_offset(helper, next_page['offset'])
    if (len(asana_events) > 0):
        save_start_at(helper, asana_events[-1]['created_at'])

def get_offset(helper):
    offset_key = _get_checkpoint_key(helper, 'offset')
    return helper.get_check_point(offset_key)

def save_offset(helper, new_offset):
    offset_key = _get_checkpoint_key(helper, 'offset')
    helper.save_check_point(key=offset_key, state=new_offset)

def get_start_at(helper):
    start_at_key = _get_checkpoint_key(helper, 'start_at')
    return helper.get_check_point(start_at_key)

def save_start_at(helper, new_start_at):
    start_at_key = _get_checkpoint_key(helper, 'start_at')
    helper.save_check_point(key=start_at_key, state=new_start_at)

def _get_checkpoint_key(helper, key):
    input_name = helper.get_input_stanza_names()
    checkpoint_key = "{}_{}".format(input_name, key)
    return checkpoint_key

def DEBUG(helper, msg):
    helper.log_debug(log_message(helper, msg))

def INFO(helper, msg):
    helper.log_info(log_message(helper, msg))

def ERROR(helper, msg):
    helper.log_error(log_message(helper, msg))

def log_message(helper, msg):
    input_name = helper.get_input_stanza_names()
    message = "%s %s" % (input_name, str(msg))
    return message

def get_start_time(days_to_backfill):
    if days_to_backfill:
        try:
            dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=int(days_to_backfill))
        except ValueError:
            raise ValueError("Incorrect days to backfill format. Should be integer.")
    else:
        dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=30)

    return datetime.datetime.strftime(dt, '%Y-%m-%dT%H:%M:%SZ')
