
# encoding = utf-8
import os
import sys
import time
import datetime
import requests
import json
import hashlib
import re
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
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # user_agent = definition.parameters.get('user_agent', None)
    # api_key = definition.parameters.get('api_key', None)
    # siteid = definition.parameters.get('siteid', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    
    opt_username = helper.get_global_setting('username')
    opt_password = helper.get_global_setting('password')
    opt_app_source_name = helper.get_global_setting('app_source_name')
    opt_api_key = helper.get_global_setting('api_key')
    opt_siteid = helper.get_global_setting('siteid')
    key = helper.get_global_setting('activation_key')
    app="Mindbodyonline Add-on for Splunk"
    if key:
        try:
            app_md =hashlib.md5(app.encode('utf-8'))
            app_hex=app_md.hexdigest().upper()
            app_dec = int(app_hex,16)
            app_dec_sum=sum([int(x) for x in str(int(app_dec))])
            key_time = key[-10:]
            key_time= key_time[::-1]
            match_key=re.search('[a-zA-Z]', key_time)
            key = key[:-10]
            vbits = key[:-32]
            key = key[-32:]
            dec = int(key, 16)
            li=[int(x) for x in str(int(dec))]
            s=sum(list(li))
            current_ts = time.time()
            if len(key)!=32 or match_key:
                helper.log_info("Actvation Key did not matched, kindly check if you have entered the correct key")
                sys.exit(2)
            else:
                if current_ts-int(key_time)>7776000:
                    helper.log_info("kindly check if you have entered the correct key OR Activation Key has expired, kindly get a new one")
                    sys.exit(2)
                if not int(s)+int(app_dec_sum)==int(vbits):
                    helper.log_info("Actvation Key did not matched, kindly check if you have entered correct key")
                    sys.exit(2)
            helper.log_info("Activation Key Successfullly Entered")
        except Exception as e:
            helper.log_info("Actvation Key did not matched, kindly check if you have entered correct key")
            sys.exit(2)
    else:
        helper.log_info("Enter the Activation Key in Configuration>Add-on Settings")
        sys.exit(2)
    url_token = "https://api.mindbodyonline.com/public/v6/usertoken/issue"
    payload_token = json.dumps({
        "Username": opt_username,
        "Password": opt_password
    })
    headers_token = {
        'User-Agent': opt_app_source_name,
        'Content-Type': 'application/json',
        'Api-Key': opt_api_key,
        'SiteId': opt_siteid,
    }
    
    
    response_token = requests.request("POST", url_token, headers=headers_token, data=payload_token)
    response_token_json=response_token.json()
    token=""
    for i in response_token_json:
        token=response_token_json["AccessToken"]
        
    ##
    url_paymenttypes = "https://api.mindbodyonline.com/public/v6/site/paymenttypes"

    headers_paymenttypes = {
        'User-Agent': opt_app_source_name,
        'Api-Key': opt_api_key,
        'Authorization': token,
        'Content-Type': 'application/json',
        'SiteId': opt_siteid,
    }
    
    response_paymenttypes = requests.request("GET", url_paymenttypes, headers=headers_paymenttypes)
    response_paymenttypes_json=response_paymenttypes.json()
        
    
    final_result = []
    for i in response_paymenttypes_json["PaymentTypes"]:
        state = helper.get_check_point(str(i["Id"]))
        if state is None:
            final_result.append(i)
            helper.save_check_point(str(i["Id"]), "Indexed")
        # helper.delete_check_point(str(i["Id"]))
    status = response_paymenttypes.status_code
    count = len(final_result)
    status = "The API="+str(url_paymenttypes)+"  | response_code="+str(status)+"  | number_of_events="+str(count)
    helper.log_info(status)
    event = helper.new_event(json.dumps(final_result))
    ew.write_event(event)
    
    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_username = helper.get_arg('username')
    opt_password = helper.get_arg('password')
    opt_user_agent = helper.get_arg('user_agent')
    opt_api_key = helper.get_arg('api_key')
    opt_siteid = helper.get_arg('siteid')
    opt_password = helper.get_arg('password')
    # In single instance mode, to get arguments of a particular input, use
    opt_username = helper.get_arg('username', stanza_name)
    opt_password = helper.get_arg('password', stanza_name)
    opt_user_agent = helper.get_arg('user_agent', stanza_name)
    opt_api_key = helper.get_arg('api_key', stanza_name)
    opt_siteid = helper.get_arg('siteid', stanza_name)
    opt_password = helper.get_arg('password', stanza_name)

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
