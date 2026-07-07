# encoding = utf-8

import os
import sys
import time
import datetime
import json, requests, base64
from pprint import pprint
from datetime import datetime

def validate_input(helper, definition):
    opt_organization = helper.get_arg('organization')
    opt_personal_access_token = helper.get_arg('personal_access_token')

    if (not opt_organization) and (not opt_personal_access_token):
        pass
    else:
        helper.log_critical("Invalid Organization or PAT")

def collect_events(helper, ew):

    global_account = helper.get_arg('organization')
    
    opt_organization = global_account['username']
    opt_personal_access_token = global_account['password']
    
    opt_personal_access_token = ':' + str(opt_personal_access_token)
    
    # Use Azure DevOps API Version 5.1
    api_version = 'api-version=5.1'

    # Base64 Encode the Personal Access Token
    encoded_pat = base64.b64encode(opt_personal_access_token.encode("UTF-8"))

    # Set the Header Authentication String
    api_authorization = 'Basic ' + encoded_pat.decode("UTF-8")

    # Configure and Format the Headers
    headers = {'Content-Type': 'application/json',
            'Authorization': api_authorization }

    # REST Endpoint [Projects - List]
    endpoint_projects_list = 'https://dev.azure.com/' + str(opt_organization) + '/_apis/projects' + '?' + api_version

    # HTTP GET [Projects - List]
    response_projects_list = requests.get(endpoint_projects_list, headers=headers)

    # HTTP GET Request Error Handling
    if response_projects_list.status_code != 200:
        # This means something went wrong.
        raise Exception('Status Code {}'.format(response_projects_list.status_code))

    # Store Response as a JSON Dict Object
    projects_list = response_projects_list.json()

    # Loop Through the Projects Under the Organization
    for project in projects_list["value"]:
        project_name = project["name"]

        continuationToken = 0
        
        while continuationToken != None:
            
            # REST Endpoint [Release - Approvals - List]
            endpoint_approvals_list = 'https://vsrm.dev.azure.com/' + opt_organization + '/' + project_name + '/_apis/release/approvals' + '?' + api_version

            if continuationToken != None:
                endpoint_approvals_list = endpoint_approvals_list + '&continuationToken=' + str(continuationToken)

            # HTTP GET Request Error Handling
            try:
                # HTTP GET [Release - Approvals - List]
                response_approvals_list = requests.get(endpoint_approvals_list, headers=headers)

            except:
                # HTTP GET Request Error Handling
                helper.log_error('Status Code :' + response_approvals_list.status_code)

            else:
                # Store Response as a JSON Dict Object
                approvals_list = response_approvals_list.json()

                continuationToken = response_approvals_list.headers.get('x-ms-continuationtoken')

                # Serialize the JSON Dict Object
                data_approvals_list = json.dumps(approvals_list)
                
                # Write event if number of JSON events is > 0
                if int(approvals_list['count']) > 0:
                    # Save and Write the Serialized Object
                    event = helper.new_event(data_approvals_list, time=datetime.now(), host='https://vsrm.dev.azure.com', index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), source=opt_organization + ':' + project_name, done=True, unbroken=True)
                    ew.write_event(event)