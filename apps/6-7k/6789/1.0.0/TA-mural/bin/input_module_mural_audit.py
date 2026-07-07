
# encoding = utf-8

import json
import os
import sys
import time
import datetime
import dateutil.parser
import urllib.parse

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
    mural_endpoint_url = definition.parameters.get('mural_endpoint_url', None)
    max_results = definition.parameters.get('max_results', None)
    action_filter = definition.parameters.get('action_filter', None)
    since_date = definition.parameters.get('since_date', None)
    global_account = definition.parameters.get('global_account', None)
    source_type = definition.parameters.get('source_type', None)
    
    # Start date checks
    if since_date is not None:
        try:
            start = ""
            start = dateutil.parser.parse(since_date)
        except Exception as e:
            error_message = "Invalid date format specified for 'Since Date'"
            helper.log_error(error_message)
            raise ValueError(error_message)
    pass

def get_start_date(helper, check_point_key):

    # Try to get a date from the check point first
    d = helper.get_check_point(check_point_key)

    # If there was a check point date, retun it.
    if (d not in [None,'']):
        return dateutil.parser.parse(d["end_date"])
    else:
        # No check point date, so look if a start date was specified as an argument
        d = helper.get_arg("since_date")
        if (d not in [None,'']):
            return dateutil.parser.parse(d)
        else:
            # If there was no start date specified, default to 7 days ago
            return (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

def collect_events(helper, ew):
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    check_point_key = "%s_obj_checkpoint" % helper.get_input_stanza_names()
    checkpoint_data = {} 
    opt_mural_endpoint_url = helper.get_arg('mural_endpoint_url')
    opt_max_results = helper.get_arg('max_results')
    opt_action_filter = helper.get_arg('action_filter')
    opt_since_date = helper.get_arg('since_date')
    opt_global_account = helper.get_arg('global_account')
    opt_source_type = helper.get_arg('source_type')
    
    start_date = str(get_start_date(helper, check_point_key))
    end_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    helper.log_debug("start_date={},end_date={}".format(start_date,end_date))
    
    start_date_epoch = int(datetime.datetime.strptime(start_date,"%Y-%m-%d %H:%M:%S").strftime('%s'))
    end_date_epoch = int(datetime.datetime.utcnow().timestamp())
    
    username = helper.get_arg('global_account').get("username")
    password = helper.get_arg('global_account').get("password")
    
    helper.log_debug("username={}".format(username))
    
    
    if end_date_epoch > start_date_epoch:
        
        nextToken = ""
        while(True):
        
            headers = {"Authorization": "apikey " +  password,
                        "accept" : "application/json"
                }
           
            start_date = urllib.parse.quote(start_date)
            end_date_parsed = urllib.parse.quote(end_date)
            
            if (opt_action_filter not in [None,'']):
                # https://api.mural.co/enterprise/v1/audit-log?maxResults=1000&filter\[action\]=ABORT_VOTING_SESSION&filter\[date\]\[since\]=2023-02-25%2000%3A00%3A00&filter\[date\]\[until\]=2023-02-27%2000%3A00%3A00
                
                url = opt_mural_endpoint_url+"?maxResults="+opt_max_results+"&filter\[action\]="+opt_action_filter+"&filter\[date\]\[since\]="+start_date+"&filter\[date\]\[until\]="+end_date_parsed
            else:
                #https://api.mural.co/enterprise/v1/audit-log?maxResults=1000&filter\[date\]\[since\]=2023-02-25%2000%3A00%3A00&filter\[date\]\[until\]=2023-02-27%2000%3A00%3A00
                url = opt_mural_endpoint_url+"?maxResults="+opt_max_results+"&filter\[date\]\[since\]="+start_date+"&filter\[date\]\[until\]="+end_date_parsed
            
            if nextToken:
                url = url+"&nextToken="+nextToken
            
            helper.log_debug("url={}".format(url))
            
            method="GET"
                
            response = helper.send_http_request(url, method, parameters=None, payload=None,
                                            headers=headers, cookies=None, verify=True, cert=None,
                                            timeout=120, use_proxy=True)
            
            if response.ok:
                
                r_json = response.json()
                #helper.log_debug("response_content={}".format(r_json))
                list_data = r_json.get('data')
                for record in list_data:
                    #helper.log_debug("record={}".format(type(record)))
                    data = json.dumps(record)
                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=opt_source_type, data=data)
                    ew.write_event(event)
                try:
                    if "nextToken" in r_json:
                        helper.log_debug("nextToken={}".format(r_json.get("nextToken")))
                        nextToken = r_json.get("nextToken")
                        
                    else:
                        helper.log_debug("nextToken is not present,exiting the script")
                        checkpoint_data["end_date"] = str(end_date)
                        helper.log_debug("saving checkpoint for input={} and end_date={}".format(check_point_key,checkpoint_data))
                        helper.save_check_point(check_point_key,checkpoint_data)
                        sys.exit()
                except Exception as e:
                    helper.log_error("exception={}".format(e))

            else:
                helper.log_debug("Error in response. response_code={}".format(response.status_code))
                helper.log_debug("Error in response. response_content={}".format(response.content))
                sys.exit()
    
    
