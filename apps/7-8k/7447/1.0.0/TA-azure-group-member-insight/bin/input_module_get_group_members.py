
# encoding = utf-8

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
    # group_display_name_keyword = definition.parameters.get('group_display_name_keyword', None)
    # global_account = definition.parameters.get('global_account', None)
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

def get_search_matched_groups(helper, access_token, keyword):
    
    graph_url = 'https://graph.microsoft.com/v1.0/'
    groups = graph_url + f'groups/?$search="displayName:{keyword}"'
    
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json',
        'ConsistencyLevel': 'eventual'
    }

    all_groups = []
    
    helper.log_info(f'Retrieving all groups matching "{keyword}". Full API uri and params: GET {groups}')

    response = requests.get(groups, headers=headers)
    
    page_counter = 1

    if response.status_code == 200:
        group_members_details = response.json()
        all_groups.extend(group_members_details['value'])

        while '@odata.nextLink' in group_members_details:
            
            page_counter = page_counter + 1
            
            if page_counter == 2:
                helper.log_info(f"Groups that match {keyword} have multiple pages.")
            
            next_link = group_members_details['@odata.nextLink']
            response = requests.get(next_link, headers=headers)
            
            if response.status_code == 200:
                group_members_details = response.json()
                all_groups.extend(group_members_details['value'])
            else:
                helper.log_error(f'Error occurred. Status={str(response.status_code)}', response.text)
                continue
        
        if page_counter > 1:
            helper.log_info(f"Finished collecting Groups that match {keyword} at page {str(page_counter)}.")
        
        return all_groups
        
    else:
        helper.log_error(f'Error occurred. Status={str(response.status_code)}', response.text)
        

def get_group_members(helper, access_token, group_id):
    
    graph_url = 'https://graph.microsoft.com/v1.0/'
    group_members_url = graph_url + f'groups/{group_id}/members?$select=id,userPrincipalName,displayName,jobTitle,accountEnabled'

    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }

    all_group_members_details = []
    
    helper.log_info(f"Retrieving members of {group_id}")

    response = requests.get(group_members_url, headers=headers)
    
    page_counter = 1

    if response.status_code == 200:
        group_members_details = response.json()
        all_group_members_details.extend(group_members_details['value'])

        while '@odata.nextLink' in group_members_details:
            
            page_counter = page_counter + 1
            
            if page_counter == 2:
                helper.log_info(f"Group {group_id} has multiple pages.")
            
            next_link = group_members_details['@odata.nextLink']
            response = requests.get(next_link, headers=headers)
            if response.status_code == 200:
                group_members_details = response.json()
                all_group_members_details.extend(group_members_details['value'])
            else:
                helper.log_error(f'Error occurred. Status={str(response.status_code)}', response.text)
                continue
        
        if page_counter > 1:
            helper.log_info(f"Group {group_id} ended collecting all members at page {str(page_counter)}.")
        
        return all_group_members_details

    else:
        helper.log_error(f'Error occurred. Status={str(response.status_code)}', response.text)


def collect_events(helper, ew):
    
    opt_global_account = helper.get_arg('global_account')
    client_id = opt_global_account['username']
    client_secret = opt_global_account['password']
    tenant_id = helper.get_arg('tenant_id')
    gdnsk = helper.get_arg('group_display_name_keyword')
    
    llvl = helper.get_log_level()
    
    helper.set_log_level(llvl)
    
    helper.log_info(f"Loging level is set to: {llvl}")
    
    helper.log_info(f"Members of group matching '{gdnsk}'. Start of collection.")
    
    token = get_bearer_token(helper, client_id, client_secret, tenant_id)
    
    matched_groups = get_search_matched_groups(helper, token, gdnsk)
    
    total_groups = len(matched_groups)
    
    if total_groups < 1: 
        helper.log_warning(f'No groups matched the keyword "{gdnsk}". Disable this collection method or change the keyword. End of collection.')
        return None
    
    helper.log_info(f"Collected {str(total_groups)} Groups. Retrieval of members from each group begins here...")
    
    meta_source = f"ms_aad_user:tenant_id:{tenant_id}"
    
    for group in matched_groups:
        
        gid = group['id']
        dn = group['displayName']
        current_group = get_group_members(helper, token, gid)
        
        total_members = len(current_group)
        
        if total_members < 1: 
            helper.log_warning(f"Group {gid} has no members. Skipping this.")
            continue
        
        for cg in current_group:
            cg['memberOfGroupId'] = gid
            cg['memberOfGroupDisplayName'] = dn
            
            data_event = json.dumps(cg, separators=(',', ':'))
            event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data_event)
            ew.write_event(event)
    
    helper.log_info(f"Ingestion of all users was successful. End of collection.")
        
