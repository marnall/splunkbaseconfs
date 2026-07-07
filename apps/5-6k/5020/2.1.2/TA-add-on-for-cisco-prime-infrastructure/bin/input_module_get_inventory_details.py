
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json

requests.packages.urllib3.disable_warnings()

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
    # global_account = definition.parameters.get('global_account', None)
    # api_version = definition.parameters.get('api_version', None)
    max_results = definition.parameters.get('max_results', None)
    
    if int(max_results) > 1000 :
        raise ValueError(
            "Max results should be 1000 or less, not {}.".format(interval))

    pass


def send_request(url, auth_values, first, max_results):

    try:
        response = requests.get(
            url=url,
            params={
                ".full": 'true',
                ".firstResult": first,
                ".maxResults": max_results,
            },
            auth=auth_values,
            headers={
                "Content-Type": "application/json",
            },
            verify=False,
        )
        results = json.loads(response.text)
        return results
    except requests.exceptions.RequestException:
        print('HTTP Request failed')


def collect_events(helper, ew):
    
    endpoint = helper.get_global_setting('endpoint')
    account = helper.get_arg('global_account')
    
    username = account['username']
    password = account['password']
    auth_values = (username, password)
    max_results = helper.get_global_setting('max_results')

    first = 0
    last = 1
    count = last
    url='https://' + endpoint + '/webacs/api/v4/data/InventoryDetails.json'
    content_type = 'inventoryDetailsDTO'

    if 'max_results' in locals():
        max_results = max_results
    else:
        max_results = 100

    while first < count:
        response = send_request(url, auth_values, first, max_results)
        if "queryResponse" in response:
            response = response['queryResponse']
            if "@count" in response:
                count = response['@count']
            if "@last" in response:
                last = response['@last']
                first = int(last) + 1
            else:
                first = count
            if "entity" in response:
                entity = response['entity']
                for device in entity:
                    data = json.dumps(device[content_type])
                    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                    ew.write_event(event)
        else:
            first = count    
        

