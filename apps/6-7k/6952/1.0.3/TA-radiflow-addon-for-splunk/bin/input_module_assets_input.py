
# encoding = utf-8

import os
import sys
import time
import json
import datetime
import requests
from radiflow_rest_client import get_all_assets,get_detailed_device_info,save_checkpoint,get_checkpoint
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

_APP_NAME = 'RadiFlowAddOnForSplunk'

log_location = make_splunkhome_path(['var', 'log', 'splunk', _APP_NAME])


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # radiflow_account = definition.parameters.get('radiflow_account', None)
    pass

def collect_events(helper, ew):
    try:
        source = helper.get_arg('name')
        all_assets = get_all_assets(helper)
        if all_assets==None:
            pass
        else:
            for asset in all_assets:
                asset_id = asset['id']
                asset_zone = asset['zone']
                zone_mapping:str = ""
                if(asset.get('bps') is not None):
                    asset_bps = asset['bps']
                    for string in asset_bps:
                        if ("." in string):
                            zone_mapping = asset_zone
                        else:
                            zone_mapping = string
                else:
                    zone_mapping = asset_zone

                checkpoint = get_checkpoint(log_location,source,asset_id)
                if(checkpoint==False):
                    get_detailed_device_info(log_location,asset_id,zone_mapping,helper,ew)
                    save_checkpoint(log_location,source,asset_id)
            helper.log_info(f"Found {len(all_assets)} Assets!")
    except Exception as e:
        sourcetype = "RadiFlowAddonForSplunk:error"
        data = str(e)
        input_type = helper.get_arg('name')
        event = helper.new_event(source=input_type, index=helper.get_output_index(), sourcetype=sourcetype, data=data)
        ew.write_event(event)
        
    