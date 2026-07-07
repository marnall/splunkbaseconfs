# encoding = utf-8

import os
import sys
import time
import datetime
import requests
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
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # user_agent = definition.parameters.get('user_agent', None)
    # api_key = definition.parameters.get('api_key', None)
    # siteid = definition.parameters.get('siteid', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    
    opt_username = helper.get_global_setting('username')
    opt_password = helper.get_global_setting('password')
    opt_app_source_name = helper.get_global_setting('app_source_name')
    opt_api_key = helper.get_global_setting('api_key')
    opt_siteid = helper.get_global_setting('siteid')

    
    
    ########################### Getting Token ######################################################
    url_token = "https://api.mindbodyonline.com/public/v6/usertoken/issue"
    payload_token = json.dumps({
        "Username": opt_username,
        "Password": opt_password
    })
    headers_token = {
        'User-Agent': opt_app_source_name,
        'Content-Type': 'application/json',
        'Api-Key': opt_api_key,
        'SiteId': opt_siteid,
    }
    response_token = requests.request("POST", url_token, headers=headers_token, data=payload_token)
    response_token_json=response_token.json()
    token=""
    for i in response_token_json:
        token=response_token_json["AccessToken"]
        
    ############################### Enrollments API #########################################################

    headers_client = {
        'User-Agent': opt_app_source_name,
        'Api-Key': opt_api_key,
        'Authorization': token,
        'Content-Type': 'application/json',
        'SiteId': opt_siteid
    }
    url_client = "https://api.mindbodyonline.com/public/v6/client/clients"
    response_client = requests.request("GET", url_client, headers=headers_client)
    response_client_json=response_client.json()
    total_result = response_client_json.get("PaginationResponse").get("TotalResults")
    offset = 0
    count=0
    Id=[]
    while offset <= total_result:
        url_clients = "https://api.mindbodyonline.com/public/v6/client/clients?limit=200&offset="+str(offset)
        response_clients = requests.request("GET", url_clients, headers=headers_client)
        response_clients_json=response_clients.json()
        offset+=200
        for j in response_clients_json["Clients"]:
            Id.append(str(j["Id"]))
            
    for i in Id:
        try:
            url_clientcompleteinfo = "https://api.mindbodyonline.com/public/v6/client/clientcompleteinfo?ClientId="+i
            response_clientcompleteinfo = requests.request("GET", url_clientcompleteinfo, headers=headers_client)
            response_clientcompleteinfo_json=response_clientcompleteinfo.json()
            count+=1
            event = helper.new_event(json.dumps(response_clientcompleteinfo_json,indent=2))
            ew.write_event(event)
        except Exception as e:
            pass
            
    status = response_clientcompleteinfo.status_code
    status = "API="+"https://api.mindbodyonline.com/public/v6/client/clientcompleteinfo"+" | response_code="+str(status)+" | number_of_events="+str(count)
    helper.log_info(status)
        
        
   

      
   