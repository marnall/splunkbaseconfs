import os
import sys
import time
import datetime
import json
import base64
import requests
import re


def validate_input(helper, definition):
    pass
    
def isValidURL(str):
 
    # Regex to check valid URL
    regex = ("((https)://)(www.)?" +
             "[a-zA-Z0-9@:%._\\+~#?&//=]" +
             "{2,256}\\.[a-z]" +
             "{2,6}\\b([-a-zA-Z0-9@:%" +
             "._\\+~#?&//=]*)")
     
    # Compile the ReGex
    p = re.compile(regex)
 
    # If the string is empty
    # return false
    if (str == None):
        return False
 
    # Return if the string
    # matched the ReGex
    if(re.search(p, str)):
        return True
    else:
        return False
        
def collect_events(helper, ew):
    opt_api_url = helper.get_arg('api_url')
    username=helper.get_arg('username')
    password=helper.get_arg('password')
    
    userpass = username + ':' + password
    encoded_u = base64.b64encode(userpass.encode()).decode()
    headers = {"Authorization" : "Basic %s" % encoded_u}
    if(isValidURL(opt_api_url) == True):
        response = requests.request("GET", opt_api_url, headers=headers, verify=False, proxies=False)
        r_json = response.json()
        
        if response.status_code!=200:
            response.raise_for_status()

    
        event = helper.new_event(json.dumps(r_json), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)
    
