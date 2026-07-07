
# encoding = utf-8

import os
import sys
import time
import datetime
import re
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
    pass

def collect_events(helper, ew):
    helper.log_info("collect_events: " + time.strftime("%d-%m-%Y %H:%M:%S"))

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_uri = helper.get_arg('octopus_uri')
    opt_verify_ssl = helper.get_arg('octopus_verify_ssl')
    opt_endpoint = helper.get_arg('octopus_api_endpoint')
    opt_checkpoint = helper.get_arg('octopus_use_checkpoint')
    
    # Get global variable configuration
    global global_api_key
    global_api_key = helper.get_global_setting("api_key")
    
    octopus_url = "%s/api/%s" % (opt_uri, opt_endpoint)
    helper.log_info("Full URI: " + octopus_url)
    
    checkpoint_key = str(opt_endpoint) + 'id'
    last_checkpoint_id = helper.get_check_point(checkpoint_key)
    if last_checkpoint_id is None:
        last_checkpoint_id = 0
    helper.log_info("last_checkpoint_id: " + str(last_checkpoint_id))
    data = []

    while True:   
        # Send REST requests to some endpoint.
        response = helper.send_http_request(
            url=octopus_url, 
            method='GET', 
            headers={
                "X-Octopus-ApiKey": global_api_key,
            }, 
            verify=opt_verify_ssl
        )
        # check the response status, if the status is not sucessful, raise requests.HTTPError
        response.raise_for_status()
                                            
        # get response body as json. If the body text is not a json string, raise a ValueError
        r_json = response.json()
        
        # Get item ID from first item returned by the API which is the most recent item
        if opt_checkpoint is True:
            try:
                if r_json['Links']['Page.Current'].split('=')[1][:1] == '0':
                    checkpoint_id = r_json['Items'][0]['Id'].split('-')[1]
                    helper.save_check_point(checkpoint_key, checkpoint_id)
                    helper.log_info("checkpoint_id: " + str(checkpoint_id))
            except Exception as exc:
                helper.log_error("use_checkpoint: " + str(exc))
    
        # Iterate items and print results to Splunk if it hasn't been printed before
        for item in r_json['Items']:
            # Get item ID
            item_id = item['Id'].split('-')[1]
    
            if opt_checkpoint is True:
                if int(item_id) > int(last_checkpoint_id):
                    data.append(item)
            else:
                data.append(item)
        
        # Try to get next page if available, else exit
        try:
            octopus_url = opt_uri + re.sub(r'.*/api','/api',r_json['Links']['Page.Next'])
        except Exception as exc:
            helper.log_error("pagination error: " + str(exc))
            break

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)

    import json
    for d in data:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(d))
        ew.write_event(event)