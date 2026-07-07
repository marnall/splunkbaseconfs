# TO DO, implement HTTPS Cert disable / validation
# encoding = utf-8

import os
import sys
import time
from datetime import datetime as dt, timedelta
import requests
import json
import datetime


def validate_input(helper, definition):
    pass

def collect_events(helper, ew):


    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_clientid = helper.get_arg('clientid')
    opt_clientsecret = helper.get_arg('clientsecret')    
    opt_disable_https_cert_validation = helper.get_arg('disable_https_cert_validation')
    opt_activity_types_to_collect = helper.get_arg('activity_types_to_collect')
    opt_qualtrics_server_selection = helper.get_arg('qualtrics_server_selection')
    opt_qualtrics_domain_selection = helper.get_arg('qualtrics_domain_selection')
    opt_delete_existing_checkpoints = helper.get_arg('delete_existing_checkpoints')    
    opt_oauth_2_0_scope = helper.get_arg('oauth_2_0_scope')
    
    #build custom parameters
    opt_base_url = ('https://' + opt_qualtrics_server_selection + opt_qualtrics_domain_selection + '/oauth2/token')
    opt_logs = ('https://' + opt_qualtrics_server_selection + opt_qualtrics_domain_selection + '/API/v3/logs')
    data={'grant_type': 'client_credentials','scope': opt_oauth_2_0_scope}
    loglevel = helper.get_log_level()
    helper.set_log_level("debug") 

    helper.get_input_type()

    helper.get_input_stanza()

    proxy_settings = helper.get_proxy()
    
    helper.log_debug("Proxy Settings Are" + str(proxy_settings))
   
    try:
        if proxy_settings['proxy_password'] != "":
            helper.log_debug("Proxy has a password specified, using auth")
            proxies = {"https" : "https://" + proxy_settings['proxy_username'] + ":" + proxy_settings['proxy_password'] + "@" + proxy_settings['proxy_url'] + ":" + proxy_settings['proxy_port']}
        elif proxy_settings['proxy_url']:
            helper.log_debug("Proxy has no password specified, using proxy without auth")
            proxies = {"https" : "https://" + proxy_settings['proxy_url'] + ":" + proxy_settings['proxy_port']}
    except:
        helper.log_debug("No proxy specified,attempting to go direct")
        proxies = 0
        
    
    helper.log_debug("Obtaining access token from Qualtrics")
    
    if proxies == 0:
        response = requests.post(opt_base_url, auth=(opt_clientid,opt_clientsecret), data=data,verify=opt_disable_https_cert_validation)        
    else:
        response = requests.post(opt_base_url, auth=(opt_clientid,opt_clientsecret), data=data,proxies=proxies,verify=opt_disable_https_cert_validation)


    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

    r_json = response.json()

    
    access_token = r_json['access_token']

    helper.log_debug("Access token is:" + access_token)

    if opt_delete_existing_checkpoints == True:
        for i in opt_activity_types_to_collect:
            helper.delete_check_point(i)
            helper.log_debug("Deleting checkpoint " + i)
        helper.log_debug("Quitting Application and Not Indexing, please deselect 'Delete Existing Checkpoints' to start again")    
        quit()
            
 
    for i in opt_activity_types_to_collect:
        
        activitytypecheckpoint = helper.get_check_point(i)
        
        if activitytypecheckpoint == None:
            helper.log_debug("There is no existing token for the activity type: " + i)   
            response = helper.send_http_request(opt_logs, method="GET", parameters={"activityType":i,"pageSize":"20"}, payload=None,headers={"authorization": "bearer "+ access_token}, cookies=None, verify=opt_disable_https_cert_validation, cert=None,timeout=None, use_proxy=True)    
            r_json = response.json()
            helper.log_debug(r_json)
        else:
            helper.log_debug("There is an existing token for the activity type: " + i)
            response = helper.send_http_request(opt_logs, method="GET", parameters={"activityType":i,"pageSize":"20","startDate":activitytypecheckpoint}, payload=None,headers={"authorization": "bearer "+ access_token}, cookies=None, verify=opt_disable_https_cert_validation, cert=None,timeout=None, use_proxy=True)    
            r_json = response.json()
            helper.log_debug(r_json)
        
        try:
            r_json['result']['elements']
            for z in r_json['result']['elements']:
                event = helper.new_event(source=i, index=helper.get_output_index(), sourcetype="_json", data=json.dumps(z),unbroken=True,time=time.time())
                ew.write_event(event)
        
            try:   
                r_json['result']['nextPage']
                while r_json['result']['nextPage'] != None:
                    nextPage = r_json['result']['nextPage']
                    response = helper.send_http_request(opt_logs, method="GET", parameters={"activityType":i,"pageSize":"1000","skipToken":nextPage}, payload=None,headers={"authorization": "bearer "+ access_token}, cookies=None, verify=opt_disable_https_cert_validation, cert=None,timeout=None, use_proxy=True)
                    r_json = response.json()
                    helper.log_debug(r_json)
                    for z in r_json['result']['elements']:
                        event = helper.new_event(source=i, index=helper.get_output_index(), sourcetype="_json", data=json.dumps(z),unbroken=True,time=time.time())
                        ew.write_event(event)
                
            except:
                helper.log_debug("An error has occured pulling data from " + i + " activitytype, the response was:")
                helper.log_debug(r_json)
            try:   
                timestamp = r_json['result']['elements'][-1]['timestamp']
                helper.log_debug("Start date to set for " + i + " activity type is: " + timestamp)
            
                #We need to increment the checkpoint slightly or it will keep getting the last event. This is a bit messy
                date_time_obj = dt.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
                date_time_obj = date_time_obj + timedelta(milliseconds=500)
                date_obj = date_time_obj.date()
                time_obj = date_time_obj.time()
                timestamp = (str(date_obj) + "T" + str(time_obj) + "Z")
                helper.save_check_point(i, timestamp)
                state = helper.get_check_point(i)
                helper.log_debug("Checkpoint set is " + state)    
            
            except:
                helper.log_debug("There was no timestamp returned for " + i + " activity type")
        
        except:
            helper.log_debug("There were no elements returned for " + i + " activity type")
