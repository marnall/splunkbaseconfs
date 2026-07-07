
# encoding = utf-8

import os
import sys
import time
import datetime
import dateutil.parser
import json

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
    # account = definition.parameters.get('account', None)
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
        return dateutil.parser.parse(d["end_date"])
    else:
        # No check point date, so look if a start date was specified as an argument
        d = helper.get_arg("since_date")
        if (d not in [None,'']):
            return dateutil.parser.parse(d)
        else:
            # If there was no start date specified, default to 7 days ago
            return datetime.datetime.utcnow() - datetime.timedelta(days=7)



def collect_events(helper, ew):
    
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    check_point_key = "%s_obj_checkpoint" % helper.get_input_stanza_names()
    checkpoint_data = {}
    
    opt_source_type = helper.get_arg('source_type')
    
    if opt_source_type:
        sourcetype = opt_source_type
    else:
        sourcetype= helper.get_sourcetype()
    
    host = helper.get_arg('account').get("username")
    password = helper.get_arg('account').get("password")
    helper.log_debug("host={}".format(host))
    
    headers = {
      'Content-Type': 'application/json',
      'Accepts': 'application/json',
      'Authorization': 'Token token='+password
    }
    
    url = "https://"+host+"/api/audit-log/security-trail/"
    
    

    while(True):
        
        start_date = get_start_date(helper, check_point_key)
        helper.log_debug("logs will be collected for datetime={}".format(start_date))
        
        # Get the current UTC time truncated to the hour
        current_utc_hour = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        # Check if start_date is less than the current UTC hour
        if start_date < current_utc_hour:
    
            year = start_date.year
            month = start_date.month
            day = start_date.day
            hour = start_date.hour
            
            payload =  json.dumps({
              "year": year,
              "month": month,
              "day": day, # Tried getting logs by just providing year and month. got error. So, day must be provided. 
              "hour": hour #possible values 1-23. don't say 01 for 1 just say 1
            })
        
    
            helper.log_debug("payload={}".format(payload))
            response = helper.send_http_request(url, method="POST", parameters=None, payload=payload,
                                                headers=headers, cookies=None, verify=True, cert=None,
                                                timeout=None, use_proxy=True)
            if response.ok:
                r_json = response.json()
                list_data = r_json.get("result")
                nextPageToken = r_json.get("nextPageToken")
                helper.log_debug("nextPageToken type={}".format(type(nextPageToken)))
                if len(list_data) > 0:
                    for record in list_data:
                        data=json.dumps(record)
                        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
                        ew.write_event(event)
                else:
                    helper.log_debug("response={}".format(response.content))
                try:
                    if nextPageToken is not None:
                        helper.log_debug("nextPageToken is present and this is not handled in script. You may loose the data, consult developer. nextPageToken={}".format(nextPageToken))
                    else:
                        # when it's known how to page nextPageToken in request, nextPageToken must be stored in checkpoint after every request is processed. this make sure that script can continue since where its stopped if the script is failed when more pages for a single request. 
                        checkpoint_data["end_date"] = start_date + datetime.timedelta(hours=1)
                        helper.log_debug("saving checkpoint for input={} and next_start_date={}".format(check_point_key,checkpoint_data))
                        helper.save_check_point(check_point_key,checkpoint_data)
                        sys.exit()
                except Exception as e:
                    helper.log_error("exception={}".format(e))
        
            else:
                helper.log_debug("Error in response. response_code={},response_content={}".format(response.status_code,response.content))
                sys.exit()
        else:
            helper.info("finished collecting logs until current time")
                        
            
        
    
    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_account = helper.get_arg('account')
    opt_since_date = helper.get_arg('since_date')
    opt_source_type = helper.get_arg('source_type')
    # In single instance mode, to get arguments of a particular input, use
    opt_account = helper.get_arg('account', stanza_name)
    opt_since_date = helper.get_arg('since_date', stanza_name)
    opt_source_type = helper.get_arg('source_type', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

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
    

    # The following examples send rest requests to some endpoint.

    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
