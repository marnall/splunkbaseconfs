# encoding = utf-8

import os
import sys
import time
import datetime
import json, requests, base64
from pprint import pprint
from datetime import datetime

def validate_input(helper, definition):
    organization = definition.parameters.get('organization', None)
    personal_access_token = definition.parameters.get('personal_access_token', None)

    if (not organization) and (not personal_access_token):
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
    endpoint_projects_list = 'https://dev.azure.com/' + opt_organization + '/_apis/projects' + '?' + api_version

    # HTTP GET
    response_projects = requests.get(endpoint_projects_list, headers=headers)

    # HTTP GET Request Error Handling
    if response_projects.status_code != 200:
        # This means something went wrong.
        raise Exception('Status Code {}'.format(response_projects.status_code))

    # Store Response as a JSON Dict Object
    projects = response_projects.json()

    # Loop Through the Projects Under the Organization
    for project in projects["value"]:
        project_name = project["name"]

        continuationToken = 0

        while continuationToken != None:

            # REST Endpoint [Release - Releases - List]
            endpoint_release_releases = 'https://vsrm.dev.azure.com/' + opt_organization + '/' + project_name + '/_apis/release/releases' + '?' + api_version

            if continuationToken != None:
                endpoint_release_releases = endpoint_release_releases + '&continuationToken=' + str(continuationToken)

            # HTTP GET Request Error Handling
            try:
                # HTTP GET 
                response_release_releases = requests.get(endpoint_release_releases, headers=headers)

            except:
                # HTTP GET Request Error Handling
                helper.log_error('Status Code :' + response_release_releases.status_code)

            else:

                # Store Response as a JSON Dict Object
                release_releases = response_release_releases.json()

                continuationToken = response_release_releases.headers.get('x-ms-continuationtoken')

                for release in release_releases["value"]:
                    releaseID = release["id"]

                    # REST Endpoint [Release - Releases - Get Release]
                    endpoint_release_getrelease = 'https://vsrm.dev.azure.com/' + opt_organization + '/' + project_name + '/_apis/release/releases/' + str(releaseID) + '?' + api_version

                    # HTTP GET Request Error Handling
                    try:
                        # HTTP GET 
                        response_release_getrelease = requests.get(endpoint_release_getrelease, headers=headers)

                    except:
                        # HTTP GET Request Error Handling
                        helper.log_error('Status Code :' + response_release_getrelease.status_code)

                    else:
                        # Store Response as a JSON Dict Object
                        release_getrelease = response_release_getrelease.json()

                        # Serialize the JSON Dict Object
                        data_release_getrelease = json.dumps(release_getrelease)
                        
                        # Save and Write the Serialized Object
                        event = helper.new_event(data_release_getrelease, time=datetime.now(), host='https://vsrm.dev.azure.com', index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), source=opt_organization + ':' + project_name, done=True, unbroken=True)
                        ew.write_event(event)