
# encoding = utf-8

import os
import sys
import time
import datetime
import dateutil.parser
import json


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    since_date = definition.parameters.get('since_date', None)
    # source_type = definition.parameters.get('source_type', None)
    
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
        return (d["end_date"])
    else:
        # No check point date, so look if a start date was specified as an argument
        d = helper.get_arg("since_date")
        if (d not in [None,'']):
            return int((dateutil.parser.parse(d)).timestamp() * 1000)
        else:
            # If there was no start date specified, default to 7 days ago
            return int((datetime.datetime.now() - datetime.timedelta(days=7)).timestamp() * 1000)

def collect_events(helper, ew):
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    check_point_key = "%s_obj_checkpoint" % helper.get_input_stanza_names()
    helper.log_info("check_point_key={}".format(check_point_key))
    checkpoint_data = {}
    
    username = helper.get_arg('global_account').get("username")
    password = helper.get_arg('global_account').get("password")
    helper.log_debug("username={}".format(username))
    
    opt_since_date = helper.get_arg('since_date')
    opt_source_type = helper.get_arg('source_type')
    
    # delete checkpoint
    #helper.delete_check_point(check_point_key)
    
    d = helper.get_check_point(check_point_key)

    # Check if 'nextToken' exists in the dictionary and is not None
    if d and d.get("nextToken"):
        start_date = d.get("start_date")
        end_date = d.get("end_date")
        nextToken = d.get("nextToken")
        helper.log_info("last job terminated unexpectedly. Resuming from the last request. Note: This may possibly result in 100 max duplicate logs.")
    else:
        start_date = str(get_start_date(helper, check_point_key))
        end_date = int(datetime.datetime.now().timestamp() * 1000)
        nextToken = ""
    
    #start_date = str(get_start_date(helper, check_point_key))
    #end_date = int(datetime.datetime.now().timestamp() * 1000)
    
    helper.log_debug("start_date={},end_date={}".format(start_date,end_date))
    
    if opt_source_type:
        sourcetype = opt_source_type
    else:
        sourcetype= helper.get_sourcetype()
    
    auth_url = "https://api.prismacloud.io/login"
    data_url = "https://api.prismacloud.io/audit/api/v1/log"
    
    if int(end_date) > int(start_date):

        
        keep_running = True
        while keep_running:
                     
            auth_payload = json.dumps({
            "username": username,
            "password": password
            })

            auth_headers = {
            'Content-Type': 'application/json'
            }

            headers = {"Authorization": "apikey " +  password,
                        "accept" : "application/json"
            }
            
            auth_response = helper.send_http_request(auth_url, method="POST", parameters=None, payload=auth_payload,
                                            headers=auth_headers, cookies=None, verify=True, cert=None,
                                            timeout=120, use_proxy=True)
                                            
            if auth_response.ok:
                auth_r_json = auth_response.json()
                auth_token = auth_r_json.get("token")
                if auth_token:
            
                    if nextToken:
                        data_payload = json.dumps({
                        "timeRange": {
                        "type": "absolute",
                        "value": {
                          "startTime": start_date,
                          "endTime": end_date
                            }
                        },
                        "limit":100, # to reduce number of duplicates if iteration fails while indexing results from any given response
                        "nextPageToken": nextToken
                        })
                    else:
                        data_payload = json.dumps({
                            "timeRange": {
                            "type": "absolute",
                                "value": {
                                  "startTime": start_date,
                                  "endTime": end_date
                                }
                            },
                            "limit":100, # to reduce number of duplicates if iteration fails while indexing results from any given response
                        })
                    
                    data_headers = {
                      'Content-Type': 'application/json',
                      'Accept': 'application/json',
                      'x-redlock-auth': auth_token
                    }
        
                    response = helper.send_http_request(data_url, method="POST", parameters=None, payload=data_payload,
                                                    headers=data_headers, cookies=None, verify=True, cert=None,
                                                    timeout=120, use_proxy=True)
        
                    if response.ok:
        
                        r_json = response.json()
                        #helper.log_debug("response_content={}".format(r_json))
                        list_data = r_json.get('value')
                        if list_data:
                            for record in list_data:
                                #helper.log_debug("record={}".format(type(record)))
                                data = json.dumps(record)
                                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
                                ew.write_event(event)
                            try:
                                if r_json.get("nextPageToken"):
                                    helper.log_debug("nextPageToken={}".format(r_json.get("nextPageToken")))
                                    nextToken = r_json.get("nextPageToken")
                                else:
                                    helper.log_info("nextPageToken is not present, saving the final checkpoint and exiting the script")
                                    nextToken = ""
                                    start_date = ""
                                    keep_running = False
                                    
                                checkpoint_data["end_date"] = str(end_date)
                                checkpoint_data["start_date"] = str(start_date)
                                checkpoint_data["nextToken"] = str(nextToken)
                                helper.log_debug("saving checkpoint for input={} and end_date={}".format(check_point_key,checkpoint_data))
                                helper.save_check_point(check_point_key,checkpoint_data)
                                
                                
                            except Exception as e:
                                helper.log_error("exception={}".format(e))
                    else:
                        helper.log_error("error in data collection".format(response.json()))
                    
                else:
                    helper.log_error("No authentication token found".format(auth_response.json()))
            else:
                helper.log_error("failed to get authentication token".format(auth_response.json()))
    else:
        helper.log_info("end_date>start_date.existing the script!")
                

