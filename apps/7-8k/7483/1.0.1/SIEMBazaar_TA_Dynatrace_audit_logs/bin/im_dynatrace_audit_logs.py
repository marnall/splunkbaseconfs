
# encoding = utf-8

import datetime
import json
import sys

def validate_input(helper, definition):
    pass

def get_start_date(helper,check_point_key):

    # check if check_point_key exists. it exists if the input was already run before successfully
    d=helper.get_check_point(check_point_key)

    if (d not in [None,'']):
        return d["end_date"]
    else:
        #No check_point_key is available. check if user has entered 'Log collection start date(start_date)' in input
        helper.log_debug("No checkpoint key available")
        d = helper.get_arg("since_date")
        if (d not in [None,'']):
            helper.log_debug("user input of Log collection since date(since_date)={}".format(d))
            return d
        else:
            seven_days_ago = datetime.datetime.now()  - datetime.timedelta(days=7)
            d = int(seven_days_ago.timestamp()) * 1000
            return d

def collect_events(helper, ew):
    
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    opt_dynatrace_account = helper.get_arg('dynatrace_account')
    
    api_token =  opt_dynatrace_account["password"]
    
    opt_dynatrace_endpoint = helper.get_arg('dynatrace_endpoint')
    opt_since_date = helper.get_arg('since_dte')
    opt_page_size = helper.get_arg('page_size')
    opt_filter = helper.get_arg('filter')
    opt_custom_source_type = helper.get_arg('custom_source_type')
    
    # get all stanza names
    input_name = helper.get_input_stanza_names()
    helper.log_debug("input_name={}".format(input_name))

    check_point_key = "%s_obj_checkpoint" % input_name
    helper.log_debug("check_point_key={}".format(check_point_key))
    

    
    headers = {"Authorization": "Api-Token "+api_token}
    
    #test - to delete checkpoint while testing this input from add-on builder
    #helper.delete_check_point(check_point_key)
            
    since_date = get_start_date(helper,check_point_key)
    helper.log_debug("since_date={}".format(since_date))
    
    end_date = int(datetime.datetime.now().timestamp()) * 1000
    helper.log_debug("end_date={}".format(end_date))
    
    nextPageKey = ""
    checkpoint_data = {}
    
    try:
        
        while(True):
            
            if nextPageKey:
                
                data_url = "https://"+opt_dynatrace_endpoint+"/api/v2/auditlogs?nextPageKey="+nextPageKey
                helper.log_debug("data_url={}".format(data_url))  
                
                response = helper.send_http_request(url=data_url, method="GET", parameters=None, payload=None,
                                            headers=headers, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
            else:
                data_url = "https://"+opt_dynatrace_endpoint+"/api/v2/auditlogs?from="+str(since_date)+"&to="+str(end_date)
    
                if opt_filter:
                    data_url = data_url+"&filter="+str(opt_filter)
                if opt_page_size:
                    data_url = data_url+"&pageSize="+str(opt_page_size)
                
                helper.log_debug("data_url={}".format(data_url))        
                    
                response = helper.send_http_request(url=data_url, method="GET", parameters=None, payload=None,
                                            headers=headers, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
                                            
            if response.ok:
                response_json = json.loads(response.content)
                #helper.log_debug("reponse={}".format(response_json))
                total_log_count = response_json.get("totalCount")
                helper.log_debug("total_log_count={}".format(total_log_count))
                
                per_call_log_count = response_json.get("pageSize")
                helper.log_debug("per_call_log_count={}".format(per_call_log_count))
                
                response_json_auditlogs = response_json.get("auditLogs")
                #helper.log_debug("response_json_auditlogs={}".format(response_json_auditlogs))
                
                auditlogs_len = len(response_json_auditlogs)
                helper.log_debug("Number of events returned={}".format(auditlogs_len))
    
                if auditlogs_len > 0:
                    for auditLog in response_json_auditlogs:
                        #helper.log_debug("accessLog={}".format(auditLog))
                        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=opt_custom_source_type if opt_custom_source_type else helper.get_sourcetype(), data=json.dumps(auditLog))
                        ew.write_event(event)
                    helper.log_info("events={} have been indexed successfully".format(auditlogs_len))
                                
                if response_json.get("nextPageKey"):
                    nextPageKey = response_json.get("nextPageKey")
                    helper.log_debug("nextPageKey={}".format(nextPageKey))
                else:
                    helper.log_info("No more events to collect; hence, exiting.")
                    checkpoint_data["end_date"] = str(end_date)
                    helper.save_check_point(check_point_key,checkpoint_data)
                    sys.exit()
            else:
                helper.log_error("failed to call api. error={}".format(response.content))
                sys.exit()
    except Exception as excp:
        helper.log_error("error occured in collect events. error={}".format(excp))

    