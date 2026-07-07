
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
    tenant_id = helper.get_arg("tenant_id")
    subscription_sourcetype = helper.get_arg("subscription_sourcetype")
    
    access_token = azauth.get_access_token(global_client_id, global_client_secret, tenant_id)
    
    if(access_token):
        url = "https://management.azure.com/subscriptions?api-version=2016-06-01"

        try:
            subscriptions = azutil.get_items(helper, access_token, url)
        
            for subscription in subscriptions:
                event = helper.new_event(
                    data=json.dumps(subscription),
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=subscription_sourcetype)
                ew.write_event(event)
        except Exception, e:
            raise e
    else:
        raise RuntimeError("Unable to obtain access token. Please check the Client ID, Client Secret, and Tenant ID")