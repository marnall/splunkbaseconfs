
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import logging

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

AUTHORIZATIONBASEURL = 'https://api{}.protect.proofpoint.com/v1/auth'


def getAccessToken(helper,user_name,password,APIKey,dataCenter,proxy_enabled,context):
    
    logging.debug("CASB {} TA - Generating Access Token - Start".format(context))
    
    
    authUrl=getURL(AUTHORIZATIONBASEURL,dataCenter)
    try:
        authResponse = helper.send_http_request(authUrl,'POST', parameters=None, payload=json.dumps({"client_id": user_name, "client_secret": password}), headers={'Content-Type': 'application/json', 'x-api-key': APIKey}, cookies=None, verify=False, cert=None,timeout=None, use_proxy=proxy_enabled)
    except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logging.error("CASB ACTIVITY TA - HTTP request exception: {}".format(message))
            logging.error("CASB ACTIVITY TA - Please verify the proxy settings")
            raise SystemExit(ex)
    r_status = authResponse.status_code
    authResponse_json=authResponse.json()
    if r_status != 200:
        message=""
        if 'message' in authResponse_json:
            message=authResponse_json['message']
        elif 'error' in authResponse_json:
            message=authResponse_json['error']
        logging.error("CASB {} TA - Failed to Generate Access Token, error Message: {}. Please verify that the credentials and API Key entered are correct".format(context,message))
        raise Exception("CASB {} TA - Failed to Generate Access Token, error Message: {}. Please verify that the credentials and API Key entered are correct".format(context,message))
    logging.debug("CASB {} TA - Generating Access Token - Completed".format(context))
    token=authResponse_json['auth_token']
    return token

def getURL(baseurl,dataCenter):
    url=""
    if dataCenter == "EU":
        if "flapi" in baseurl:
            url = baseurl.format("-EU2")
        else:
            url = baseurl.format("")
    elif dataCenter == "US":
        url = baseurl.format("-US1")
    elif dataCenter == "STG":
        url = baseurl.format("-STG")
    elif dataCenter == "AU":
        url = baseurl.format("-AU1")
    return url


def getPlatfromRegion(dataCenter):
    if dataCenter == "EU":
        return "eu-central-1"
    elif dataCenter == "US":
        return "us-east-1"
    elif dataCenter == "AU":
        return "ap-southeast-2"
    else:
        return "us-east-1" 
    
def extract_alert_timestamp(json):
    try:
        return int(json['timestamp'])
    except KeyError:
        return 0
        
def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        elif type(x) is str:
            out[name[:-1]] = x.strip("[]").strip("\"\"")
        else:
            out[name[:-1]] = x

    flatten(y)
    return out
