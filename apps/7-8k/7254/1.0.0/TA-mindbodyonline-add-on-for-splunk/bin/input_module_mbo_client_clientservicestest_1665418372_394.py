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
    # start_date = helper.get_arg('start_date')
    # end_date = helper.get_arg('end_date')
    
    
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
        
    ############################### Client Services API #########################################################

    headers_client = {
        'User-Agent': opt_app_source_name,
        'Api-Key': opt_api_key,
        'Authorization': token,
        'Content-Type': 'application/json',
        'SiteId': opt_siteid
    }
    
    headers_service = {
        'User-Agent': opt_app_source_name,
        'Api-Key': opt_api_key,
        'Content-Type': 'application/json',
        'SiteId': opt_siteid
    }
    
    # client_services_dataset=[]
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
            url_client_services = "https://api.mindbodyonline.com/public/v6/client/clientservices?ClientId="+i
            response_client_services = requests.request("GET", url_client_services, headers=headers_service)
            response_client_services_json=response_client_services.json()
            for j in response_client_services_json["ClientServices"]:
                state = helper.get_check_point(str(j['Id']))
                if state is None:
                    # client_services_dataset.append(j)
                    event = helper.new_event(json.dumps(j))
                    ew.write_event(event)
                    helper.save_check_point(str(j['Id']), "Indexed")
                    count+=1
                # helper.delete_check_point(str(j['Id']))
        except Exception as e:
            pass
       
 
    status = response_client_services.status_code
    status = f"API=https://api.mindbodyonline.com/public/v6/client/clientservices | response_code={status} | number_of_events={count}"
    helper.log_info(status)

