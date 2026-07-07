
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests

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
    # securitycentral_webhook_url = definition.parameters.get('securitycentral_webhook_url', None)
    # securitycentral_security_token = definition.parameters.get('securitycentral_security_token', None)
    pass

def collect_events(helper, ew):
    helper.log_info("started  collecting events from security central")
    
    INDEX = helper.get_output_index()
    try:
        index = helper.service.indexes[INDEX]
        helper.log_info("using"+ str(index))

    except KeyError as e:
        helper.log_error("Index {} does not exist! Please create it as a new index. Exiting.".format(INDEX))
        return
    else:
        if index is None:
            helper.log_error("Index {} does not exist! Please create it as a new index. Exiting.".format(INDEX))
            return
    
    opt_security_central_splunk_token = helper.get_arg('securitycentral_security_token')
    SPLUNK_ENDPOINT = helper.get_arg('securitycentral_webhook_url')
    
    if opt_security_central_splunk_token is None or len(opt_security_central_splunk_token) == 0:
        helper.log_error("Token Missing")
        return
    
    headers= {"X-Bm-Splunk-Token" : opt_security_central_splunk_token}

    response = requests.get(SPLUNK_ENDPOINT, headers=headers)
                                        
    if response.status_code != 200:
        helper.log_error("Status Code: " + str(response.status_code))
        helper.log_error("Error Response: " + response.text)
        return
    
    response_json = response.json()
    
    status = response_json.get("message", None)
    
    if status is None or status != "SUCCESS":
        helper.log_error("Status: Failed")
        return
    
    data = response_json.get("data", None)
    
    if data is None or len(data) == 0:
        helper.log_info("No data received")
        return
    helper.log_info("Received {0} issues".format(str(len(data))))
    acked_items = []
    
    for item in data:
        id = item.get("id", None)
        metaData = item.get("metaData", None)
        metaData = json.dumps(metaData)
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=metaData)
        helper.log_info(event)
        try:
            ew.write_event(event)
        except Exception as e:
            helper.log_error(e)
        else:
            if id is None or len(id) == 0:
                continue
            acked_items.append(str(id))
    
    if len(acked_items) != 0:
        data = {"ackedTasks": acked_items}
        acked_response = requests.post(SPLUNK_ENDPOINT, headers=headers, data=json.dumps(data))
        
        if acked_response.status_code == 200:
            helper.log_info("Successfully acked {0} issues".format(str(len(acked_items))))
        else:
            helper.log_error("Failed to ack")
            helper.log_error(acked_response.text)
