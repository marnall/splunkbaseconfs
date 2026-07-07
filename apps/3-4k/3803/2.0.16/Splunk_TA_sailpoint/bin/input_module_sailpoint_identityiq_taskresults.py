
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
    
    # Check if url is https.
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
    
    # Build the header.
    headers = build_header(helper, identityiq_url, client_id, client_secret)
    
    payload = {}
    
    hostname = urlparse(identityiq_url).hostname
    file_name = f"task_results_checkpoint_{hostname}.txt"
        
    #Read the created time from the checkpoint file, and create the checkpoint file if necessary
    #The checkpoint file contains created date to be utilized for next run of this script
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
    
    count = 1000
    
    #Standard query params  
    queryparams= {
         "sortBy" : "completed",
         "startIndex" : 1,
         "count" : count,
         "sortOrder" : "descending"
    }
    
    yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
    initial_checkpoint_time = yesterday.isoformat()
    
    #Check if the created time is set in the checkpoint file. 
    #If yes,add it to the list of query params and this will be utilized for next run of the script
    #If no, set the completed time filter to initial checkpoint time which is 1 day in past
    if len(checkpoint_time) == 1:
        completed_checkpoint_time = checkpoint_time[0]
    else:
        completed_checkpoint_time = initial_checkpoint_time
        
    filter_param = "completed ge \"{}\"".format(completed_checkpoint_time)
    queryparams['filter'] = filter_param
    task_results_url = "{}/scim/v2/TaskResults".format(identityiq_url)
    
    # Check if task_results_url is https.
    if not is_https(helper, task_results_url):
        return False
     
    # Check timeout value. If set will override “None” sent in the send_http_request() 
    valid_timeout = setTimeout(timeout_value)
    
    helper.log_info("Initiating the request")
    
    #Initiate the request
    response = helper.send_http_request(task_results_url, "GET", parameters=queryparams, payload=payload, headers=headers, cookies=None, verify=True, cert=None, timeout=valid_timeout, use_proxy=None)
    
    response_status_code = response.status_code
    
    results = []
    
    if response_status_code == 200:
       results = response.json()
    else:
        helper.log_error("Failure from server " + str(response_status_code))
        
    #Retrieve task result "Resources" from the json.
    taskResults = get_json_element(results, ["Resources"])

    #Iterate the resources array and create Splunk events for each one
    invalid_response = isListEmpty(taskResults)
    if not invalid_response:
        for taskResult in taskResults:
           
            data = json.dumps(taskResult)
            event = helper.new_event(data=data, time=None, host=None, index=helper.get_output_index(), source=helper.get_input_type(), sourcetype=helper.get_sourcetype(), done=True, unbroken=True)
            ew.write_event(event)
        
        #Get the completed date of the first task result in the run and save it as a checkpoint time in the checkpoint file    
        completed_time = get_json_element(taskResult, ["completed"])
        completed_checkpoint_time = completed_time[0]
        helper.log_info("completed_checkpoint_time {}".format(completed_checkpoint_time))
    
        #Write new completed time to the checkpoint file    
        with open(checkpoint_file, 'r+') as f:
            f.seek(0)
            f.write(str(completed_checkpoint_time))
            f.truncate()
