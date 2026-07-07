
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import xmltodict
from addonutils.activation_key import _validate_activation_key

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
UrlList = {"EC2"  : "https://status.aws.amazon.com/rss/ec2-us-east-1.rss",

"S3" : "https://status.aws.amazon.com/rss/s3-us-east-1.rss",

"RDS" : "https://status.aws.amazon.com/rss/rds-us-east-1.rss",

"Cloudfront" : "https://status.aws.amazon.com/rss/cloudfront.rss",

"VPC" : "https://status.aws.amazon.com/rss/vpc-us-east-1.rss",

"SNS" : "https://status.aws.amazon.com/rss/sns-us-east-1.rss",

"Lambda" : "https://status.aws.amazon.com/rss/lambda-us-east-1.rss"}

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # multiple_dropdown = definition.parameters.get('multiple_dropdown', None)
    pass

def collect_events(helper, ew):
    app_name = "Cloud Status Add-on for Splunk"
    activation_key = helper.get_global_setting('activation_key')
    key_validator = _validate_activation_key(app_name, activation_key)
    if key_validator:
        helper.log_info(key_validator)
        sys.exit(2)
    final_data_set = []
    opt_multiple_dropdown = helper.get_arg('multiple_dropdown')
    urls = [UrlList[i] for i in opt_multiple_dropdown]
    count = 0
    for url in urls:
        response = helper.send_http_request(url, 'GET', parameters=None, payload=None
                                            , cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
        data = xmltodict.parse(response.text)  
        data = data["rss"]["channel"]
        if type(data) == list:
            for k in data:
                TimeEntry_state = helper.get_check_point(str(k["title"]+k["lastBuildDate"]+k["generator"]), "Indexed")
                if TimeEntry_state is None:
                    final_data_set.append(k)
                    count+=1
                    helper.save_check_point(str(k["title"]+k["lastBuildDate"]+k["generator"]), "Indexed")
                # helper.delete_check_point(k["title"]+k["lastBuildDate"]+k["generator"])
                
            if final_data_set!=[]:
                event = helper.new_event(json.dumps(final_data_set, indent=4), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)
        else:
            key = json.dumps(str(data["title"] + data["lastBuildDate"] + data["generator"]))
            TimeEntry_state = helper.get_check_point(key)
            if TimeEntry_state is None:
                count+=1
                helper.save_check_point(key, "Indexed")
                data.update({"Status":"Active"})
                event = helper.new_event(json.dumps(data, indent=4), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)
            # helper.delete_check_point(key)
            
      

    status = ("API=" + ''.join(urls) + "| response_code=" + str(response.status_code) +"| number_of_events=" + str(count))                        
    helper.log_info(status)        
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_multiple_dropdown = helper.get_arg('multiple_dropdown')
    # In single instance mode, to get arguments of a particular input, use
    opt_multiple_dropdown = helper.get_arg('multiple_dropdown', stanza_name)

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
    loglevel = helper.get_log_level()
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
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
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
