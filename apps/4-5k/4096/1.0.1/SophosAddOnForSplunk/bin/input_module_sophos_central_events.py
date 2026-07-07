
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import jsonpath_rw
from datetime import datetime

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # server = definition.parameters.get('server', None)
    # port = definition.parameters.get('port', None)
    pass

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # server = definition.parameters.get('server', None)
    # port = definition.parameters.get('port', None)
    pass

def UtcNow():
    now = datetime.datetime.utcnow()
    return now


def collect_events(helper, ew):
   
    import datetime
    import time
    import json
    import jsonpath_rw
    
    method = 'GET'
    api_request = 'application/json' 
    
    global_api_access_url_ = helper.get_arg("api_gateway")
    global_x_api_key_ = helper.get_arg("x_api_key_")
    global_authorization_ = helper.get_arg("authorization_")
    expiration = helper.get_arg("expiration_date_")
    account_id = helper.get_arg("customer_name_or_account_id")
    
    input_source = helper.get_input_stanza_names()
    
    
    #get current time
    now = datetime.datetime.now()
    
    #get checkpoint value
    ckpt = "start_time"
    ckpt_value = helper.get_check_point(ckpt)

    #if there is no checkpoint value - that means its an initial load - set start time to now - 5 Minute
    if ckpt_value == None:

        old = int(time.mktime((now - datetime.timedelta(minutes=5)).timetuple()))
        #format the time
        # This is a timestamp in UTC-based ISO-8601 format (YYYY-MM-DDThh:mm:ssZ) 
        start_time = old
    #if it does exist then checkpoint value is start time
    else:
        start_time=ckpt_value

    end_time=int(time.time()) 

    
    path = "/siem/v1/events/?limit=1000&from_date=" + str(old)
    url = str(global_api_access_url_) + str(path)
    
    
    headers = {
           'x-api-key': global_x_api_key_,
           'Authorization': 'Basic %s' % global_authorization_
           }
           
    response = helper.send_http_request(url, 
                                        method, 
                                        parameters=None, 
                                        payload=None,
                                        headers=headers, 
                                        cookies=None, 
                                        verify=True, 
                                        cert=None,
                                        timeout=None, 
                                        use_proxy=True)
     
    r_status = response.status_code
    response.raise_for_status()
    helper.log_error (response.text) 
    
    r= response.json()
    
    input_type = helper.get_input_type()
    
    for index, value in enumerate(r["items"], start=0):
        r["items"][index][u"expiration_date"] = expiration
        r["items"][index][u"customer_name"] = account_id
    
        
    for stanza_name in helper.get_input_stanza_names():

        for one_dict in r["items"]:
            data = json.dumps(one_dict)
                    
            
            event = helper.new_event(source=input_source, index=helper.get_output_index(), data=data)
            helper.log_error (response.text) 
            
            try:
                ew.write_event(event)
                helper.log_error (response.text) 
            except Exception as e:
                raise e
        return
        
    #save checkpoint value to end_time which is data collection time
    ckpt_value = helper.save_check_point(ckpt, end_time)