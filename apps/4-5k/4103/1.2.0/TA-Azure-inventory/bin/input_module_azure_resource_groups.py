
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
import azure.utils as azutil
import azure.auth as azauth

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    subscription_id = helper.get_arg("subscription_id")
    tenant_id = helper.get_arg("tenant_id")
    
    resource_group_api_version = "2018-05-01"
    
    access_token = azauth.get_access_token(global_client_id, global_client_secret, tenant_id)
    
    if(access_token):
        
        helper.log_debug("Collecting resource group data.")
        url = "https://management.azure.com/subscriptions/%s/resourcegroups?api-version=%s" % (subscription_id, resource_group_api_version)
        resource_groups = azutil.get_items(helper, access_token, url)
        for resource_group in resource_groups:
            event = helper.new_event(
                data=json.dumps(resource_group),
                source=helper.get_input_type(), 
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype())
            ew.write_event(event)

    else:
        raise RuntimeError("Unable to obtain access token. Please check the Client ID, Client Secret, and Tenant ID")
        