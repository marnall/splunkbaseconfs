
# encoding = utf-8

import os
import sys
import time
import datetime

from umbrella.event_processer import AWSS3Connection

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
    # region = definition.parameters.get('region', None)
    # access_key_id = definition.parameters.get('access_key_id', None)
    # secret_access_key = definition.parameters.get('secret_access_key', None)
    # bucket_name = definition.parameters.get('bucket_name', None)
    # prefix = definition.parameters.get('prefix', None)
    # start_date = definition.parameters.get('start_date', None)
    # event_type = definition.parameters.get('event_type', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    aws_s3_conn = AWSS3Connection()
    aws_s3_conn.ew = ew
    aws_s3_conn.helper = helper
    # collect events AWS S3 bucket
    aws_s3_conn.fetch_events_from_s3_bucket()
    #aws_s3_conn.delete_existing_check_point()

    """
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_region = helper.get_arg('region')
    opt_access_key_id = helper.get_arg('access_key_id')
    opt_secret_access_key = helper.get_arg('secret_access_key')
    opt_bucket_name = helper.get_arg('bucket_name')
    opt_prefix = helper.get_arg('prefix')
    opt_start_date = helper.get_arg('start_date')
    opt_event_type = helper.get_arg('event_type')
    # In single instance mode, to get arguments of a particular input, use
    opt_region = helper.get_arg('region', stanza_name)
    opt_access_key_id = helper.get_arg('access_key_id', stanza_name)
    opt_secret_access_key = helper.get_arg('secret_access_key', stanza_name)
    opt_bucket_name = helper.get_arg('bucket_name', stanza_name)
    opt_prefix = helper.get_arg('prefix', stanza_name)
    opt_start_date = helper.get_arg('start_date', stanza_name)
    opt_event_type = helper.get_arg('event_type', stanza_name)
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
