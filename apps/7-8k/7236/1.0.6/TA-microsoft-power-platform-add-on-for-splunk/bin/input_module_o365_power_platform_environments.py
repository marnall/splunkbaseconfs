
# encoding = utf-8

import os
import sys
import time
import json
import datetime
import requests

from o365_power_platform_main import get_access_token, get_api_data, API_VERSION


RESOURCE = "https://api.bap.microsoft.com"
SCOPE = f'{RESOURCE}/.default'

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # scope = definition.parameters.get('scope', None)
    # client_id = definition.parameters.get('client_id', None)
    # tenant_id = definition.parameters.get('tenant_id', None)
    # client_secret = definition.parameters.get('client_secret', None)
    pass

def collect_events(helper, ew):
    opt_client_id = helper.get_arg('client_id')
    opt_tenant_id = helper.get_arg('tenant_id')
    opt_client_secret = helper.get_arg('client_secret')
    
    ms_url = f"https://login.microsoftonline.com/{opt_tenant_id}/oauth2/v2.0/token"


    url = f"{RESOURCE}/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments?api-version={API_VERSION}"#&$expand=properties.capacity,properties.addons"
    
    data = {
        'client_id': opt_client_id,
        'client_secret': opt_client_secret,
        'grant_type': 'client_credentials',
        'scope': SCOPE
    }

    # generate access token
    token = get_access_token(data, ms_url)
    # get and transform data
    env_data = get_api_data(token, url)
    env_data = json.loads(env_data)

    final_result = []
    
    for env in env_data["value"]:
        state = helper.get_check_point(str(env["name"]))
        if state is None:
            final_result.append(env)
            helper.save_check_point(str(env["name"]), "Indexed")
        #helper.delete_check_point(env["name"])
    
    res = json.dumps(final_result)
    # To create a splunk event
    event = helper.new_event(res, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    ew.write_event(event)