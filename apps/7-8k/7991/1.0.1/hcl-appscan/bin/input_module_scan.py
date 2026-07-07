# *************************************************************************
#  * HCL Confidential
#  * HCL AppScan
#  * (c) Copyright HCL Technologies Limited 2024. All Rights Reserved.
#  *
#  * The source code for this program is not published or otherwise
#  * divested of its trade secrets, irrespective of what has been
#  * deposited with the U.S. Copyright Office.
# *************************************************************************


# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import traceback
import constants_definition
import splunk.rest as rest
import splunk

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
    # global_account = definition.parameters.get('global_account', None)
    pass

def collect_events(helper, ew):
    try:
        input_name = helper.get_input_stanza_names()
        dc_starting_time = time.time()
        helper.log_info(
            "Starting data collection for input {} at {}".format(
                input_name, dc_starting_time
            )
        )
        global_account = helper.get_arg("global_account")
        source = helper.get_input_type()
        if not global_account:
            helper.log_error("Invalid global_account for input '{}'.".format(input_name))
            return
        keyID = global_account.get("username")
        secretID = global_account.get("password")
        appScanUrl = global_account.get("url")
        allowUntrustedConnection = global_account.get("allowUntrusted", False)
        skip = 0
        count = "true"
        top = 10
        collection_name = "hcl_appscan_checkpointer"
        path = "/servicesNS/nobody/hcl-appscan/storage/collections/config"
        try:
            # Check if the collection exists
            data = rest.simpleRequest(
                path,
                sessionKey=helper.context_meta['session_key'],
                method="GET",
                getargs={'output_mode': 'json'},
                raiseAllErrors=True,
            )
            data_str = data[1].decode('utf-8')
            data_json = json.loads(data_str)
            collections = data_json['entry']
            collection_exists = any(collection['name'] == collection_name for collection in collections)
            
            if not collection_exists:
                # Create the collection if it does not exist
                collection_data = {
                    "name": collection_name
                }
                rest.simpleRequest(
                    path,
                    sessionKey=helper.context_meta['session_key'],
                    method="POST",
                    postargs=collection_data,
                    raiseAllErrors=True,
                )
        except splunk.ResourceNotFound:
            # Handle the case where the storage/collections/config endpoint is not found
            pass
        path = "/servicesNS/nobody/hcl-appscan/storage/collections/data/hcl_appscan_checkpointer/scans"
        try:
            data = rest.simpleRequest(
                path,
                sessionKey=helper.context_meta['session_key'],
                method="GET",
                getargs={'output_mode': 'json'},
                raiseAllErrors=True,
            )
            data_str = data[1].decode('utf-8')
            data_json = json.loads(data_str)
            state_list = data_json['state']
        except splunk.ResourceNotFound:
            state_list = None
        while True:
            scans = constants_definition.fetch_scans(keyID, secretID,appScanUrl,allowUntrustedConnection, skip, count, top)
            helper.log_info(f"Fetched {len(scans)} scans")
            for scan in scans:
                if state_list is None or "scans_" + str(scan["Id"]) not in state_list:
                    if state_list is None:
                        state_list = []
                    event = helper.new_event(index=helper.get_output_index(),
                                    sourcetype="AppScanScans",
                                    source=source,
                                    data=json.dumps(scan, ensure_ascii=False))
                    ew.write_event(event)
                    helper.log_info(scan)
                    helper.log_info(scan["Id"])
                    if isinstance(state_list, str):
                        state_list = json.loads(state_list)
                    state_list.append("scans_" + str(scan["Id"]))
                    helper.save_check_point("scans", state_list)
            skip += 10
            if len(scans) < 10:
                break
        helper.log_info("Total time taken in data collection for input {} "
                                    "is {}".format(input_name, (time.time() - dc_starting_time)))
    except requests.exceptions.SSLError as e:
        helper.log_error("SSL certificate verification failed. Please add a valid "\
                         "SSL Certificate or Change VERIFY_SSL flag to False "\
                         "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
    except requests.exceptions.ProxyError as e:
        helper.log_error("Please verify Proxy Configurations. "\
                         "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
    except Exception as e:
        helper.log_error(
            "HCL AppScan Error: Terminating the data collection unsuccessfully. "\
            "Error: {}".format(str(e)))
        helper.log_debug("Error Trace: {}".format(traceback.format_exc()))
        return False
