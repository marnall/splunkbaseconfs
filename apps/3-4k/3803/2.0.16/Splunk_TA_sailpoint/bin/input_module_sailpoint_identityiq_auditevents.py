
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import base64
import json
from urllib.parse import urlparse

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''

def validate_input(helper, definition):
    # This example accesses the modular input variable
    # text = definition.parameters.get('text', None)
    pass
    
    #This method will extract array of object events as well as any particular element from those incoming objects
def get_json_element(obj, path):
    res = []
    path_len = len(path)-1  # Setting len to loop through all the elements
    
    for lookup_key in path:     # Looking up each element in the path list
        if isinstance(obj, dict):   # Check if the object is a dictionary.
            if path.index(lookup_key) == path_len and lookup_key in obj.keys():
                res.append(obj[lookup_key])    # Append the desired value in the result list. 
            else:
                obj = obj[lookup_key]   # If this is not the last element in the path list navigate to the child object.
                continue    # Lookup the next element from path list from new object. 

        if isinstance(obj, list):   # Check if the child object is an instance of a list.
            for ele in obj:    # Loop through all the objects in the obj list.  
                if isinstance(ele, dict):
                    if path.index(lookup_key) == path_len and lookup_key in ele.keys():
                        res.append(ele[lookup_key]) # Append the desired value in the result list.
                    else:
                        obj = ele[lookup_key]   # If this is not the last element in the path list navigate to the 
                                                # child object.

    return res
    
# Function to test if the url is https.
def is_https(helper, identityiq_url):
    
    helper.log_info("INFO Entering is_https")
    scheme = urlparse(identityiq_url).scheme
    if scheme.lower() == 'https':
        helper.log_info("INFO IdentityIQ URL is HTTPS.")
        return True
    else:
        helper.log_info("ERROR IdentityIQ URL is not HTTPS.")
        return False      

# Function to get OAuth token from IdentityIQ.
def get_token(helper, identityiq_url, client_id, client_secret):
    
    helper.log_info("INFO Entering get_token")
    endpoint = '{identityiq_url}/oauth2/token'
    url = endpoint.format(identityiq_url=identityiq_url)
    
    basic_auth = client_id + ':' + client_secret
    basic_auth_bytes = base64.b64encode(basic_auth.encode()).decode()

    # This is as per the IdentityIQ 8.1 release docs.
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Basic %s' % basic_auth_bytes}
    data = {'grant_type':'client_credentials'}
    
     # Check if identityiq_url is https.
    if not is_https(helper, url):
       return False
    
    response = requests.post(url, headers=headers, data=data)
    return response
    
# Function to construct an oauth header.
def build_oauth2_header(helper, identityiq_url, client_id, client_secret):
    
    helper.log_info("INFO Entering build_oauth2_header")
    token = get_token(helper,identityiq_url, client_id, client_secret)
    # Verify if the token was received.
    if not token:
        helper.log_error("ERROR No response received from IdentityIQ for access token.")
        return {'Accept': 'application/json', 'Content-Type': 'application/json'}
    else:
        # Get the token.
        token_body = token.content.decode('utf8').replace("'", '"')
        access_token = json.loads(token_body)['access_token']

        if not access_token:
            helper.log_info("DEBUG Response received from IdentityIQ but no access token was sent.")
            return {'Accept': 'application/json', 'Content-Type': 'application/json'}
        else:
            helper.log_info("DEBUG Received access token from IdentityIQ.")
            return {'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + access_token}

# Function to build a header for IdentityIQ requests.
def build_header(helper, identityiq_url, client_id, client_secret):

    helper.log_info("INFO Entering build_header")
    if client_id and client_secret:
        # If client_id & client_secret exists then construct oauth.
        return build_oauth2_header(helper, identityiq_url, client_id, client_secret)
    else:
        # This should not happen.
        helper.log_error("Error No credentials were provided.")
        return None
        
# Function to test if the list is empty
def isListEmpty(events):
    if isinstance(events, list): # Is a list
        return all( map(isListEmpty, events) )
    return False # Not a list
    
# Function to test timeout value.
def setTimeout(timeout):
    if timeout is None or timeout == "":
        timeoutValue=None
    else:
        timeoutValue = float(timeout)
    return timeoutValue

def collect_events(helper, ew):
    
    helper.log_info("DEBUG Entering collect events")
    
    #Get data input configuration
    global_account = helper.get_arg('global_account')
    client_id = global_account['username']
    client_secret= global_account['password']
    identityiq_url= helper.get_arg("identityiq_url")
    timeout_value= helper.get_arg("timeout_value")
    
    hostname = urlparse(identityiq_url).hostname

    # Build the header.
    headers = build_header(helper, identityiq_url, client_id, client_secret)

    payload = {}
    file_name = f"audit_events_checkpoint_{hostname}.txt"
    
    #Read the timestamp from the checkpoint file, and create the checkpoint file if necessary
    #The checkpoint file contains the epoch datetime of the 'created' date of the last event seen in the previous execution of the script. 
    checkpoint_file = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Splunk_TA_sailpoint', 'tmp', file_name)
    try:
        file = open(checkpoint_file, 'r')
    except IOError:
        try:
            file = open(checkpoint_file, 'w')
        except IOError:
            os.makedirs(os.path.dirname(checkpoint_file))
            file = open(checkpoint_file, 'w')
            
    with open(checkpoint_file, 'r') as f:
         checkpoint_time = f.readlines()
     
    yesterday_dt = datetime.datetime.now() - datetime.timedelta(days = 1)
    
    #calculate epoch time in milliseconds which is 1 day in past 
    initial_checkpoint_time = int((yesterday_dt - datetime.datetime(1970, 1, 1)).total_seconds() *1000)
    helper.log_error("Initial checkpoint time is " + str(initial_checkpoint_time))
    
    if len(checkpoint_time) == 1:
        checkpoint_time =int(checkpoint_time[0])
    else:
        checkpoint_time = initial_checkpoint_time
        helper.log_info("No checkpoint time available. Setting it to default value.")
    
    #Standard query params, checkpoint_time value is set from what was saved in the checkpoint file
    queryparams= {
         "startTime" : checkpoint_time,
         "startIndex" : 1,
         "count" : 1000
    }

    audit_events_url = "{}/plugin/rest/SIEMPlugin/audit-events".format(identityiq_url)
    
     #Check if audit_events_url is https.
    if not is_https(helper, audit_events_url):
        return False
        
    # Check timeout value. If set will override “None” sent in the send_http_request() 
    valid_timeout = setTimeout(timeout_value)
    
    helper.log_info("Initiating the request")
    
    #Initiate the request
    response = helper.send_http_request(audit_events_url, "GET", parameters=queryparams, payload=payload, headers=headers, cookies=None, verify=True, cert=None, timeout=valid_timeout, use_proxy=None)
    
    response_status_code = response.status_code
    
    results = []
    
    if response_status_code == 200:
       results = response.json()
    else:
        helper.log_error("Failure from server " + str(response_status_code))
        
    #Retrieve audit events from the json.
    auditEvents = get_json_element(results, ["auditEvents"])

    #Iterate the audit events array and create Splunk events for each one
    invalid_response = isListEmpty(auditEvents)
    if not invalid_response:
        for auditEvent in auditEvents:
            
            data = json.dumps(auditEvent)
            event = helper.new_event(data=data, time=None, host=None, index=helper.get_output_index(), source=helper.get_input_type(), sourcetype=helper.get_sourcetype(), done=True, unbroken=True)
            ew.write_event(event)
            
        #Get the created date of the last audit event in the run and save it as a checkpoint key in the checkpoint file    
        list_of_created_date = get_json_element(results, ["auditEvents", "created"])
        helper.log_info("list of created dates are as below: ")
        helper.log_info(list_of_created_date)

        new_checkpoint_created_date = list_of_created_date[-1]
        helper.log_info("DEBUG New checkpoint date \n{}".format(new_checkpoint_created_date))
    
        #Write new checkpoint key to the checkpoint file    
        with open(checkpoint_file, 'r+') as f:
            f.seek(0)
            f.write(str(new_checkpoint_created_date))
            f.truncate()