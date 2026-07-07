
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

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # only_impacting_threats = definition.parameters.get('only_impacting_threats', None)
    pass

def tw_transform_threat_event(threat):
    # Cleanup unwanted fields
    threat.pop('tags')

def collect_events(helper, ew):
    
    # get user provided values
    opt_only_impacting_threats = helper.get_arg('only_impacting_threats')
    
    helper.log_debug("Started new run for Threat ingestion")
    helper.log_debug("User provided input for only impacting threats: %s" % opt_only_impacting_threats)
    
    """
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()

    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    """
    # get global variable configuration
    global_threatworx_instance = helper.get_global_setting("threatworx_instance")
    global_threatworx_handle = helper.get_global_setting("threatworx_handle")
    global_threatworx_api_key = helper.get_global_setting("threatworx_api_key")
    
    # Make API call to TW to get filtered Threat data
    url = "https://" + global_threatworx_instance + "/api/v1/threats/?"
    bearer_auth = "Bearer " + global_threatworx_api_key
    method = "POST"
    payload = { }
    filters_list = ['recent']
    if opt_only_impacting_threats == True:
        filters_list.append('impacting')
    payload['filters'] = filters_list
    payload['window_start'] = "30"
    payload['window_end'] = "0"
    # Note since we are using 'recent' filter we don't need to move/update offset progressively
    payload['offset'] = 0
    payload['limit'] = 100

    helper.log_debug("Threat API payload: %s" % payload)
    total_threats = 0    
    while True:
        response = helper.send_http_request(url, method, parameters=None, payload=payload,
                                        headers={"Content-Type": "application/json", "Authorization": bearer_auth}, cookies=None, verify=True, cert=None,
                                        timeout=300, use_proxy=True)
        helper.log_debug("Threat API response status code: %s" % response.status_code)
        if response.status_code != 200:
            helper.log_debug("API response text: %s" % response.text)
            # check the response status, if the status is not sucessful, raise requests.HTTPError
            response.raise_for_status()

        r_json = response.json()
        helper.log_debug("Number of Threats in API response: %s" % r_json["total"])

        threats = r_json["threats"]
        for threat in threats:
            tw_transform_threat_event(threat)
            # Always create a new event in Splunk
            event = helper.new_event(data=json.dumps(threat), time=None, host=None, index=helper.get_output_index(), source="ThreatWorx", sourcetype="threatworx:threat", done=True, unbroken=True)
            ew.write_event(event)
            
        total_threats = total_threats + r_json['total']
        if r_json["total"] != payload['limit']:
            helper.log_debug("Processed total [%s] Threats. Run completed." % total_threats)
            # last page processed, so break from the while loop
            break
        
