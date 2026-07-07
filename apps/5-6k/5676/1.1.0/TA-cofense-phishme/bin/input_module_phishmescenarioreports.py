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
    opt_scenarios_to_collect = helper.get_arg('scenarios_to_collect')
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

    # The following examples send rest requests to some endpoint.
    
    response = helper.send_http_request("https://" + opt_phishme_login_domain + opt_scenarios_to_collect, method="GET", parameters=None, headers={'Authorization': 'Token token=' + opt_phishme_api_token}, cookies=None, verify=True, cert=None,timeout=600, use_proxy=True)

    
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()
    r_json = response.json()

    for identifier in r_json:
        
        touse = identifier['id']
        scenario_type = identifier['scenario_type']
        scenario_title = identifier['title']
        helper.log_debug(touse)
        jsonArray = []
        
        response = helper.send_http_request("https://" + opt_phishme_login_domain +"/scenario/"+touse+"/full_csv", method="GET", parameters=None, headers={'Authorization': 'Token token=' + opt_phishme_api_token}, cookies=None, verify=True, cert=None,timeout=600, use_proxy=True)
        
        decoded = response.content.decode('utf-8')
        reader = csv.DictReader(decoded.splitlines(), delimiter=',')


        
        for row in reader:
            jsonArray.append(row)
        
        rows = len(jsonArray)
        helper.log_debug("Number of recipients are " + str(rows))        
        #seconds to sleep being slightly cautious
        sleepingfor = (rows//900)
        
        for item in jsonArray:
            item['scenario_type'] = scenario_type
            item['scenario_title'] = scenario_title
            item['scenario_id'] = touse
        
        jsondata = json.dumps(jsonArray)
        

        event = helper.new_event(source="Phish_Me_Scenario_Reports", index=helper.get_output_index(), sourcetype="_json", data=jsondata,unbroken=False,time=time.time())
        ew.write_event(event)
            
        time.sleep(sleepingfor)
        
    
    
    
    