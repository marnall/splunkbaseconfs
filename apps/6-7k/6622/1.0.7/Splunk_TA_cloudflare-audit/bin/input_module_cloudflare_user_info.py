
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json 

def writeEvent(helper,ew,data=None):
    if data == None:
        helper.log_warning("No data was passed to writeEvent()")
        quit()
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)  

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # email = definition.parameters.get('email', None)
    # global_api_key = definition.parameters.get('global_api_key', None)
    pass

def collect_events(helper, ew):
    try:
        key = helper.get_arg('global_api_key')
        email = str(helper.get_arg('email'))
        timeout = float(helper.get_arg('timeout'))
        accounts_url = "https://api.cloudflare.com/client/v4/accounts/"
        accounts_export_url = accounts_url+"?export=true"
        headers={"X-Auth-Key":key,"X-Auth-Email":email,"Content-type":"application/json"}
        accountsReq = helper.send_http_request(accounts_export_url,"GET",headers=headers,verify=True,use_proxy=True,timeout=timeout)    
        for account in accountsReq.json()['result']:
            aid = account['id']
            members_url = accounts_url+aid+"/members/?export=true"
            membersReq = helper.send_http_request(members_url,"GET",headers=headers,verify=True,use_proxy=True,timeout=timeout)
            for result in membersReq.json()['result']:
                writeEvent(helper, ew, json.dumps(result['user']))
    except Exception as e:
        helper.log_error(str(e))