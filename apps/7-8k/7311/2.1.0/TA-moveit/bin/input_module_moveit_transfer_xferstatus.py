# encoding = utf-8

import os
import sys
import json
import time

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
    
    input_type = 'xferstatus'
    product = 'MFT'

    # uncomment to debug
    '''
    dbg.set_breakpoint()
    helper.set_log_level("debug")
    '''
    
    helper.log_debug(f'{product} - {input_type} - Start')

    # collecting credential parameters from the global settings

    global_account = helper.get_arg('global_account')
    opt_username = global_account['username']
    opt_password= global_account['password']
    opt_audit= helper.get_arg('audit_reports')

    # fetching MOVEit server URL from the settings

    server_address = helper.get_global_setting('moveit_transfer_url') # eg "https://192.168.50.160:443"

    helper.log_debug(f'{product} - {input_type} - requesting access token')
    
    auth_obj = AuthenticateMOVEit(helper,product,server_address,opt_username,opt_password)
    
    # fetching access token
    acc_token = auth_obj.SendRequest()

    # latest logstamp of the event list

    logstamp_l = ''

    if(acc_token!=''):

        report_types_list = [{'report_type':'xferstatus','time_field':'timeStarted'}]

        for report_info in report_types_list:

            report_type = report_info['report_type']
            time_field = report_info['time_field']
            
            helper.log_debug(f'{product} - {input_type} - {report_type} - requesting report')

            # fetch task report
            reports_list = RequestReports(helper,server_address,time_field,acc_token,product,input_type,report_type)

            if reports_list:
                
                helper.log_debug(f'{product} - {input_type} - {report_type} - event list - {reports_list}')

                # get splunk configuration variables
                idx = helper.get_output_index()
                s_type = helper.get_sourcetype()

                helper.log_debug(f'{product} - {input_type} - {report_type} - adding data to index - {idx}. sourcetype - {s_type}')

                # processing each event in the list and writing to the index

                for report in reports_list:

                    helper.log_debug(f'{product} - {input_type} - {report_type} - event- {report}')

                    report['Topic'] = input_type
                    report['Type'] = f'{report_type}'

                    # recording the logstamp. 

                    logstamp_l = report[f'{time_field}']

                    helper.log_debug(f'{product} - {input_type} - {report_type} - timestamp: {logstamp_l}')
                    
                    report['timestamp'] = logstamp_l

                    try:
                        event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type,time=None,data=json.dumps(report))
                        ew.write_event(event)
                        helper.log_debug(f'{product} - {input_type} - {report_type} - writing event to index {idx} and sourcetype {s_type} - success')

                    except Exception as e:
                        helper.log_error(f'{product} - {input_type} - {report_type} - error on parse event. Error: {e}')

            else:
                helper.log_debug(f'{product} - {input_type} - {report_type} - empty report retrieved')

    else:
        helper.log_error(f'{product} - {input_type} - empty access token retrieved')

    helper.log_debug(f'{product} - {input_type} - End')

def RequestReports(helper,server_address,time_field,token,product,input_type,report_type):

    helper.log_debug(f'{product} - {input_type} - {report_type} - initiating report retrieve')

    #helper.delete_check_point('ta_moveit_task_report_last_timastamp')

    # getting the latest recorded timestamp from kv store
    
    timestamp_checkpoint = f'ta_moveit_transfer_{report_type}_last_timastamp'

    last_saved_timestamp = helper.get_check_point(f'{timestamp_checkpoint}')
    
    helper.log_debug(f'{product} - {input_type} - {report_type} - {timestamp_checkpoint} retrieve. value : {last_saved_timestamp}')

    # if no presaved timestamp, fetch transfers for last 60 minutes
    t_diff = 60
    
    if last_saved_timestamp:
        dateTimeStart = int(time.time())
        t_diff = (dateTimeStart - last_saved_timestamp)
        if t_diff > 3600:
            t_diff = 3600

    helper.log_debug(f'{product} - {input_type} - {report_type} - t_diff : {t_diff}')
    
    report_url = f'{server_address}/api/v1/{report_type}?recentlyCompletedPeriod={t_diff}'

    # if no timestamp can be found (e.g. scripts 1st run)

    payld = None
    
    # no matter the response, if there is no timestamp checkpoint in kv, program will save a checkpoint
    if not last_saved_timestamp:
        dateTimeNow = int(time.time())
        helper.save_check_point(f'{timestamp_checkpoint}', dateTimeNow)
        helper.log_debug(f'{product} - {input_type} - {report_type} - {timestamp_checkpoint} saved. value : {dateTimeNow}')
        
    r_status,response = send_request.SendRequest(helper,report_type,token,report_url,"GET",payld)
    
    helper.log_debug(f'{product} - {input_type} - {report_type} - r_status : {r_status}')
    helper.log_debug(f'{product} - {input_type} - {report_type} - response : {response}')
    
    if r_status == 200:
        xfer_list = response.json()['items']
        helper.log_debug(f'{product} - {input_type} - {report_type} - report retrieve - success')
        
        dateTimeNow = int(time.time())
        helper.save_check_point(f'{timestamp_checkpoint}', dateTimeNow)
        helper.log_debug(f'{product} - {input_type} - {report_type} - {timestamp_checkpoint} saved. value : {dateTimeNow}')
        
        return xfer_list
        
    else:
        raise ValueError(r_status)
    
    
    
    
    
    
