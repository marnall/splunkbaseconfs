
# encoding = utf-8

import os
import sys
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
    # client_id = definition.parameters.get('client_id', None)
    # tenant_id = definition.parameters.get('tenant_id', None)
    pass

def get_bearer_token(helper, client_id, client_secret, tenant_id):
    
    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        
        helper.log_info("Obtaining access token...")
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_info = response.json()
        
        helper.log_info(f"Access token for client id {client_id} has been granted...")
        
        return token_info['access_token']
    except requests.RequestException as e:
        helper.log_error(f"Error obtaining token: {e}")
        return None

def get_application_details(helper, access_token, query_parameters):
    """Retrieve details of Azure applications"""
    
    graph_url = 'https://graph.microsoft.com/v1.0/applications'
    
    helper.log_info(f"Performing MS Graph API query 'GET /applications'")
    
    query_parameters = None if query_parameters == '' else query_parameters
    
    if query_parameters is not None:
        graph_url = f'{graph_url}?{query_parameters}'
        helper.log_info(f"Performing MS Graph API query with params: {query_parameters}")
    
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }
    
    all_apps = []
    response = requests.get(graph_url, headers=headers)

    if response.status_code == 200:
        apps_details = response.json()
        all_apps.extend(apps_details['value'])

        # Check if there are more pages
        while '@odata.nextLink' in apps_details:
            next_link = apps_details['@odata.nextLink']
            response = requests.get(next_link, headers=headers)
            
            if response.status_code == 200:
                apps_details = response.json()
                all_apps.extend(apps_details['value'])
            else:
                print(response.text)
                break

        return all_apps
    else:
        helper.log_error("Failed to retrieve application details: " + response.text)
        return None

def collect_events(helper, ew):
    
    opt_global_account = helper.get_arg('client_id')
    client_id = opt_global_account['username']
    client_secret = opt_global_account['password']
    tenant_id = helper.get_arg('tenant_id')
    query_parameters = helper.get_arg('query_parameters')
    meta_source = f'ms_aad_apps:tenant_id:{tenant_id}'

    llvl = helper.get_log_level()
    
    helper.set_log_level(llvl)
    helper.log_info(f"Loging level is set to: {llvl}")
    helper.log_info(f"Start of collection.")
    
    token = get_bearer_token(helper, client_id, client_secret, tenant_id)
    
    if token is None:
        helper.log_error("No access token. Exiting this collection.")
        return None
    
    apps = get_application_details(helper, token, query_parameters)
    
    total_apps = len(apps)
    
    if apps is None or total_apps < 1:
        helper.log_error("No App Registration Details retrieved. Exiting this collection.")
        return None
        
    total_events = 0
    
    for app in apps:
        
        if len(app) == 0:
            continue
        
        app['tenantId'] = tenant_id
        
        data_event = json.dumps(app, separators=(',', ':'))
        event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data_event)
        ew.write_event(event)
        total_events = total_events + 1
    
    if total_events == 0:
        helper.log_warning(f'Total events indexed was 0. This could mean an invalid query parameter was entered or something is wrong in this App ID\'s permissions. End of collection.')
    else:
        helper.log_info(f"Ingestion of all (total={total_events}) Application Registration was successful. End of collection.")
    
    
