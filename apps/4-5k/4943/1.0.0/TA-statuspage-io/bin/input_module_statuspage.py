
# encoding = utf-8

import os
import sys
import time
import datetime
import json
from datetime import datetime
import time


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    statuspage_url = definition.parameters.get('statuspage_url', None)
    pass

def collect_events(helper, ew):
    
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_statuspage_url = helper.get_arg('statuspage_url')
    opt_incidents = helper.get_arg('incidents')
    opt_maintenance = helper.get_arg('maintenance')

    # get input type
    helper.get_input_type()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    
    icp_key=opt_statuspage_url + "-incidents"
    mcp_key=opt_statuspage_url + "-maintenance"
    service_name= "Statuspage:" + helper.get_input_stanza_names()
    #Build Incidents URL
    iurl = "https://" + opt_statuspage_url + "/api/v2/incidents.json"
    murl = "https://" + opt_statuspage_url + "/api/v2/scheduled-maintenances.json"
    method = "GET"
    
    #Get Saved Checkpoints
    icp_updated_at=helper.get_check_point(icp_key)
    mcp_updated_at=helper.get_check_point(mcp_key)
    if icp_updated_at is None:
        icp_updated_at=0
    nicp_updated_at=icp_updated_at
    if mcp_updated_at is None:
        mcp_updated_at=0
    nmcp_updated_at=mcp_updated_at

    if opt_incidents:
        response = helper.send_http_request(iurl, method, parameters=None, payload=None,
                                            headers=None, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
        # get response body as json. If the body text is not a json string, raise a ValueError
        r_json = response.json()
        # get response status code
        r_status = response.status_code
        # check the response status, if the status is not sucessful, raise requests.HTTPError
        response.raise_for_status()

        for incidents in r_json['incidents']:
            updated_at=time.mktime(datetime.timetuple(datetime.fromisoformat(incidents['updated_at'])))

            if updated_at > icp_updated_at:
                data=json.dumps(incidents)
                if updated_at > nicp_updated_at:
                    nicp_updated_at=updated_at
                # To create a splunk event
                event = helper.new_event(source=service_name, index=helper.get_output_index(), sourcetype="statuspage:incidents", data=data)
                ew.write_event(event)
    if opt_maintenance:
        response = helper.send_http_request(murl, method, parameters=None, payload=None,
                                            headers=None, cookies=None, verify=True, cert=None,
                                            timeout=None, use_proxy=True)
        # get response body as json. If the body text is not a json string, raise a ValueError
        r_json = response.json()
        # get response status code
        r_status = response.status_code
        # check the response status, if the status is not sucessful, raise requests.HTTPError
        response.raise_for_status()
        for maintenance in r_json['scheduled_maintenances']:
            updated_at=time.mktime(datetime.timetuple(datetime.fromisoformat(maintenance['updated_at'])))

            if updated_at > icp_updated_at:
                data=json.dumps(maintenance)
                if updated_at > nmcp_updated_at:
                    nmcp_updated_at=updated_at
                # To create a splunk event
                event = helper.new_event(source=service_name, index=helper.get_output_index(), sourcetype="statuspage:maintenance", data=data)
                ew.write_event(event)
    ## Save Checkpoint
    helper.save_check_point(icp_key, nicp_updated_at)
    helper.save_check_point(mcp_key, nmcp_updated_at)