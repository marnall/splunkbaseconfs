
# encoding = utf-8

import os
import sys
import time
import datetime
import requests 
import json
from requests.auth import HTTPDigestAuth

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # endpoint_domain = definition.parameters.get('endpoint_domain', None)
    # group_id = definition.parameters.get('group_id', None)
    # cluster_name = definition.parameters.get('cluster_name', None)
    start_date = definition.parameters.get('start_date', None)
    
    if start_date is not None:
        try:
            start = int(start_date)
        except Exception as ve:
            error_message = "Invalid date format specified for 'Log collection start date'. Enter value in UNIX epoch format"
            raise ValueError(error_message)
    pass

def get_start_date(helper,check_point_key):
    
    # check if check_point_key exists. it exists if the input was already run before successfully 
    d=helper.get_check_point(check_point_key)
    
    if (d not in [None,'']):
        return d["end_date"]
    else:
        #No check_point_key is available. check if user has entered 'Log collection start date(start_date)' in input
        helper.log_debug("No checkpoint key available")
        d = helper.get_arg("start_date")
        if (d not in [None,'']):
            helper.log_debug("user input of Log collection start date(start_date):{}".format(d))
            return d
        else:
            seven_days_ago = datetime.datetime.now()  - datetime.timedelta(days=7)
            d = int(seven_days_ago.timestamp())
            return d
    
    

def collect_events(helper, ew):
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    # For multi instance mod input, args will be returned as a single value.
    opt_endpoint_domain = helper.get_arg('endpoint_domain')
    opt_group_id = helper.get_arg('group_id')
    opt_cluster_name = helper.get_arg('cluster_name')
    opt_start_date = helper.get_arg('start_date')
    
    # get all stanza names
    input_name = helper.get_input_stanza_names()
    helper.log_debug("input_name={}".format(input_name))
    
    check_point_key = "%s_obj_checkpoint" % input_name
    helper.log_debug("check_point_key={}".format(check_point_key))
    
    username = helper.get_arg("global_account").get("username")
    password = helper.get_arg("global_account").get("password")
    
    helper.log_debug("username={}".format(username))
    
    #test - to delete checkpoint while testing this input from add-on builder
    #helper.delete_check_point(check_point_key)
    
    start_date = get_start_date(helper,check_point_key)
    end_date = int((datetime.datetime.now()).timestamp())
    
    data_url = "https://"+opt_endpoint_domain+"/api/atlas/v2/groups/"+opt_group_id+"/dbAccessHistory/clusters/"+opt_cluster_name+"?pretty=true&start="+str(start_date)+"&end="+str(end_date)
    
    session = requests.Session()
    session.auth = HTTPDigestAuth(username,password)
    
    headers = {
        'Accept':'application/vnd.atlas.2023-02-01+json'
        }
    try:
        response = session.get(data_url,verify=True,headers=headers)
        
        checkpoint_data = {}
        
        if response.ok:
            response_json = json.loads(response.content)
            #helper.log_debug("reponse={}".format(response_json))
            response_json_accessLogs = response_json.get("accessLogs")
            
            accessLogs_len = len(response_json_accessLogs)
            
            helper.log_debug("Number of events returned={}".format(accessLogs_len))
            
            if accessLogs_len > 0:
                for accessLog in response_json_accessLogs:
                    helper.log_debug("accessLog={}".format(accessLog))
                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(accessLog))
                    ew.write_event(event)
                checkpoint_data["end_date"] = str(end_date)
                helper.save_check_point(check_point_key,checkpoint_data)
                helper.log_info("events={} have been indexed successfully".format(accessLogs_len))
                
        else:
            helper.log_error("failed to call api. error={}".format(response.content))
    except Exception as excp:
        helper.log_error("error occured in collect events. error={}".format(excp))
        
            
    