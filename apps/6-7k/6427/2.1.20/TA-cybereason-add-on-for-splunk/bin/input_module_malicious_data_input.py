# encoding = utf-8
import math
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
    # group_name = definition.parameters.get('group_name', None)
    # malops = definition.parameters.get('malops', None)
    # suspicious_objects = definition.parameters.get('suspicious_objects', None)
    # malware = definition.parameters.get('malware', None)
    # pull_comments = definition.parameters.get('pull_comments', None)
    pass

def get_last_polled_timestamp(base_url, username):
    host = "malicious-"+base_url.split(":")[0]+"-"+username
    file_dir = os.path.join(log_location, 'malicious_data_input',host) 
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
    host = "malicious-"+base_url.split(":")[0]+"-"+username
    file_dir = os.path.join(log_location, 'malicious_data_input',host) 
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
        opt_interval = int(helper.get_arg('interval'))
        opt_hist_days = helper.get_arg('hist_days')
        opt_buffer_time = int(helper.get_arg('buffer_time'))
        opt_authentication_type = helper.get_arg('authentication_type')
        opt_sensor_group_names = helper.get_arg('group_name')
        opt_malop_status = helper.get_arg('select_malop_status')
        helper.log_info(f"malop_status: {opt_malop_status}")
        opt_malops = helper.get_arg('malops')
        opt_suspicious_objects = helper.get_arg('suspicious_objects')
        opt_malware = helper.get_arg('malware')
        opt_pull_comments = helper.get_arg('pull_comments')
        opt_cybereason_account = dict()
        opt_cybereason_account['password'] = opt_password
        opt_cybereason_account['username'] = opt_username

        # get proxy setting configuration
        proxy_settings = helper.get_proxy()

        now = round(datetime.datetime.now().timestamp())
        earliest = get_last_polled_timestamp(opt_base_url, opt_username)
        last_poll_timestamp = earliest
        if earliest < 1:
            earliest = int(
                math.ceil(time.mktime((datetime.datetime.now() - datetime.timedelta(days=int(opt_hist_days))).timetuple())))
            last_poll_timestamp = earliest
        else:
            # polling for buffer time: twice the poll interval or 2 hours (whichever is greater)
            if (opt_interval * 2) > opt_buffer_time:
                earliest = (earliest - (opt_interval * 2))
            else:
                earliest = earliest - opt_buffer_time
            helper.log_info(f"buffer time for polling is {earliest}")
        cyb_client = CybereasonClient(helper,ew, opt_base_url, opt_cybereason_account, opt_authentication_type,proxy_settings)
        if opt_malops:
            malops = cyb_client.get_time_bound_malops(ew, earliest=earliest, latest=int(now), sensor_group_name=opt_sensor_group_names, malop_status=opt_malop_status)
            sourcetype = "cybereason:api"
            data = json.dumps(malops)
            event = helper.new_event(host=opt_base_url.split(":")[0], source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
            ew.write_event(event)
        if opt_suspicious_objects:
            suspicious = cyb_client.get_time_bound_suspicious(requested_type="Process",earliest=earliest, latest=int(now))
            sourcetype = "cybereason:api"
            data = json.dumps(suspicious)
            event = helper.new_event(host=opt_base_url.split(":")[0], source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
            ew.write_event(event)
        if opt_malware:
            malware = cyb_client.get_all_malware(starttime=earliest, limit=1000)
            sourcetype = "cybereason:api"
            data = json.dumps(malware)
            event = helper.new_event(host=opt_base_url.split(":")[0], source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
            ew.write_event(event)
        if opt_pull_comments:
            if last_poll_timestamp > 1:
                pull_comments = cyb_client.pull_latest_comments(earliest=last_poll_timestamp, latest=int(now), sensor_group_name=opt_sensor_group_names)
                helper.log_debug("pull_latest_comments ran successfully {}".format(pull_comments))
                sourcetype = "cybereason:api"
                data = json.dumps(pull_comments)
                event = helper.new_event(host=opt_base_url.split(":")[0], source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
                ew.write_event(event)
        set_last_polled_timestamp(opt_base_url,opt_username, now)
    except Exception as e:
        sourcetype = "CybereasonAddonForSplunk:error"
        data = str(e)
        event = helper.new_event(
            host=opt_base_url.split(":")[0] if opt_base_url and len(opt_base_url) > 0 else "host",
            source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
        ew.write_event(event)
   
    

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''
