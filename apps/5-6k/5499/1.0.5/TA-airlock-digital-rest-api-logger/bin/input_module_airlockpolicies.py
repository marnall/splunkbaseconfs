
# encoding = utf-8

import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_airlock_server_fqdn = helper.get_global_setting('airlock_server_fqdn')
    opt_airlock_rest_api_port = helper.get_global_setting('airlock_rest_api_port')
    opt_airlock_rest_api_key = helper.get_global_setting('airlock_rest_api_key')
    opt_verify_remote_tls_certificate = helper.get_global_setting('verify_remote_tls_certificate')    
    helper.get_input_stanza()
    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    #loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    #account = helper.get_user_credential_by_username("username")
    #account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    #global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

    #helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request("https://"+ opt_airlock_server_fqdn +":"+opt_airlock_rest_api_port+"/v1/group", method="POST", parameters=None, headers={"X-ApiKey":opt_airlock_rest_api_key}, cookies=None, verify=bool(opt_verify_remote_tls_certificate), cert=None,timeout=None, use_proxy=True)

    r_json = response.json()

    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()


    for i in r_json['response']['groups']:
        groupid=i['groupid']
        response = helper.send_http_request("https://"+ opt_airlock_server_fqdn +":"+opt_airlock_rest_api_port+"/v1/group/policies", method="POST", parameters=None, payload={"groupid":groupid},headers={"X-ApiKey":opt_airlock_rest_api_key}, cookies=None, verify=bool(opt_verify_remote_tls_certificate), cert=None,timeout=None, use_proxy=True)
        
        policy = response.json()
        event = helper.new_event(source="Airlock_REST_policies", index=helper.get_output_index(), sourcetype="_json", data=json.dumps(policy),unbroken=True,time=time.time())
        ew.write_event(event)