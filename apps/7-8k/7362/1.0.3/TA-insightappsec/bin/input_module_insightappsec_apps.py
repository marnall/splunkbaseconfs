
# encoding = utf-8

import os
import sys
import time
import datetime

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
    # api_endpoint = definition.parameters.get('api_endpoint', None)
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    
    import requests
    import json
    
    api_endpoint = helper.get_arg('api_endpoint')
    api_key = helper.get_arg('api_key')
    index=0
    flag=1
    
    while(flag == 1):
        url = api_endpoint+"/ias/v1/search?index="+str(index)+"&size=100"
    
        payload = json.dumps({
        "query": "app.name IS NOT NULL",
        "type": "APP"
        })
        headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': api_key
        }
    
        response = requests.request("POST", url, headers=headers, data=payload)
        
        if response.status_code == 200:
            # Process the response data (e.g., print or parse JSON)
            json_data = json.loads(response.content)
            
            try:
                total_pages = json_data['metadata']['total_pages']
                if(index+1 == total_pages):
                    flag=0
                else:
                    index=index+1
            except:
                flag = 0
    
            for item in json_data['data']:
                item=json.dumps(item)
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="rapid7:insightappsec:app", data=item)
                ew.write_event(event)
        else:
            print(f"Error: {response.status_code} - {response.text}")
