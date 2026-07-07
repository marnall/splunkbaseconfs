# encoding = utf-8

import os
import sys
import re
import json
from collections import OrderedDict
from datetime import datetime

from moveit_authenticate import AuthenticateMOVEit
import get_list

# uncomment to debug
'''
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
'''

source_list= []
dest_list = []

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    input_type = 'asset'
    product = 'MA'

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
    server_address = helper.get_global_setting('moveit_automation_url') # eg "https://192.168.50.160:443"

    auth_obj = AuthenticateMOVEit(helper,product,server_address,opt_username,opt_password)
    
    # fetching access token
    acc_token = auth_obj.SendRequest()
    
    if(acc_token!=''):

        asset_types = ['sshkeys','sslcerts','pgpkeys','tasks','hosts']
        
        # single timestamp for all asset values
        # otherwise hardtime with getting a snapshot in all assets in a single dashboard
        dateTimeObj = datetime.now()
        timestamp_now = dateTimeObj.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

        for asset_type in asset_types:
            
            helper.log_debug(f'{product} - {input_type} - Processing asset type: {asset_type}')
            
            helper.log_debug(f'{product} - {input_type} - {asset_type} - Sending get list request')

            # fetch lists
            asset_list = get_list.GetList(helper,server_address,asset_type,acc_token)
            
            helper.log_debug(f'{product} - {input_type} - {asset_type} - asset_list : {asset_list}')

            if asset_list:

                # get splunk configuration variables
                idx = helper.get_output_index()
                s_type = helper.get_sourcetype()

                helper.log_debug(f'{product} - {input_type} - {asset_type} - adding data to index - {idx}. sourcetype - {s_type}')

                # processing each event in the list and writing to the index

                for asset in asset_list:

                    helper.log_debug(f'{product} - {input_type} - {asset_type} - event : {asset}')
                    
                    # for hosts injest additional fields, extracting from the existing event
                    if(asset_type=='hosts'):
                        for key in asset:
                            host_type = key.split(".")
                            if host_type[0]:
                                asset['HostType'] = host_type[0]
                                keyID = f'{host_type[0]}.ID'
                                keyName = f'{host_type[0]}.Name'
                                keyIsUsed = f'{host_type[0]}.IsUsed'
                                if asset[f'{host_type[0]}']['ID']:
                                    asset['ID'] = asset[f'{host_type[0]}']['ID']
                                if asset[f'{host_type[0]}']['Name']:
                                    asset['Name'] =  asset[f'{host_type[0]}']['Name']
                                if asset[f'{host_type[0]}']['IsUsed']:
                                    asset['IsUsed'] = asset[f'{host_type[0]}']['IsUsed']
                                if not asset[f'{host_type[0]}']['IsUsed']:
                                    asset['IsUsed'] = False
                                break
                    
                    if(asset_type=='tasks'):
                        step_dict = asset['steps']
                        source_list.clear()
                        dest_list.clear()
                        find_hosts(step_dict)
                        source_list_local = list(OrderedDict.fromkeys(source_list))
                        dest_list_local = list(OrderedDict.fromkeys(dest_list))
                        host_list_local = source_list_local + dest_list_local
                        asset['HostsSources'] = source_list_local
                        asset['HostsDestinations'] = dest_list_local
                        asset['Hosts'] = list(OrderedDict.fromkeys(host_list_local))

                    asset['timestamp'] =  timestamp_now
                    asset['Topic'] = 'asset'

                    asset['Type'] = f'{asset_type}'


                    try:
                        helper.log_debug(f'{product} - {input_type} - {asset_type} - event : {asset}')

                        #event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type, time=timestamp_now, data=json.dumps(asset))
                        event = helper.new_event(source=helper.get_input_type(),index=idx, sourcetype=s_type, data=json.dumps(asset))
                        ew.write_event(event)
                        helper.log_debug(f'{product} - {input_type} - {asset_type} - writing event to index {idx} and sourcetype {s_type} - success')

                    except Exception as e:
                        helper.log_error('error on parse event. ' + str(e))

            else:
                helper.log_debug(f'{product} - {input_type} - {asset_type} - empty {asset_type} list retrieved')

    else:

        helper.log_error(f'{product} - {input_type} - {asset_type} - empty access token retrieved')
    
    helper.log_debug(f'{product} - {input_type} - End')

# iterate if its a list
def find_hosts(step_dict):
    if step_dict:
        for step in step_dict:
            find_in_dict(step)

# iterate if its a dictionary
def find_in_dict(step):
    if step:
        for key in step:
            value=step[key]
            
            if key== "Source" and value:
                source_list.append(value['HostID'])
            elif key == "Destination" and value:
                dest_list.append(value['HostID'])
            elif isinstance(value, list):
                find_hosts(value)
            elif isinstance(value, dict):
                find_in_dict(value)
            else:
                continue
                




