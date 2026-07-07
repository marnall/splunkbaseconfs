
# encoding = utf-8

import os
import sys
import time
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
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    import json, re
    import jsonpath_rw
    api_base_url = "https://api.newrelic.com/v2/"
    opt_api_key = helper.get_arg('api_key')
    headers = {'X-Api-Key': '{}'.format(opt_api_key)}
    parameters = ""
    api_url = helper.get_arg('api_url')
    opt_account = helper.get_arg('account')
    account_dict = {'account_id': '{}'.format(opt_account)}
    urls = api_url

    if opt_account:
        input_source = helper.get_input_stanza_names() + ":" + opt_account
    else:
        input_source = helper.get_input_stanza_names()

    for i in range(len(urls)):
        url = api_base_url + urls[i]
        if urls[i] == "alerts_events.json":
            break_point = "recent_events"
            source_type = "newrelic:alerts:events"
        elif urls[i] == "alerts_violations.json":
            break_point = "violations"
            source_type = "newrelic:alerts:violations"
        elif urls[i] == "browser_applications.json":
            break_point = "browser_applications"
            source_type = "newrelic:applications:browser"
        elif urls[i] == "mobile_applications.json":
            break_point = "applications"
            source_type = "newrelic:applications:mobile"
        elif urls[i] == "servers.json":
            break_point = "servers"
            source_type = "newrelic:servers"
        elif urls[i] == "key_transactions.json":
            break_point = "key_transactions"
            source_type = "newrelic:transactions"
        else:
            break_point = "applications"
            source_type = "newrelic:applications"
        
        
        j=0
        while j==0:
            response = helper.send_http_request(url, "GET", headers=headers,  parameters=parameters, payload=None, cookies=None, verify=True, cert=None, timeout=None, use_proxy=True)

            r_json = response.json()
            r_headers = str(response.headers)
            r_status = response.status_code

            try:
                response.raise_for_status()
                
            except:
                helper.log_error (response.text)
                
            if r_status == 200:
                helper.log_info ("Continue data collection process ")
            #capture next link for pagination
            m = re.search(".*Link.*(http[^>]+).+\srel=\"next\".*", r_headers)
            
            try:
                for one_dict in r_json.get(break_point):
                    one_dict.update(account_dict)
                    data = json.dumps(one_dict)
                    event = helper.new_event(source=input_source, index=helper.get_output_index(), sourcetype=source_type, data=data)
                    ew.write_event(event)
            except:
                helper.log_info("Caught noneType")
            if r_status == 200:
                helper.log_info("checking if more pages exist to collect data from")
            
            
            if m:
                url=m.group(1)
                helper.log_info("Collecting data from next page i.e, url={}".format(url)) 
                i=i+1
            else:
                if r_status == 200:
                    helper.log_warning ("No more data exist for sourcetype={}, end of data collection".format(source_type))
                break
            

    
    
    
  


  