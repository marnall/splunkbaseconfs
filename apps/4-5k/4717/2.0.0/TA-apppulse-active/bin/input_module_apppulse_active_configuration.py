# encoding = utf-8

import os
import sys
import time
import json, requests, base64
from datetime import datetime
     
def validate_input(helper, definition):
    
    pass
	
def collect_events(helper, ew):

    global_account = helper.get_arg('tenant')
    
    client_id = global_account['username']
    client_secret = global_account['password']
    
    saas_domain = helper.get_global_setting('saas_domain')
    tenant_id = helper.get_global_setting('tenant_id')

    endpoint_token = "https://" + saas_domain + "/openapi/rest/v1/" + tenant_id + "/oauth/token"

    headers_token = {'Content-Type': 'application/json' }

    data_token = {
        'clientSecret': client_secret,
        'clientId': client_id
    }

    # Get Auth Token
    try:

        response_token = requests.post(endpoint_token, data=json.dumps(data_token), headers=headers_token)

        response_token_json = response_token.json()

        auth_token = response_token_json["token"]

    except:
        # HTTP GET Request Error Handling
        helper.log_error('Status Code :' + str(response_token.status_code))

    # Configure and Format the Headers
    headers_configuration = {"Authorization": 'Bearer ' + auth_token}

    # REST Endpoint [getConfiguration]
    endpoint_configuration = "https://" + saas_domain + "/openapi/rest/v1/" + tenant_id + "/getConfiguration"

    # Get Configuration
    try:

        # HTTP GET [getConfiguration]
        response_configuration = requests.get(endpoint_configuration, headers=headers_configuration)

        # Store Response as a JSON Dict Object
        response_configuration_json = response_configuration.json()

        # Loop Through the Monitored Applications
        for application in response_configuration_json["applications"]:

            # Serialize the JSON Dict Object
            data_application = json.dumps(application)

            # Save and Write the Serialized Object
            event = helper.new_event(data_application, time=datetime.now(), host="https://" + saas_domain, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), source='getConfiguration', done=True, unbroken=True)
            ew.write_event(event)

    except:
        # HTTP GET Request Error Handling
        helper.log_error('Status Code :' + str(response_configuration.status_code))