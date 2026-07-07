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

    opt_organization = helper.get_arg('organization')
    opt_personal_access_token = helper.get_arg('personal_access_token')
    opt_index_name = helper.get_arg('index')
    opt_sourcetype_name = helper.get_arg('sourcetype')

    # Use Azure DevOps API Version 4.1
    api_version = '?api-version=4.1'

    # Base64 Encode the Personal Access Token
    encoded_pat = base64.b64encode(":".encode("UTF-8") + opt_personal_access_token.encode("UTF-8"))

    # Set the Header Authentication String
    api_authorization = 'Basic ' + encoded_pat.decode("UTF-8")

    # Configure and Format the Headers
    headers = {'Content-Type': 'application/json',
            'Authorization': api_authorization }

    # REST Endpoint for All Projects Under the Organization
    endpoint_projects = 'https://dev.azure.com/' + opt_organization + '/_apis/projects'

    url_projects = endpoint_projects + api_version

    # HTTP GET
    response_projects = requests.get(url_projects, headers=headers)

    # HTTP GET Request Error Handling
    if response_projects.status_code != 200:
        # This means something went wrong.
        raise Exception('Status Code {}'.format(response_projects.status_code))

    # Store Response as a JSON Dict Object
    projects = response_projects.json()

     # Serialize the JSON Dict Object
    data_projects = json.dumps(projects)

    # Save and Write the Serialized Object
    event = helper.new_event(data_projects, time=datetime.now(), host='https://vsrm.dev.azure.com', index=opt_index_name, source=opt_organization, sourcetype=opt_sourcetype_name, done=True, unbroken=True)
    ew.write_event(event)

    # Loop Through the Projects Under the Organization
    for project in projects["value"]:
        project_name = project["name"]

        # REST Endpoint for All Release Definitions Under the Organization
        endpoint_release_definitions = 'https://vsrm.dev.azure.com/' + opt_organization + '/' + project_name + '/_apis/release/definitions'

        # REST API Endpoint and Version
        url_release_definitions = endpoint_release_definitions  + api_version

        # HTTP GET Request Error Handling
        try:
            # HTTP GET
            response_release_definitions = requests.get(url_release_definitions, headers=headers)

            # Store Response as a JSON Dict Object
            release_definitions = response_release_definitions.json()

            # Serialize the JSON Dict Object
            data_release_definitions = json.dumps(release_definitions)

            # Save and Write the Serialized Object
            event = helper.new_event(data_release_definitions, time=datetime.now(), host='https://vsrm.dev.azure.com', index=opt_index_name, source=opt_organization + ':' + project_name, sourcetype=opt_sourcetype_name, done=True, unbroken=True)
            ew.write_event(event)

        except:
            # HTTP GET Request Error Handling
            helper.log_error('Status Code :' + response_release_releases.status_code)

        # Loop Through the Release Definitions Under Each Project
        for release_definition in release_definitions["value"]:
            
            # REST Endpoint for All Release Definitions Under the Organization
            endpoint_release_releases = 'https://vsrm.dev.azure.com/' + opt_organization + '/' + project_name + '/_apis/release/releases'

            # REST API Endpoint, Version, and Release Definition ID
            url_release_releasess = endpoint_release_releases  + api_version + '&releaseId=' + str(release_definition["id"])
            
            try:
                # HTTP GET
                response_release_releases = requests.get(url_release_releasess, headers=headers)

                # Store Response as a JSON Dict Object
                release_releases = response_release_releases.json()

            except:
                # HTTP GET Request Error Handling
                helper.log_error('Status Code: ' + response_release_releases.status_code)
            
            try:
                releaseId = release_releases["id"]

                # Serialize the JSON Dict Object
                data_release_releases = json.dumps(release_releases)

                # Save and Write the Serialized Object
                event = helper.new_event(data_release_releases, time=datetime.now(), host='https://vsrm.dev.azure.com', index=opt_index_name, source=project_name + ':' + release_definition["name"], sourcetype=opt_sourcetype_name, done=True, unbroken=True)
                ew.write_event(event)

            except:
                # HTTP GET Request Error Handling
                helper.log_error('Exception :' + release_releases["message"])
                helper.log_error('Exception :' + release_releases["typeName"])