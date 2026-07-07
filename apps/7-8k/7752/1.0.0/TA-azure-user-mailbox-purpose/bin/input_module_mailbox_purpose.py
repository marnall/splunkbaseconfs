
# encoding = utf-8

import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_access_token(helper, client_id, client_secret, token_url):
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    
    helper.log_info("Retrieving access token from Graph.")
    
    try:
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_info = response.json()
        
        helper.log_info(f"Access token for client id {client_id} has been granted...")
        
        return token_info['access_token']
    except requests.RequestException as e:
        helper.log_error(f"Error obtaining token: {e}")
        return None

def get_all_users(helper, token, url):
    
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    
    if response.status_code > 200:
        return None
    
    response.raise_for_status()
    
    data = response.json()

    next_url = data.get("@odata.nextLink")

    return data.get("value", []), next_url

def get_user_purpose(helper, user_id, token):
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailboxSettings/userPurpose"
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        response = requests.get(url, headers=headers)

        if response.status_code == 429:  # Rate limit hit
            retry_after = int(response.headers.get("Retry-After", 10))
            helper.log_error(f"Rate limited for {user_id}. Retrying in {retry_after} sec...")
            time.sleep(retry_after)
            continue

        if response.status_code == 200:
            user_purpose = response.json().get("value")
            if user_purpose in ('linked', 'shared', 'room', 'equipment', 'others'):
                return user_purpose 
            else:
                return None

        return None

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    
    CLIENT_ID = helper.get_arg('app_client_id')
    CLIENT_SECRET = helper.get_arg('client_secret')
    TENANT_ID = helper.get_arg('tenant_id')
    
    TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0/users?$select=id,userPrincipalName,mail&$filter=userType eq 'Member'&"
    
    log_level = helper.get_log_level()
    
    helper.set_log_level(log_level)
    
    helper.log_info(f"Start of collection.")
    helper.log_info(f"Logging level is set to: {log_level}")
    helper.log_info(f"Collecting Azure Entra ID user objects' mailboxSettings-->userPurpose from Azure tenant {TENANT_ID}, using app/client {CLIENT_ID}")
    
    token = get_access_token(helper, CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    meta_source = f"ms_aad_user:tenant_id:{TENANT_ID}"
    
    ctr = 0
    
    helper.log_info("Concurrent Futures, multi-thread API calls start here.")
    
    next_url = GRAPH_API_URL
    
    while next_url:
        
        helper.log_info(f"Getting all users. Will start indexing data for every pagination.")
        
        users, next_url = get_all_users(helper, token, GRAPH_API_URL)
    
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_user = {executor.submit(get_user_purpose, helper, user["id"], token): user for user in users}

            for future in as_completed(future_to_user):
                user = future_to_user[future]
                try:
                    user_purpose = future.result()
                    if user_purpose:
                        
                        user["mailboxSettingsUserPurpose"] = user_purpose
                        
                        data_event = json.dumps(user, separators=(',', ':'))
                        event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data_event)
                        
                        ctr = ctr + 1
                        
                        ew.write_event(event)
                        
                except Exception as e:
                    helper.log_error(f"Error processing user {user['id']}: {e}")
    
    helper.log_info(f"ThreadPoolExecutor has completed for all possible API calls. Total events ingested: {ctr}.")
    helper.log_info("End of collection.")
    