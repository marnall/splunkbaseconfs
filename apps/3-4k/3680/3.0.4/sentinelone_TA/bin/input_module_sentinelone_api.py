
# encoding = utf-8

import os
import platform
import sys
import time
import json, operator
from datetime import datetime
from datetime import timedelta
import re
import getpass

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
    # console = definition.parameters.get('console', None)
    # s1_domain = definition.parameters.get('s1_domain', None)
    # api_token = definition.parameters.get('api_token', None)
    # api_channels = definition.parameters.get('api_channels', None)
    # start_checkpoint = definition.parameters.get('start_checkpoint', None)
    # ssl_check = definition.parameters.get('ssl_check', None)
    pass

def collect_events(helper, ew):
    """ Get inputs from user """
    app_name = helper.get_app_name()
    input_name = helper.get_input_stanza_names()
    api_url_path = helper.get_arg('api_url_path')
    api_version = helper.get_arg('api_version')
    http_method = 'GET'
    protocol = "https"
    opt_console_name = helper.get_arg('console_name')
    opt_api_token = helper.get_arg('api_token')
    opt_api_channels = helper.get_arg('api_channels')
    opt_ssl_check = helper.get_arg('ssl_check')
    opt_subdomain = helper.get_arg('subdomain')
    opt_s1_domain = helper.get_arg('s1_domain')
    initial_cp = helper.get_arg('start_checkpoint')
    proxy_settings = helper.get_proxy()
    full_input_name = helper.get_input_type() + "://" + input_name
    console_fqdn = opt_subdomain + "." + opt_s1_domain
    checkpoint_dir = os.path.join(os.environ['SPLUNK_DB'],'modinputs')
        
    """ Check SSL and Time Stamp inputs """
    if opt_ssl_check is True:
        ssl_check = True
    else:
        ssl_check = False
    
    if proxy_settings is not None:
        use_proxy = True
    else:
        use_proxy = False
        
    if initial_cp == "now":
        nowGMT = time.gmtime()
        initial_cp = time.strftime("%s000", nowGMT)
    
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)

    """ Function to convert createdAt time field to epoch timestamp in milliseconds. """
    def time_convert(time_field):
        if len(time_field) == 27:
            utc_time = datetime.strptime(time_field, '%Y-%m-%dT%H:%M:%S.%fZ')
        elif len(time_field) == 20:
            utc_time = datetime.strptime(time_field, '%Y-%m-%dT%H:%M:%SZ')
        else:
            msg = "Time value: '" + time_field + "'is in unknown format!"
            helper.log_critical(msg)
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
        epoch_time = str.split(str(repr(epoch_time)), ".")
        if len(epoch_time[1]) == 2:
            epoch_time[1] = epoch_time[1] + '0'
        elif len(epoch_time[1]) == 1:
            epoch_time[1] = epoch_time[1] + '00'
        epoch_milliseconds = epoch_time[0] + epoch_time[1]
        return epoch_milliseconds
    
    """ This function writes current checkpoint to checkpoint file.
        Log exception for failure and stop script execution.
    """
    def write_cp(checkpoint_file, current_cp):
        try:
            with open(checkpoint_file, 'w') as cp_out_file:
                current_cp = str(current_cp)
                cp_out_file.write(current_cp)
        except Exception as exception:
            msg = "Failed to write the checkpoint file {}. Running as user: {}. Exception: {}".format(checkpoint_file, getpass.getuser(), repr(exception))
            helper.log_critical(msg)
            sys.exit(msg)
    
    """
        Function to Set/Retrieve latest saved/available checkpoint
    """
    def set_latest_cp(checkpoint_file, initial_cp):
        try:
            if not os.path.exists(checkpoint_file):
                with open(checkpoint_file, 'a'):
                    os.utime(checkpoint_file, None)
            """ Get checkpoint file size. If file size is zero use user input """
            file_size = os.path.getsize(checkpoint_file)
            if file_size == 0:
                latest_cp = str(initial_cp)
                write_cp(checkpoint_file, latest_cp)
            elif file_size != 0:
                with open(checkpoint_file, 'r') as lcp_input_file:
                    lcp_input_file.seek(0)
                    lcp_line = lcp_input_file.readline()
                    latest_cp = lcp_line
        except Exception as exception:
            msg = "Failed to create/read/write the checkpoint file {}. Running as user: {}. Exception: {}".format(checkpoint_file, getpass.getuser(), repr(exception))
            helper.log_critical(msg)
            sys.exit(msg)
        return latest_cp
            
    """ Create checkpoint_dir.
        Log exception for failure and stop script execution.
    """
    try:
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
    except Exception as exception:
        msg = "Failed to create checkpoint directory {}. Running as user: {}. Exception: {}".format(checkpoint_dir, getpass.getuser(), repr(exception))
        helper.log_critical(msg)
        sys.exit(msg)

    """ Iterate on API Channels chosen by user """
    for api_channel in opt_api_channels:
        checkpoint_file = os.path.join(checkpoint_dir,app_name + "_" + input_name + "_" + api_channel)
        
        latest_cp = set_latest_cp(checkpoint_file, initial_cp)
            
        """
        Set relevant API query parameter by api_channel
        
        Query by timestamp currently is not supported by API for groups and policies endpoints
            
        """
        if api_channel == "threats":
            payload_param = dict(updated_at__gt=latest_cp)
        elif api_channel == "activities":
            payload_param = dict(created_at__gt=latest_cp)
        elif api_channel == "agents":
            payload_param = dict(last_active_date__gt=latest_cp)
        else:
            payload_param = None
        
        """ Set main URL by API Endpoint """
        url = protocol + "://" + console_fqdn + "/" + api_url_path + "/" + api_version + "/" + api_channel
        
        """ Query the API according to query parameters """
        try:
            helper.log_debug(api_channel + " data download start!")
            if payload_param is None:
                response = helper.send_http_request(url, method=http_method, headers={'Authorization': 'APIToken ' + opt_api_token, 'Content-Type': 'application/json'}, verify=ssl_check, use_proxy=use_proxy)
            else:
                response = helper.send_http_request(url, method=http_method, headers={'Authorization': 'APIToken ' + opt_api_token, 'Content-Type': 'application/json'}, verify=ssl_check, parameters=payload_param, use_proxy=use_proxy)
                response.raise_for_status()
            helper.log_debug(api_channel + " data download end!")
        except Exception as exception:
            msg = 'Failed to download data from {}. Error: {}.'.format(url, repr(exception))
            helper.log_critical(msg)
            sys.exit(msg)
        
        helper.log_debug(api_channel + " data processing start!")
        try:
            """ Set current_cp to None """
            current_cp = None
            
            """ Parse API response to JSON data """
            json_data = json.loads(response.text)
            
            if api_channel == "threats":
                json_data = sorted(json_data, key=lambda x: (x['meta_data']['updated_at']))
            if api_channel == "activities":
                json_data = sorted(json_data, key=lambda x: (x['meta_data']['created_at']))
            if api_channel == "agents":
                json_data = sorted(json_data, key=lambda x: (x['last_active_date']))
            if api_channel == "groups":
                json_data = sorted(json_data, key=lambda x: (x['meta_data']['updated_at']))
            if api_channel == "policies":
                json_data = sorted(json_data, key=lambda x: (x['meta_data']['updated_at']))
            
            if type(json_data) is dict:
                json_data = [json_data]
            
            """ Iterate over Response and turn each entry to Splunk event """
            for entry in json_data:
                entry['console'] = input_name
                entry['subdomain'] = opt_subdomain
                entry['meta_st'] = api_channel
                
                """ Turn the relevant time field to unified time_field for each entry according to API Endpoint specification """
                meta_data = entry['meta_data']
                if api_channel in "threats" "policies" "groups":
                    time_field = meta_data['updated_at']
                    entry['adatetime'] = meta_data['updated_at']
                if api_channel in "policies" "groups":
                    entry['s1source'] = entry['source']
                    del entry['source']
                if api_channel == "activities":
                    time_field = meta_data['created_at']
                    entry['adatetime'] = meta_data['created_at']
                if api_channel == "agents":
                    time_field = entry['last_active_date']
                    entry['adatetime'] = entry['last_active_date']
                    

                
                """ 
                Convert the API Endpoint name from plural to singular
                to support old versions of saved searches and dashboards
                """
                if api_channel[-3:] == 'ies':
                    s1sourcetype = api_channel[:-3:] + 'y'
                else:
                    s1sourcetype = api_channel[:-1]
                    
                """ Convert the time_field to an epoch time """
                current_cp = time_convert(time_field)
                if current_cp>latest_cp:
                    """ Dump each event into JSON """
                    entry = json.dumps(entry, sort_keys=True)
                    """ Write events to index with provided API Host as host and sourcetype customized per collected report """
                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=s1sourcetype, host=console_fqdn, data=entry)
                    ew.write_event(event)
                else:
                    continue
        except Exception as exception:
            msg = "Failure: {} for api_channel: {}".format(repr(exception), api_channel)
            helper.log_critical(msg)
            sys.exit(msg)
            
        """ Write the latest checkpoint value to the file """
        if current_cp is not None:
            write_cp(checkpoint_file, current_cp)
        helper.log_debug(api_channel + " data processing end!")