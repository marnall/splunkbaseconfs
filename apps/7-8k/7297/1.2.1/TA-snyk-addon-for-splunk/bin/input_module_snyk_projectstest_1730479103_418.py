
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
    # organization_id = definition.parameters.get('organization_id', None)
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    
    import requests
    import json
    import re
    
    org_id = helper.get_arg('organization_id')
    api_key = helper.get_arg('api_key')
    api_region = helper.get_arg('region')
    url = api_region+"/rest/orgs/"+org_id+"/projects"
    next_url = 0
    flag = 0
    
    while flag==0:
        
        if next_url==0:
            url = url
        else:
            url = api_region+next_url
            next_url = 0
    
        params = {
            "version": "2024-10-15",
            "limit": 100
        }
    
        headers = {
            "accept": "application/vnd.api+json",
            "authorization": api_key
        }
    
        response = requests.get(url, params=params, headers=headers)
    
        if response.status_code == 200:
            # Process the response data (e.g., print or parse JSON)
            #print(response.json())
            json_data = json.loads(response.content)
            
            try:
                next_page = json_data['links']['next']
                next_url = re.sub('version=.*?&|limit=100&', '', next_page, 2)
            except:
                flag = 1
    
            for item in json_data['data']:
                item = json.dumps(item)
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=item)
                ew.write_event(event)
           
        else:
            print(f"Error: {response.status_code} - {response.text}")
    
