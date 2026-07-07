
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import re

'''
    Calls the listvs operation on the Kemp API
    Handles discovered issue with the JSON response
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # kemp_server = definition.parameters.get('kemp_server', None)
    pass

def collect_events(helper, ew):
    
    kemp_server = helper.get_arg('kemp_server')
    api_key = helper.get_arg('api_key')
    # set the API endpoint and request body
    url = 'https://'+kemp_server+'/accessv2'
    data = "{\"apikey\":\""+api_key+"\",\n\"cmd\":\"listvs\"}"

    # make a POST request to the API endpoint with the specified request body
    helper.log_info("Making API Call to: "+kemp_server)
    response = requests.post(url, data=data)
    helper.log_info("API Call Responded with: "+str(response.status_code))

    # check if the response status code is 200 (OK)
    if response.status_code == 200:
        # fix known bugs in the KEMP API listvs response
        fixed_json = re.sub(r'(?<!,\n)\s"EspEnabled".*?:\sfalse,','',response.text)
        # retrieve the JSON data from the response
        data = json.loads(fixed_json)
        # retrieve the array of items from the 'VS' field
        items = data['VS']
        # print the number of items in the array
        helper.log_info("Total items in response: "+str(len(items)))
        # iterate over each item in the array
        for item in items:
            # write each event in this block
            # log some debug but handle scenario where NickName is not set:
            if "NickName" in item:
                helper.log_debug("Processing item: "+item["NickName"])
            else:
                helper.log_debug("Processing item without NickName")
            strItem=json.dumps(item)
            sourceStr = helper.get_input_type()+"://"+helper.get_input_stanza_names()
            event = helper.new_event(host=kemp_server,source=sourceStr, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=strItem)
            ew.write_event(event)
    else:
        # handle any errors that occur
        helper.log_error('Error: unable to retrieve data from API')
        helper.log_error(str(response.status_code))
        
        
    