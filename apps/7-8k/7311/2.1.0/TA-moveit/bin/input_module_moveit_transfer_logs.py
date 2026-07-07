# encoding = utf-8

import os
import sys
import json
import urllib.parse

from datetime import datetime
from datetime import timedelta

from moveit_authenticate import AuthenticateMOVEit
import send_request

# uncomment to debug
'''
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
'''

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    # uncomment to debug
    '''
    dbg.set_breakpoint()
    helper.set_log_level("debug")
    '''
    
    product = 'MFT'
    input_type = 'logs'
    
    helper.log_debug(f'{product} - {input_type} - Start')

    # collecting credential parameters from the global settings

    global_account = helper.get_arg('global_account')
    opt_username = global_account['username']
    opt_password= global_account['password']

    # fetching MOVEit server URL from the settings

    server_address = helper.get_global_setting('moveit_transfer_url') # eg "https://192.168.50.160:443"
    
    helper.log_debug(f'{product} - {input_type} - requesting access token')
    
    auth_obj = AuthenticateMOVEit(helper,product,server_address,opt_username,opt_password)
    
    # fetching access token
    acc_token = auth_obj.SendRequest()

    if(acc_token!=''):
        report_type = input_type
        report_topic = input_type
        
        # name of the KV store log entry
        timestamp_checkpoint_key = f'ta_moveit_transfer_{report_type}_last_timastamp'

        # retrieve the last saved timestamp from KV store
        last_saved_timestamp = helper.get_check_point(f'{timestamp_checkpoint_key}')
        
        # if no timestamp can be found (e.g. scripts 1st run)
        if not last_saved_timestamp:
            dateTimeObj = datetime.now()
            timestamp_now = dateTimeObj.strftime("%Y-%m-%dT%H:%M:%S")
            last_saved_timestamp = timestamp_now
            helper.save_check_point(f'{timestamp_checkpoint_key}', last_saved_timestamp)
        else:
            ## add 1 second to timestamp to avoid ovelapping events
            datetime_object_conv = datetime.strptime(last_saved_timestamp, "%Y-%m-%dT%H:%M:%S")
            tdelta = timedelta(seconds=1)
            new_datetime_object_conv = datetime_object_conv + tdelta
            last_saved_timestamp = new_datetime_object_conv.strftime("%Y-%m-%dT%H:%M:%S")
            helper.save_check_point(f'{timestamp_checkpoint_key}', last_saved_timestamp)

            
        helper.log_debug(f'{product} - {input_type} - {report_type} - querying events stating from {last_saved_timestamp}')
        
        # url encode the timestamp
        last_saved_timestamp_url_enc = urllib.parse.quote_plus(last_saved_timestamp)
            
        report_list_url = f'{server_address}/api/v1/{report_type}?startDateTime={last_saved_timestamp_url_enc}&suppressSigns=false'
        
        payld = None

        # fetch lists
        r_status,response = send_request.SendRequest(helper,report_type,acc_token,report_list_url,"GET",payld)

        if r_status == 200:
            
            # the items key has all the info

            log_record_list = response.json()['items']

            helper.log_debug(f'{product} - {input_type} - {report_type} - items - {log_record_list}')
            helper.log_debug(f'{product} - {input_type} - {report_type} - items retrieve - success')

        if log_record_list is None:

            helper.log_debug(f'{product} - {input_type} - {report_type} - items retrieve - empty')
            return

        idx = helper.get_output_index()
        s_type = helper.get_sourcetype()

        for log_record in log_record_list:
            
             # get splunk configuration variables

            helper.log_debug(f'{product} - {input_type} - {report_type} - adding data to index - {idx}. sourcetype - {s_type}')

            # processing each event in the list and writing to the index

            log_record_time = log_record['logTime']
            
            log_record['timestamp'] = log_record_time
            log_record['Topic'] = report_topic
            log_record['Type'] = f'{report_type}'

            try:
                event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type, data=json.dumps(log_record))
                ew.write_event(event)
                helper.save_check_point(f'{timestamp_checkpoint_key}',log_record_time)
                helper.log_debug(f'{product} - {input_type} - {report_type} - writing event to index {idx} and sourcetype {s_type} - success')

            except Exception as e:
                helper.log_error(f'{product} - {input_type} - {report_type} - error on parse event. error : {e}')
                
    else:

        helper.log_error(f'{product} - {input_type} - empty access token retrieved')

    helper.log_debug(f'{product} - {input_type} - End')





