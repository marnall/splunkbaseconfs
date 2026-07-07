# encoding = utf-8

import os
import sys
import datetime
import time
import json

import requests

def validate_input(helper, definition):
    endpoint_type = definition.parameters.get('endpoint_type', None)
    log_type = definition.parameters.get('log_type', None)

def collect_events(helper, ew):
    opt_endpoint_type = helper.get_arg('endpoint_type')
    opt_log_type = helper.get_arg('log_type')
    
    opt_url = helper.get_global_setting('librenms_url')
    opt_token = helper.get_global_setting('api_token')
    
    headers = {
    'X-Auth-Token': opt_token,
    }

    if opt_endpoint_type != 'api/v0/logs':
        res = requests.get(opt_url + '/' + opt_endpoint_type, headers=headers)

        if res.status_code == 200:
            data = json.dumps(res.json())
    else:
        logTypes = []
        for s in range (len(opt_log_type)):
            
            res = requests.get(opt_url + '/' + opt_endpoint_type + '/' + opt_log_type[s], headers=headers)
            
            if res.status_code == 200:
                logTypes.append(res.json()["logs"])
        
        data = json.dumps(logTypes)

    try:
        event = helper.new_event(data, host=None, source=None, sourcetype='librenms', done=True, unbroken=True)
        ew.write_event(event)
    
    except Exception as e:
        raise e
