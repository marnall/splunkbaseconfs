
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import os.path
import logging as Log

# Validate if checkpoint log exists
def isCheckpoint(check_file, chkpntID):
    file_exists = os.path.isfile(check_file) 
    if file_exists:
        with open(check_file, 'r') as file:
            chkpntID_list = file.read().splitlines()
    else:
        with open(check_file, 'w+') as file:
            chkpntID_list = file.read().splitlines()

    return (chkpntID in chkpntID_list)

# Write checkpoint log
def write2Checkpoint(check_file, chkpntID):
    with open(check_file,'a') as file:
        file.writelines(chkpntID + '\n')

# Write to Splunk
def write2Splunk(helper, ew, data, sType):
    data = json.dumps(data)
    if sType == '':
        event = helper.new_event(data, host=None, done=True, unbroken=True)
    else:
        event = helper.new_event(data, sourcetype=sType, host=None, done=True, unbroken=True)

    try:
        ew.write_event(event)
    except Exception as e:
        raise e

# Filter/search parameters creation
def genParams(event_source, FROM,  request_method, resource, occurred_at):
    lstParams = []
    lstParams.append(('event_source[in]', event_source))
    lstParams.append(('from', FROM))
    lstParams.append(('size', '100'))
    lstParams.append(('request_method[in]', request_method))
    lstParams.append(('resource[in]', resource))

    if occurred_at:
        lstParams.append(('occurred_at[gte]', occurred_at))

    params = []
    for p in  lstParams:
        params.append(p)

    return tuple(params)

def validate_input(helper, definition):
    mambu_audit_trail_endpoint = definition.parameters.get('mambu_audit_trail_endpoint', None)
    api_key = definition.parameters.get('api_key', None)
    event_source = definition.parameters.get('event_source', None)
    resource = definition.parameters.get('resources', None)
    request_method = definition.parameters.get('request_method', None)
    occurred_at = definition.parameters.get('occurred_at', None)

def collect_events(helper, ew):
    opt_mambu_audit_trail_endpoint = helper.get_arg('mambu_audit_trail_endpoint')
    opt_api_key = helper.get_arg('api_key')
    opt_event_source = helper.get_arg('event_source')
    opt_resource = helper.get_arg('resources')
    opt_request_method = helper.get_arg('request_method')
    opt_occurred_at = helper.get_arg('occurred_at')

    # Convert param lists to comma separated strings
    opt_event_source = ','.join(opt_event_source)
    opt_resource = ','.join(opt_resource)
    opt_request_method = ','.join(opt_request_method)

    headers = {
        'apiKey': opt_api_key
    }

    # Audit Trail Endpoint V1
    opt_mambu_audit_trail_endpoint = opt_mambu_audit_trail_endpoint + "/api/v1/events"
    
    # Path para el archivo de checkpoint utilizado (se crea un archivo por fecha YYYYMMDD)
    dtFile = str(datetime.datetime.now().strftime("%Y%m%d"))
    check_file = os.path.join('/', os.path.dirname(os.path.abspath(__file__)), 'checkpoint', dtFile + '-mambu')

    # We set to 0 the 'FROM' parameter (at first time)
    FROM = 0

    # Params generation
    params = genParams(opt_event_source, FROM, opt_request_method, opt_resource, opt_occurred_at)
    
    # Session Init
    client = requests.session()
    
    try:
        # API Call
        response = client.get(opt_mambu_audit_trail_endpoint, headers=headers, params=params, timeout=10)
        
        if response.status_code >= 200 and response.status_code <= 226:
    
            totalItemsCount = response.json()["totalItemsCount"]
            if totalItemsCount > 0:
                # First Page
                if len(response.json()["events"]) > 0:
                    for ev in response.json()["events"]:
        
                        chkpntID = ev["occurred_at"] + "_" + str(ev["response_code"]) + "_" + ev["resource"] + "_" + ev["event_source"] + "_" + ev["client_ip"] + "_" + ev["request_method"] + "_" + ev["username"]
        
                        # If checkpoint log does not exists 
                        if not isCheckpoint(check_file, chkpntID):
                            # Write checkpoint log 
                            write2Checkpoint(check_file, chkpntID)
                            
                            # Write to Splunk 
                            write2Splunk(helper, ew, ev, '_json')
        
                # Maximum size per page is 100
                size = 100
        
                # Recall every 100 events until Total is reached
                while FROM <= totalItemsCount:
        
                    # 'FROM' parameter value will increase (by size -100-) until 'totalItemsCount' value is reached.
                    FROM = FROM + size
        
                    # Params generation
                    params = genParams(opt_event_source, FROM, opt_request_method, opt_resource, opt_occurred_at)
                    
                    # API Call
                    response = client.get(opt_mambu_audit_trail_endpoint, headers=headers, params=params, timeout=10)
        
                    if len(response.json()["events"]) > 0:
                        for ev in response.json()["events"]:
                            chkpntID = ev["occurred_at"] + "_" + str(ev["response_code"]) + "_" + ev["resource"] + "_" + ev["event_source"] + "_" + ev["client_ip"] + "_" + ev["request_method"] + "_" + ev["username"]
        
                            # If checkpoint log does not exists 
                            if not isCheckpoint(check_file, chkpntID):
                                # Write checkpoint log
                                write2Checkpoint(check_file, chkpntID)
                                
                                # Write to Splunk 
                                write2Splunk(helper, ew, ev, '_json')
        else:
            msg = json.dumps(response.json()["message"])
            status = str(response.status_code)
           
            Log.error(status + ' - Mambu Audit Trail connection Failure - ' + msg)
            
    except requests.exceptions.ConnectTimeout:
        Log.error('Mambu Audit Trail ' + opt_mambu_audit_trail_endpoint + ', connection Timeout')