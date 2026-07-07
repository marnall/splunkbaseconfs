
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
from requests import Request

import random
from datetime import datetime

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
    # data_type = definition.parameters.get('data_type', None)
    pass


# create post request from nucleon activeTreats api
def request(global_username,global_password,global_usrn,global_client_id,reset,limit,helper):
    """
    API Request Details
    """
    body={'usrn':global_usrn,'clientID':global_client_id,'reset':reset,'limit':limit}
    req = Request("POST", 'http://api.nucleoncyber.com/feed/ActiveThreats', auth=(global_username,global_password), data=body)
    prepped_req = requests.session().prepare_request(req)
    response = requests.session().send(prepped_req)
    if response.status_code != 200:
        helper.log_error("Error While fetching Assets Information : "+response.text) 
        exit()
    

    return response.text

# send event to splunk    
def write_event_splunk(active_threat_event,ew,helper):
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=active_threat_event)
    ew.write_event(event)
    

# create event 
def modify_array(active_threat_array,active_threat_summary,timeStamp,ew,helper):
    """
    add to event the API call summary and timestamp
    """
    helper.log_info(" in func:Modifying Array")
    for event in active_threat_array:
        event["localCountry"] = active_threat_summary.get("localCountry")
        event["localRegion"] = active_threat_summary.get("localRegion")
        event["timeStamp"] = timeStamp
        write_event_splunk(json.dumps(event),ew,helper)
    helper.log_info("succesfuly enter data to index: "+helper.get_output_index())
        

# main func-cal api ,create events and save it in splunk  
def collect_events(helper, ew):
    """
    Main function 
    """
    """
    get global variable configuration
    """
    global_username = helper.get_global_setting("username")
    global_password = helper.get_global_setting("password")
    global_usrn = helper.get_global_setting("usrn")
    global_client_id = helper.get_global_setting("clientid")
    
    """
    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    
    you can find the logs in : $SPLUNK_HOME/var/log/splunk/[add-on folder name].log 
    in this case:
    ta_nucleon_add_on_for_threat_intelligent_activeThreats
    """
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    # helper.log_info("Started")
    if(global_username == None):
        helper.log_warning("Set UserName")
        exit()

    if(global_usrn == None):
        helper.log_warning("Set USRN")
        exit()

    if(global_client_id == None):
        helper.log_warning("Set Client ID")
        exit()


    if(global_password == None):
        helper.log_warning("Set Password")
        exit()
        
        
    helper.log_info("Started fetching assets information")
    

    reset=0
    limit=190 # limt of returned data from the api cal 
    response = request(global_username,global_password,global_usrn,global_client_id,reset,limit,helper)
    json_payload=json.loads(response)
    if(json_payload.get('status')!=1):
        helper.log_error(json_payload.get("msg"))
        exit()
        
    
    if(json_payload.get('status')==1 and json_payload.get('summary').get("total")==0):
        helper.log_info("API total=0")
        exit()
    helper.log_info(" count of fetched data from activethreats api: "+str(len(json_payload.get('data'))))
    helper.log_info("API total="+ str(json_payload.get('summary').get("total")))
        
    modify_array(json_payload.get('data'),json_payload.get('summary'),json_payload.get('timeStamp'),ew,helper)
    
    
    
