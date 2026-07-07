# encoding = utf-8

import os
import sys
import time
import json
from datetime import datetime

from moveit_authenticate import AuthenticateMOVEit
import send_request
import csv_reformat


# uncomment to debug
'''
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
'''

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    input_type = 'reports'
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
    opt_report_names = helper.get_arg('report_names')

    # fetching MOVEit server URL from the settings

    server_address = helper.get_global_setting('moveit_transfer_url') # eg "https://192.168.50.160:443"

    helper.log_debug(f'{product} - {input_type} - requesting access token')
    
    auth_obj = AuthenticateMOVEit(helper,product,server_address,opt_username,opt_password)
    
    # fetching access token
    acc_token = auth_obj.SendRequest()

    if(acc_token!=''):

        report_type = input_type
        report_topic = input_type
        
        report_list_url = f'{server_address}/api/v1/{report_type}'
        
        payld = None
        
        helper.log_debug(f'{product} - {input_type} - {report_type} - requesting report details')

        # fetch lists
        r_status,response = send_request.SendRequest(helper,report_type,acc_token,report_list_url,"GET",payld)

        if r_status == 200:
            report_list = response.json()['items']
            helper.log_debug(f'{product} - {input_type} - {report_type} report list {report_list}')
            helper.log_debug(f'{product} - {input_type} - {report_type} report list retrieve - success')


        if report_list is None:
            helper.log_debug(f'{product} - {input_type} - {report_type} report list retrieve - empty')
            return
        
        opt_report_names_list = opt_report_names.split(",")
        
        # single timestamp for all asset values
        # otherwise hardtime with getting a snapshot in all assets in a single dashboard
        dateTimeObj = datetime.now()
        timestamp_now = dateTimeObj.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        
        for report in report_list:
        
            for report_name in opt_report_names_list:
                
                if report['title'] == report_name:
                    
                    report_id = report['id']

                    report_url = f'{server_address}/api/v1/{report_type}/{report_id}/results/download'

                    payld = None
                    
                    helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - requesting report')

                    # fetch lists
                    r_status,response = send_request.SendRequest(helper,report_type,acc_token,report_url,"GET",payld)

            
                    if r_status == 200:

                        csvt = response.text
                        helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - csv response: {csvt}')

                        report_rows = csv_reformat.CSVtoDict(csvt)
                        helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - report retrieve - success')

                    else:

                        helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - report retrieve - fail')
                        raise ValueError(r_status)

                    if report_rows:
                        
                        helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - report row: {report_rows}')

                        # get splunk configuration variables

                        idx = helper.get_output_index()
                        s_type = helper.get_sourcetype()

                        helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - adding data to index - {idx}. sourcetype - {s_type}')

                        # processing each event in the list and writing to the index

                        for report_row in report_rows:

                            helper.log_debug(report_row)

                            report_row['timestamp'] =  timestamp_now
                            report_row['Topic'] = report_topic
                            report_row['Type'] = f'{report_type}'
                            report_row['ReportName'] = report_name

                            try:

                                event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type, data=json.dumps(report_row))
                                ew.write_event(event)
                                helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - writing event to index {idx} and sourcetype {s_type} - success')

                            except Exception as e:

                                helper.log_error('{product} - {input_type} - {report_type} - {report_name} - error on parse event. ' + str(e))
                                
                    else:
                        helper.log_debug(f'{product} - {input_type} - {report_type} - {report_name} - empty list retrieved')
                        
                    # break the loop. no need to search anymore
                    break

    else:
        helper.log_error(f'{product} - {input_type} - empty access token retrieved')

    
    helper.log_debug(f'{product} - {input_type} - End')

