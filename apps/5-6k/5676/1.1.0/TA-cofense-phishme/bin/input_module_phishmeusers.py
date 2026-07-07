# encoding = utf-8

import os
import sys
import time
import datetime
import json
import csv

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_phishme_login_domain = helper.get_global_setting('phishme_login_domain')
    opt_phishme_api_token = helper.get_global_setting('phishme_api_token')
    #opt_verify_remote_tls_certificate = helper.get_global_setting('verify_remote_tls_certificate')    
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
    jsonArray = []
    # The following examples send rest requests to some endpoint.
    
    response = helper.send_http_request("https://" + opt_phishme_login_domain +"/users.csv", method="GET", parameters=None, headers={'Authorization': 'Token token=' + opt_phishme_api_token}, cookies=None, verify=True, cert=None,timeout=None, use_proxy=True)
    decoded = response.content.decode('utf-8')
    helper.log_debug(decoded)
    reader = csv.DictReader(decoded.splitlines(), delimiter=',')
    
    for row in reader:
        jsonArray.append(row)
    
    #Convert to JSON
    jsondata = json.dumps(jsonArray)

    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()


    event = helper.new_event(source="Phish_Me_Users", index=helper.get_output_index(), sourcetype="_json", data=jsondata,unbroken=False,time=time.time())
    ew.write_event(event)