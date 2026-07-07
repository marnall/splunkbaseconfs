
# encoding = utf-8

import os
import sys
import time
import requests
import re
import json

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
    # object_type = definition.parameters.get('object_type', None)
    pass


def get_auth_token(endpoint, account):

    username = account['username']
    password = account['password']
    url = 'https://' + endpoint + '/Services/REST/v1/login'
    
    try:
        response = requests.get(
            url=url,
            params={
                "username": username,
                "password": password,
            },
            verify=False
        )
        content = response.text
        c = re.search('^\"(?:\S+\s){2}(\S+\s\S+)', content)
        if c:
            token = c.group(1)
            return token
    except requests.ConnectionError as e:
        print(str(e))
    except requests.exceptions.RequestException as e:
        print('HTTP Request failed')
        print(str(e))


def get_objects(endpoint, account, object_type, object_count):
    
    url = 'https://' + endpoint + '/Services/REST/v1/searchByObjectTypes'
    auth_token = get_auth_token(endpoint, account)

    try:
        response = requests.get(
            url = url,
            params={
                "keyword": "*",
                "types": object_type,
                "start": "0",
                "count": object_count,
            },
            verify=False,
            headers={
                "Authorization": auth_token,
                "Content-Type": "application/json",
            },
        )
        objects = json.loads(response.text)
        return objects
    except requests.ConnectionError as e:
        print(str(e))
    except requests.exceptions.RequestException as e:
        print('HTTP Request failed')
        print(str(e))


def collect_events(helper, ew):
   
    # get global variable configuration
    account = helper.get_arg('global_account')
    endpoint = helper.get_global_setting("endpoint")
    object_type = helper.get_arg("object_type")
    object_count = helper.get_arg("object_count")
    
    response = get_objects(endpoint, account, object_type, object_count)
    for network_object in response:
        data = json.dumps(network_object)
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
        ew.write_event(event)