
# encoding = utf-8

import os
import sys
import time
import datetime
import json
from datetime import datetime
import random
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
    # start_date = definition.parameters.get('start_date', None)
    pass

def collect_events(helper, ew):
    
    opt_start_date = helper.get_arg('start_date')
    global_server_ip = helper.get_global_setting("server_ip")
    global_server_port = helper.get_global_setting("server_port")
    global_access_token = helper.get_global_setting("access_token")
    global_protocol = helper.get_global_setting("protocol")
    
    stanza_name = helper.get_input_stanza_names()
    date_checkpoint = helper.get_check_point(f"{stanza_name}:start_date")
    
    if global_protocol == True:
        protocol='https'
    else:
        protocol='http'
    
    if date_checkpoint ==None:
        
        if opt_start_date == '':
            opt_start_date= datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            helper.save_check_point("start_date", opt_start_date)
            
    else:
        opt_start_date = date_checkpoint
        
    url = f"{protocol}://{global_server_ip}:{global_server_port}/api/transaction/list"
        
    params={
            'startDate':str(opt_start_date),
            'endDate':str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            'pageNo':1,
            'pageSize':200,
            'access_token': global_access_token
        }
    
    response = helper.send_http_request(url, 'GET', parameters=params, payload=None,
                                    headers=None, cookies=None, verify=True, cert=None,
                                    timeout=None, use_proxy=True)
    
    r_status = response.status_code
    
    if r_status != 200:
        helper.log_error("api call responded with {r_status} error message")
    
    r_json = response.json()['data']
    
    
    if len(r_json)>0:
        
        temp_time = ''
        results = []
        
        stanza_name = helper.get_input_stanza_names()
        
        for event in r_json:
            
            temp_time = r_json[r_json.index(event)]["eventTime"]
            event_id = r_json[r_json.index(event)]["id"]
            
            key = f"{stanza_name}:{event_id}"
            
            state = helper.get_check_point(key)
            
            event.pop("pin")
            event.pop("cardNo")
            
            if r_json[r_json.index(event)]["accZone"] == None:
                event.pop("accZone")
            
            if state is None:
                
                results.append(event)
                helper.save_check_point(key,"Indexed")
                
        helper.save_check_point(f"{stanza_name}:start_date",temp_time)
        
        data=json.dumps(results)
    
    
        event = helper.new_event(data, time=None, host=None, index=None, source=stanza_name, sourcetype=None, done=True, unbroken=True )
        ew.write_event(event)
        helper.log_info(f"number of events ingested: {len(results)}")
    else:
        helper.log_info("no new events ingested")
 