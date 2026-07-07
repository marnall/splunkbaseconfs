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

    api_count=0
    
    ########################### Getting Token ######################################################
    url_token = "https://api.mindbodyonline.com/public/v6/usertoken/issue"
    api_count=api_count+1
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
    api_count=api_count+1
    response_client = requests.request("GET", url_client, headers=headers_client)
    response_client_json=response_client.json()
    total_result = response_client_json.get("PaginationResponse").get("TotalResults")
    offset = 0
    count=0
    # Id=[]
    status=0
    flag=0
    for j in range(0,total_result,200):
        try:
            url_clients = "https://api.mindbodyonline.com/public/v6/client/clients?limit=200&offset="+str(offset)
            api_count=api_count+1
            response_clients = requests.request("GET", url_clients, headers=headers_client)
            response_clients_json=response_clients.json()
            offset+=200
            for k in response_clients_json["Clients"]:
                try:
                    url_clientcompleteinfo = "https://api.mindbodyonline.com/public/v6/client/clientcompleteinfo?ClientId="+str(k["UniqueId"])
                    api_count=api_count+1
                    response_clientcompleteinfo = requests.request("GET", url_clientcompleteinfo, headers=headers_client)
                    response_clientcompleteinfo_json=response_clientcompleteinfo.json()
                    status = response_clientcompleteinfo.status_code
                    if(status==200):
                        checkpoint=str(response_clientcompleteinfo_json.get('Client')['UniqueId'])+ str(response_clientcompleteinfo_json.get('Client')['LastModifiedDateTime'])
                        state = helper.get_check_point(str(checkpoint))
                        flag=1
                        if state is None:
                            event = helper.new_event(json.dumps(response_clientcompleteinfo_json,indent=2))
                            ew.write_event(event)
                            count+=1
                            helper.save_check_point(str(checkpoint), "Indexed")
                        # helper.delete_check_point(str(checkpoint))
                    else:
                        pass
                except Exception as e:
                    pass  
        except Exception as e:
            pass
    
    # eve = helper.new_event(str(count))
    # ew.write_event(eve)
    
    if(flag==1):
        status=200
    else:
        status = response_clientcompleteinfo.status_code
        
    status = f"The API=https://api.mindbodyonline.com/public/v6/client/clientcompleteinfo | response_code={status} | number_of_events={count} | API_Hit_Count={api_count}"
    helper.log_info(status)
    # for j in range(0,total_result,200):
    #     try:
    #         url_clients = f"https://api.mindbodyonline.com/public/v6/client/clients?limit=200&offset={offset}"
    #         response_clients = requests.request("GET", url_clients, headers=headers_client)
    #         response_clients_json=response_clients.json()
    #         offset+=200
            
    #         for k in response_clients_json["Clients"]:
    #             Id.append(str(k["UniqueId"]))
    #     except Exception as e:
    #         pass
            
  
    # IdLength = len(Id)
    # increment=0
        
    # for l in range(0,IdLength):
    #     try:
    #         url_clientcompleteinfo = f"https://api.mindbodyonline.com/public/v6/client/clientcompleteinfo?ClientId={Id[increment]}"
    #         response_clientcompleteinfo = requests.request("GET", url_clientcompleteinfo, headers=headers_client)
    #         response_clientcompleteinfo_json=response_clientcompleteinfo.json()
    #         increment+=1
    #         checkpoint=str(response_clientcompleteinfo_json.get('Client')['UniqueId'])+ str(response_clientcompleteinfo_json.get('Client')['LastModifiedDateTime'])
            # state = helper.get_check_point(str(checkpoint))
            # if state is None:
            #     event = helper.new_event(json.dumps(response_clientcompleteinfo_json,indent=2))
            #     ew.write_event(event)
            #     count+=1
            #     helper.save_check_point(str(checkpoint), "Indexed")
            # helper.delete_check_point(str(checkpoint))
    #     except Exception as e:
    #         pass
        
    # even = helper.new_event(str(count))
    # ew.write_event(even)
            
    # status = response_clientcompleteinfo.status_code
    # status = f"The API=https://api.mindbodyonline.com/public/v6/client/clientcompleteinfo | response_code={status} | number_of_events={count}"
    # helper.log_info(status)
        
        
   

      
   