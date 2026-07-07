# encoding = utf-8

import os
import sys
import re
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
    
    input_type = 'userinfo'
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

    helper.log_debug(f'{product} - {input_type} - requesting access token')

    auth_obj = AuthenticateMOVEit(helper,product,server_address,opt_username,opt_password)
    
    # fetching access token
    acc_token = auth_obj.SendRequest()

    if(acc_token!=''):

        asset_types = ['users','groups']

        # single timestamp for all asset values
        dateTimeObj = datetime.now()
        timestamp_now = dateTimeObj.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

        for asset_type in asset_types:
            
            helper.log_debug(f'{product} - {input_type} - {asset_type} - sending command to get list')

            
            # if its group, iterate through each group and get group member information.
            if asset_type == 'groups':
                
                group_list = get_list.GetList(helper,server_address,asset_type,acc_token)
                WriteAssetList(helper,ew,server_address,asset_type,group_list,None,acc_token,product,input_type,timestamp_now)
                
                if group_list:
                    
                    helper.log_debug(f'{product} - {input_type} - {asset_type} - groups list - {group_list}')
                    
                    for group in group_list:
                        gid = group['id']
                        
                        end_point = f'groups/{gid}/members'
                        # fetch lists
                        asset_list = get_list.GetList(helper,server_address,end_point,acc_token)
                        WriteAssetList(helper,ew,server_address,end_point,asset_list,gid,acc_token,product,input_type,timestamp_now)

            else:
                # fetch lists
                asset_list = get_list.GetList(helper,server_address,asset_type,acc_token)
                WriteAssetList(helper,ew,server_address,asset_type,asset_list,None,acc_token,product,input_type,timestamp_now)
                


    else:
        helper.log_error(f'{product} - {input_type} - Empty access token retrieved')
        
    helper.log_debug(f'{product} - {input_type} - End')
    
    
def WriteAssetList(helper,ew,server_address,asset_type,asset_list,gid,acc_token,product,input_type,timestamp_now):
                    

    if asset_list:
                
        helper.log_debug(f'{product} - {input_type} - {asset_type} - event list - {asset_list}')

        # get splunk configuration variables
        idx = helper.get_output_index()
        s_type = helper.get_sourcetype()

        helper.log_debug(f'{product} - {input_type} - {asset_type} - adding data to index - {idx}. sourcetype - {s_type}')

        # processing each event in the list and writing to the index

        for asset in asset_list:

            helper.log_debug(f'{product} - {input_type} - {asset_type} - event - {asset}')
                    
            asset['timestamp'] =  timestamp_now
            asset['Topic'] = input_type
            
            # if there is a group id, it means that this is an event which carries member information for a group
            if gid:
                asset['Type'] = 'group_members'
                asset['gid'] = f'{gid}'
            else:
                asset['Type'] = f'{asset_type}'

            try:
                event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type, data=json.dumps(asset))
                ew.write_event(event)
                helper.log_debug(f'{product} - {input_type} - {asset_type} - Writing {asset_type} event to index {idx} and sourcetype {s_type} - success')

            except Exception as e:
                helper.log_error(f'{product} - {input_type} - {asset_type} - error on parse event. Error: {e}')

    else:
        helper.log_debug(f'{product} - {input_type} - {asset_type} - Empty event retrieved')
    
    

