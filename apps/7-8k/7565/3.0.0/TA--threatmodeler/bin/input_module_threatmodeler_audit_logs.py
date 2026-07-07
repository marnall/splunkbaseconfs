
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
    since_date = definition.parameters.get('since_date', None)
    # custom_source_type = definition.parameters.get('custom_source_type', None)
    
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
            return (dateutil.parser.parse(d)).strftime("%Y-%m-%dT%H:%M:%S")
        else:
            # If there was no start date specified, default to 7 days ago
            return (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")


def collect_events(helper, ew):
    
    
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    check_point_key = "%s_obj_checkpoint" % helper.get_input_stanza_names()
    checkpoint_data = {} 
    
    opt_since_date = helper.get_arg('since_date')
    opt_source_type = helper.get_arg('custom_source_type')
    
    start_date = str(get_start_date(helper, check_point_key))
    end_date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    
    helper.log_debug("start_date={},end_date={}".format(start_date,end_date))
    
    domain = helper.get_arg('global_account').get("username")
    password = helper.get_arg('global_account').get("password")
    
    helper.log_debug("domain={}".format(domain))
    
    
    headers = {
        'X-ThreatModeler-ApiKey' : password
        }
    
    url = f"https://{domain}/api/auditevents/0/0/{start_date}/{end_date}"
    
    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method="GET", parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
                                        
    if response.ok:
        
        r_json = response.json()
        list_data = r_json.get('Data')
        for record in list_data:
            data = json.dumps(record)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=opt_source_type if opt_source_type else helper.get_sourcetype(), data=data)
            ew.write_event(event)
        checkpoint_data["end_date"] = str(end_date)
        helper.log_debug("saving checkpoint for input={} and end_date={}".format(check_point_key,checkpoint_data))
        helper.save_check_point(check_point_key,checkpoint_data)
        sys.exit()
        
    else:
        helper.log_debug("Error in response. response_code={}, response_content={}".format(response.status_code, response.content))

  
