
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
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_airlock_server_fqdn = helper.get_global_setting('airlock_server_fqdn')
    opt_airlock_rest_api_port = helper.get_global_setting('airlock_rest_api_port')
    opt_airlock_rest_api_key = helper.get_global_setting('airlock_rest_api_key')
    opt_verify_remote_tls_certificate = helper.get_global_setting('verify_remote_tls_certificate')
    opt_delete_existing_checkpoint = helper.get_arg('delete_existing_checkpoint')
    
    if opt_delete_existing_checkpoint is True:
        helper.delete_check_point("svrcheckpoint")
        helper.log_debug("Existing checkpoint deleted, now exiting. Disable the Delete Existing Checkpoint option to index logs")
        exit()    
    # The following examples get options from setup page configuration.
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    #account = helper.get_user_credential_by_username("username")
    #account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    #global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")
    # get checkpoint
    svrcheckpoint = helper.get_check_point("svrcheckpoint")
    try:
        helper.log_debug("Checkpoint value in Splunk is:" + svrcheckpoint)
    except:
        helper.log_debug("Checkpoint appears to be empty")
    # The following examples send rest requests to some endpoint.
    if svrcheckpoint is None:
        helper.log_debug("No historical checkpoint found, obtaining restart checkpoint from Airlock") 

        response = helper.send_http_request("https://" + opt_airlock_server_fqdn +":"+opt_airlock_rest_api_port+"/v1/logging/svractivities", method="POST", parameters=None, payload=None,headers={"X-ApiKey":opt_airlock_rest_api_key}, cookies=None, verify=bool(opt_verify_remote_tls_certificate), cert=None,timeout=None, use_proxy=True)
        response.raise_for_status()
        r_json = response.json()        
        if not 'response' in r_json or len(r_json['response']['svractivities']) == 0: #If there are no results we don't need to write anything or do much
            helper.log_debug("Something went wrong sending the request to the Airlock Server, please check connectivity. Unable to get initial checkpoint.")
            exit() #Stop here because we can't continue
            
        else:
            r_json = response.json()
            helper.log_debug(r_json)
            svrcheckpoint = r_json['response']['svractivities'][-1]['checkpoint']
            #Write the events to the specified index
            event = helper.new_event(source="Airlock_REST_svractivities", sourcetype="_json", index="main", data=json.dumps(r_json['response']['svractivities']))
            #replace hardcoded index with index=helper.get_output_index()
            # save checkpoint
            helper.log_debug("Saving checkpoint to Splunk:" + svrcheckpoint)
            helper.save_check_point("svrcheckpoint", svrcheckpoint)

    else:
        helper.log_debug("Historical checkpoint found:" + svrcheckpoint)
        try:
            response = helper.send_http_request("https://" + opt_airlock_server_fqdn +":"+opt_airlock_rest_api_port+"/v1/logging/svractivities", method="POST", parameters=None, payload={"checkpoint":svrcheckpoint},headers={"X-ApiKey":opt_airlock_rest_api_key}, cookies=None, verify=bool(opt_verify_remote_tls_certificate), cert=None,timeout=None, use_proxy=True)
            response.raise_for_status()
            r_json = response.json()
        except:
            helper.log_info("Something went wrong sending the request to the Airlock Server, please check connectivity and that the supplied REST API key is valid. Please enable debug logging to see more information. If Access Forbidden is seen on debug level logging, the API key is invalid.")
            r_json = response.json()
            helper.log_debug(r_json)
            exit() #If the request is unable to be sent we should quit here
            
        if not 'response' in r_json or len(r_json['response']['svractivities']) == 0: #If there are no results we don't need to write anything or do much
            helper.log_debug("no results, nothing to do")
        else:    
            helper.log_debug("there are results to parse")
            helper.log_debug(r_json)
            #Write the events to the specified index
            for i in r_json['response']['svractivities']:
                event = helper.new_event(source="Airlock_REST_svractivities", sourcetype="_json", index=helper.get_output_index(), data=json.dumps(i))
                ew.write_event(event)

            #Set latest checkpoint
            svrcheckpoint = r_json['response']['svractivities'][-1]['checkpoint']
            # save checkpoint
            helper.log_info("Saving checkpoint to Splunk:" + svrcheckpoint)
            helper.save_check_point("svrcheckpoint", svrcheckpoint)



