# encoding = utf-8

import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # jumpcloud_api_key = definition.parameters.get('jumpcloud_api_key', None)
    # index_name = definition.parameters.get('index_name', None)
    pass


def collect_events(helper, ew):

    # user variables
    stanza = helper.get_input_stanza()
    opt_jumpcloud_api_key = helper.get_arg('jumpcloud_api_key')
    opt_index_name = helper.get_output_index()
    opt_interval_refresh = int(helper.get_arg("interval"))

    # log level, filter with search index=_internal "[JumpCloud]"
    helper.set_log_level(2)
    
    #helper.log_info("[JumpCloud] Interval set to %s" % opt_interval_refresh)

    
    # build the API call
    # source: https://docs.jumpcloud.com/api/insights/directory/1.0/index.html

    url = "https://api.jumpcloud.com/insights/directory/v1/events"
    
    method = "POST"
    
    headers = {
        "accept": "application/json",
        "x-api-key": opt_jumpcloud_api_key,
        "content-type": "application/json"
    }
    
    # determine start_time
    start_time = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0) - datetime.timedelta(seconds=opt_interval_refresh)
    start_time = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')


    helper.log_info("[JumpCloud] time mark: %s" % start_time)


    payload = {
        "start_time": start_time,
        "service": ["all"]
    }
    
    response = helper.send_http_request(
        url, 
        method=method, 
        parameters=None, 
        payload=payload,
        headers=headers, 
        cookies=None, 
        verify=True, 
        cert=None,
        timeout=None, 
        use_proxy=True
        )

    r_json = response.json()
    r_status = response.status_code
    
    # if there are any errors
    if(r_status == 200):
        
        helper.log_info("[JumpCloud] Proceeding with %s log events." % len(r_json))

        for splunk_event in r_json:

            # construct a splunk event
            parsed_event = helper.new_event(source="JumpCloud", index=opt_index_name, sourcetype="jumpcloud:json", data=json.dumps(splunk_event))
            #save event in the index
            ew.write_event(parsed_event)

    else:
        helper.log_error("[JumpCloud] Something went wrong. Response: %s" % r_status)

    helper.log_info("[JumpCloud] Finished")