# encoding = utf-8

import os
import sys
import json
from datetime import datetime

from moveit_authenticate import AuthenticateMOVEit
import get_list

# uncomment to debug
'''
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
'''

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    input_type = 'filestorage'
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

    # fetching MOVEit server URL from the settings

    server_address = helper.get_global_setting('moveit_transfer_url') # eg "https://192.168.50.160:443"

    auth_obj = AuthenticateMOVEit(helper,product,server_address,opt_username,opt_password)
    
    # fetching access token
    acc_token = auth_obj.SendRequest()

    if(acc_token!=''):

        asset_types = ['files','folders','packages']
        
        # single timestamp for all asset values
        # otherwise hardtime with getting a snapshot in all assets in a single dashboard
        dateTimeObj = datetime.now()
        timestamp_now = dateTimeObj.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

        for asset_type in asset_types:
            
            helper.log_debug(f'{product} - {input_type} - {asset_type} - sending command to get list')
            
            # fetch lists
            asset_list = get_list.GetList(helper,server_address,asset_type,acc_token)

            if asset_list:

                # get splunk configuration variables

                idx = helper.get_output_index()
                s_type = helper.get_sourcetype()
                
                helper.log_debug(f'{product} - {input_type} - {asset_type} - event list : {asset_list}')

                helper.log_debug(f'{product} - {input_type} - {asset_type} - adding data to index - {idx}. sourcetype - {s_type}')


                # processing each event in the list and writing to the index

                for asset in asset_list:

                    helper.log_debug(f'{product} - {input_type} - {asset_type} - event : {asset}')

                    asset['timestamp'] =  timestamp_now
                    asset['Topic'] = input_type
                    asset['Type'] = f'{asset_type}'

                    try:

                        event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type, data=json.dumps(asset))
                        ew.write_event(event)
                        helper.log_debug(f'{product} - {input_type} - {asset_type} - writing event to index {idx} and sourcetype {s_type} - success')

                    except Exception as e:
                        helper.log_error(f'{product} - {input_type} - {asset_type} - error on parse event. error : {e}')

                    

            else:

                helper.log_debug(f'{product} - {input_type} - {asset_type} - empty list retrieved')

    else:

        helper.log_error(f'{product} - {input_type} - {asset_type} - empty access token retrieved')
    
    helper.log_debug(f'{product} - {input_type} - End')























