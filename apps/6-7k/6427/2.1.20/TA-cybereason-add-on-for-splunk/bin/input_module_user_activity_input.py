
# encoding = utf-8

import os
import sys
import time
import datetime
import json
from cybereason_rest_client import CybereasonClient
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

_APP_NAME = 'CybereasonAddOnForSplunk'

log_location = make_splunkhome_path(['var', 'log', 'splunk', _APP_NAME])
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
    # base_url = definition.parameters.get('base_url', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # authentication_type = definition.parameters.get('authentication_type', None)
    # users = definition.parameters.get('users', None)
    # user_action_logs = definition.parameters.get('user_action_logs', None)
    # logon_sessions = definition.parameters.get('logon_sessions', None)
    pass

def get_last_polled_timestamp(base_url, username):
    host = "user_activity-"+base_url.split(":")[0]+"-"+username
    file_dir = os.path.join(log_location, 'user_activity_data_input',host)
    filepath = os.path.join(file_dir, 'timestamp.txt')
    earliest = 0
    if not os.path.exists(file_dir):
            os.makedirs(file_dir)
    elif os.path.exists(filepath) and os.stat(filepath).st_size != 0:
        file1 = open(filepath, "r")
        earliest = int(file1.read())
        file1.close()

    return earliest

def set_last_polled_timestamp(base_url, username, timestamp):
    host = "user_activity-"+base_url.split(":")[0]+"-"+username
    file_dir = os.path.join(log_location, 'user_activity_data_input',host)
    filepath = os.path.join(file_dir, 'timestamp.txt')
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(filepath, "w") as file1:
        file1.write(str(timestamp))

def collect_events(helper, ew):
    
    try:
        # The following examples get the arguments of this input.
        # Note, for single instance mod input, args will be returned as a dict.
        # For multi instance mod input, args will be returned as a single value.
        opt_base_url = helper.get_arg('base_url')
        opt_username = helper.get_arg('username')
        opt_password = helper.get_arg('password')
        opt_hist_days = helper.get_arg('hist_days')
        opt_authentication_type = helper.get_arg('authentication_type')
        opt_users = helper.get_arg('users')
        opt_user_action_logs = helper.get_arg('user_action_logs')
        opt_logon_sessions = helper.get_arg('logon_sessions')
        opt_cybereason_account = dict()
        opt_cybereason_account['password'] = opt_password
        opt_cybereason_account['username'] = opt_username
        # get proxy setting configuration
        proxy_settings = helper.get_proxy()
        earliest = get_last_polled_timestamp(opt_base_url, opt_username)
        if earliest < 1:
            earliest = round((datetime.datetime.now() - datetime.timedelta(days=int(opt_hist_days))).timestamp())
        now = round(datetime.datetime.now().timestamp())
        cyb_client = CybereasonClient(helper,ew, opt_base_url, opt_cybereason_account, opt_authentication_type, proxy_settings)
        if opt_users:
            users = cyb_client.get_all_users() 
            if users:
                sourcetype = "cybereason:api"
                data = json.dumps(users)
                event = helper.new_event(host=opt_base_url.split(":")[0], source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
                ew.write_event(event)
        if opt_logon_sessions:
            logon_sessions  = cyb_client.get_logon_sessions(start_time=int(earliest), end_time=int(now))
            if logon_sessions:
                sourcetype = "cybereason:api"
                data = json.dumps(logon_sessions)
                event = helper.new_event(host=opt_base_url.split(":")[0], source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
                ew.write_event(event)
        if opt_user_action_logs:
            cyb_client.get_all_action_logs()
        set_last_polled_timestamp(opt_base_url, opt_username, now)
    except Exception as e:
        sourcetype = "CybereasonAddonForSplunk:error"
        data = str(e)
        event = helper.new_event(source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
        ew.write_event(event)
    

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''
