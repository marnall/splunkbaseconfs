
# encoding = utf-8

import os
import sys
import time
import datetime
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
    # object_type = definition.parameters.get('object_type', None)
    # object_count = definition.parameters.get('object_count', None)
    pass


def get_auth_token(endpoint, username, password):

    url = endpoint + '/login'
    
    try:
        response = requests.get(
            url=url,
            params={
                "username": username,
                "password": password,
            }
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


def get_objects(auth_token, url, parameters):
    
    try:
        response = requests.get(
            url = url,
            params = parameters,
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
        
def logout(endpoint):

    url = endpoint + '/logout'
    
    try:
        response = requests.get(
            url = url,
        )
    except requests.ConnectionError as e:
        print(str(e))
    except requests.exceptions.RequestException as e:
        print('HTTP Request failed')
        print(str(e))


def collect_events(helper, ew):

    username = helper.get_global_setting("username")
    password = helper.get_global_setting("password")
    endpoint = helper.get_global_setting("endpoint")

    endpoint = 'https://' + endpoint + '/Services/REST/v1'
    

    # get global variable configuration
    object_type = helper.get_arg("object_type")
    object_count = helper.get_arg("object_count")
    if object_type == "IP4Block" or object_type == "IP6Block":
        st = "bluecat:ipam:block"
    elif object_type == "IP4Network" or object_type == "IP6Network":
        st = "bluecat:ipam:network"
    elif object_type == "IP4Address" or object_type == "IP6Address":
        st = "bluecat:ipam:address"
    elif object_type == "HostRecord":
        st = "bluecat:ipam:host"
    parent_type = helper.get_arg("parent_type")
    parent_id = helper.get_arg("parent_id")
    try:
        parent_id = int(parent_id)
    except ValueError:
        parent_id = 0
    except TypeError:
        parent_id = 0
    keyword = helper.get_arg("keyword")
    is_kw = re.search('^(\w+)', keyword)
        
    auth_token = get_auth_token(endpoint, username, password)
    
    if (((object_type == "IP4Address" and parent_type == "IP4Block") or (object_type == "IP6Address" and parent_type == "IP6Block")) and parent_id > 0) or (is_kw and object_type =="IP4Address"):
        if is_kw:
            url = endpoint + '/searchByObjectTypes'
            parameters = {
                "keyword": keyword,
                "types": "IP4Network",
                "start": "0",
                "count": 16384,
            }
        else:
            if parent_type == "IP4Block":
                ot = "IP4Network"
            elif parent_type == "IP6Block":
                ot = "IP6Network"
            url = endpoint + '/getEntities'
            parameters = {
                "parentId": parent_id,
                "type": ot,
                "start": "0",
                "count": 16384,
            } 
        networks = get_objects(auth_token, url, parameters)
        for network in networks:
            parent_id = network["id"]
            parent_id = int(parent_id)
            url = endpoint + '/getEntities'
            parameters = {
                "parentId": parent_id,
                "type": object_type,
                "start": "0",
                "count": object_count,
            }
            response = get_objects(auth_token, url, parameters)
            for network_object in response:
                data = json.dumps(network_object)
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=st, data=data)
                ew.write_event(event)
   
    elif  (parent_type == "IP4Block" or parent_type == "IP6Block") and parent_id > 0:
        url = endpoint + '/getEntities'
        parameters = {
            "parentId": parent_id,
            "type": object_type,
            "start": "0",
            "count": object_count,
        }
        response = get_objects(auth_token, url, parameters)
        for network_object in response:
            data = json.dumps(network_object)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=st, data=data)
            ew.write_event(event)

    else:
        url = endpoint + '/searchByObjectTypes'
        parameters = {
                "keyword": "*",
                "types": object_type,
                "start": "0",
                "count": object_count,
        }
        response = get_objects(auth_token, url, parameters)
        for network_object in response:
            data = json.dumps(network_object)
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=st, data=data)
            ew.write_event(event)
            
    logout(endpoint)        
