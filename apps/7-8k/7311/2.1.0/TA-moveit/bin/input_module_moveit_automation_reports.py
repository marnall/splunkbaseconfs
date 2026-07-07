# encoding = utf-8

import os
import sys
import json
from datetime import datetime

from moveit_authenticate import AuthenticateMOVEit
import send_request

# uncomment to debug
'''
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
'''

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    input_type = 'report'
    product = 'MA'

    # uncomment to debug
    '''
    dbg.enable_debugging(timeout=25)
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

    server_address = helper.get_global_setting('moveit_automation_url') # eg "https://192.168.50.160:443"

    helper.log_debug(f'{product} - {input_type} - requesting access token')

    auth_obj = AuthenticateMOVEit(helper,product,server_address,opt_username,opt_password)
    
    # fetching access token
    acc_token = auth_obj.SendRequest()

    # latest logstamp of the event list

    logstamp_l = ''

    if(acc_token!=''):

        report_types_list = [{'report_type':'taskruns','record_id':'RunID','time_field':'LogStamp'},{'report_type':'fileactivity','record_id':'LogID','time_field':'LogStamp'}]
        
        if opt_audit:
            report_types_list.append({'report_type':'audit','record_id':'LogID','time_field':'LogTime'})

        for report_info in report_types_list:

            report_type = report_info['report_type']
            id_type = report_info['record_id']
            time_field = report_info['time_field']
            
            timestamp_checkpoint = f'ta_moveit_{product}_{input_type}_{report_type}_last_timastamp'
            log_id_checkpoint = f'ta_moveit_{product}_{input_type}_{report_type}_last_id'
            
            helper.log_debug(f'{product} - {input_type} - {report_type} - requesting report')

            # fetch task report
            reports_list = RequestReports(helper,server_address,product,input_type,report_type,id_type,time_field,acc_token,timestamp_checkpoint,log_id_checkpoint)

            
            if reports_list:

                # get splunk configuration variables

                idx = helper.get_output_index()
                s_type = helper.get_sourcetype()
                
                helper.log_debug(f'{product} - {input_type} - {report_type} - event list: {reports_list}')

                helper.log_debug(f'{product} - {input_type} - {report_type} - adding data to index - {idx}. sourcetype - {s_type}')

                # processing each event in the list and writing to the index

                for report in reports_list:

                    helper.log_debug(f'{product} - {input_type} - {report_type} - event : {report}')
                    
                    report['Topic'] = f'{input_type}'
                    report['Type'] = f'{report_type}'

                    # recording the logstamp. 
                    logstamp_l = report[f'{time_field}']
                    
                    report['timestamp'] = logstamp_l

                    run_id = report[f'{id_type}']

                    try:

                        event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type,time=None,data=json.dumps(report))
                        ew.write_event(event)
                        # writng the latest log stamp to the KV store as a check point
                        helper.save_check_point(f'{log_id_checkpoint}', run_id)
                        helper.log_debug(f'{product} - {input_type} - {report_type} - {run_id} - writing event to index {idx} and sourcetype {s_type} - success')

                    except Exception as e:
                        helper.log_error(f'{product} - {input_type} - {report_type} - error on parse event. {e}')

            else:
                helper.log_debug(f'{product} - {input_type} - {report_type} - empty event retrieved')

    else:

        helper.log_error(f'{product} - {input_type} - {report_type} - empty access token retrieved')
        
    helper.log_debug(f'{product} - {input_type} - End')
 

def RequestReports(helper,server_address, product, input_type, report_type,id_type,time_field,token,timestamp_checkpoint,log_id_checkpoint):

    helper.log_debug(f'{product} - {input_type} - {report_type} - starting report retrieve')
    
    report_url = f'{server_address}/api/v1/reports/{report_type}'
    
    #helper.delete_check_point(f'{timestamp_checkpoint}')
    #helper.delete_check_point(f'{log_id_checkpoint}')
    # getting the latest recorded timestamp from kv store

    last_saved_timestamp = helper.get_check_point(f'{timestamp_checkpoint}')
    helper.log_debug(f'{product} - {input_type} - {report_type} - last_saved_timestamp : {last_saved_timestamp}')
    
    last_saved_runid = helper.get_check_point(f'{log_id_checkpoint}')
    helper.log_debug(f'{product} - {input_type} - {report_type} - last_saved_runid : {last_saved_runid}')

    # if no timestamp can be found (e.g. scripts 1st run)

    if not last_saved_timestamp:
        dateTimeObj = datetime.now()
        timestamp_now = dateTimeObj.strftime("%Y-%m-%dT%H:%M:%S.%f")
        last_saved_timestamp = timestamp_now[:-3]
        helper.save_check_point(f'{timestamp_checkpoint}',last_saved_timestamp)
        helper.log_debug(f'{product} - {input_type} - last_saved_timestamp : {last_saved_timestamp}')

    if not last_saved_runid:
        # if there is no last saved id try to pull events which was generated since the input has started.
        # after atleast 1 event has been pulled, shift to logid to be the predicated instead of the timestamp.
        # fetch all succeeded/failed report entries after last_saved_timestamp. max event count will be 1000
        payld = {'predicate': time_field + '>' + '\"'+ last_saved_timestamp +'\"','orderBy': id_type ,'maxCount':1000}

    else:
        payld = {'predicate': id_type +'>'+str(last_saved_runid),'orderBy': id_type ,'maxCount':1000}

    # fetch lists
    r_status,response = send_request.SendRequest(helper,report_type,token,report_url,"POST",payld)


    if r_status == 200:
        report_list = response.json()['items']
        helper.log_debug(f'{product} - {input_type} - {report_type} - report list {report_list}')
        helper.log_debug(f'{product} - {input_type} - {report_type} - report list retrieve - success')

    if report_list is None:
        helper.log_debug(f'{product} - {input_type} - {report_type} - report list retrieve - empty')
        
    return report_list

    

    

    