
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
    
    alert_api_version = "2015-06-01-preview"
    alert_sourcetype = helper.get_arg("security_alert_sourcetype")
    collect_alerts = helper.get_arg("collect_security_center_alerts")
    
    task_api_version = "2015-06-01-preview"
    task_sourcetype = helper.get_arg("security_task_sourcetype")
    collect_tasks = helper.get_arg("collect_security_center_tasks")
    
    access_token = azauth.get_access_token(global_client_id, global_client_secret, tenant_id)
    
    if(access_token):
        
        if(collect_alerts):
            helper.log_debug("Collecting security alert data. sourcetype='%s'" % alert_sourcetype)
            url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Security/alerts?api-version=%s" % (subscription_id, alert_api_version)
            alerts = azutil.get_items(helper, access_token, url)
            for alert in alerts:
                event = helper.new_event(
                    data=json.dumps(alert),
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=alert_sourcetype)
                ew.write_event(event)
                
        if(collect_tasks):
            helper.log_debug("Collecting security task data. sourcetype='%s'" % task_sourcetype)
            url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Security/tasks?api-version=%s" % (subscription_id, task_api_version)
            tasks = azutil.get_items(helper, access_token, url)
            for task in tasks:
                event = helper.new_event(
                    data=json.dumps(task),
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=task_sourcetype)
                ew.write_event(event)
    else:
        raise RuntimeError("Unable to obtain access token. Please check the Client ID, Client Secret, and Tenant ID")