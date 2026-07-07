
# encoding = utf-8

import os
import sys
import time
import datetime
import dateutil.parser
import json
import azure_util.utils as azutil
import azure_util.auth as azauth


def validate_input(helper, definition):
    start_date = definition.parameters.get('start_date')
    if (start_date not in ['',None]):
        try:
            d = dateutil.parser.parse(start_date)
        except Exception as e:
            helper.log_error("_Splunk_ Invalid date format specified for 'Start Date': %s" % start_date)
            raise ValueError("Invalid date format specified for 'Start Date': %s" % start_date)

def get_start_date(helper, check_point_key):
    
    # Try to get a date from the check point first
    d = helper.get_check_point(check_point_key)
    
    # If there was a check point date, retun it.
    if (d not in [None,'']):
        return d
    else:
        # No check point date, so look if a start date was specified as an argument
        start_date = helper.get_arg("start_date")
        if (start_date not in [None,'']):
            if not start_date.endswith("Z"):
                start_date = "%sZ" % start_date
            return start_date
        else:
            # If there was no start date specified, default to 30 days ago
            return (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')

def collect_events(helper, ew):

    global_account = helper.get_arg("azure_app_account")
    client_id = global_account["username"]
    client_secret = global_account["password"]
    tenant_id = helper.get_arg("tenant_id")
    start_date = helper.get_arg("start_date")
    
    environment = helper.get_arg("environment")
    if(environment == "gov"):
        graph_base_url = "https://graph.microsoft.us"
    else:
        graph_base_url = "https://graph.microsoft.com"

    authorization_server_url = "https://login.windows.net/%s/oauth2/token" % tenant_id
    resource = "https://api.security.microsoft.com"
    check_point_key = "m365_incident_lastUpdateTime_%s" % helper.get_input_stanza_names()
    query_date = get_start_date(helper, check_point_key)
    incident_url = "https://api.security.microsoft.com/api/incidents?$filter=lastUpdateTime+gt+%s" % query_date
    
    access_token = azauth.get_access_token(client_id, client_secret, authorization_server_url, resource, helper)
    
    if(access_token):
        helper.log_debug("Incident URL: %s" % incident_url)
        
        max_incident_date = query_date
        
        incidents = azutil.get_atp_alerts_odata(helper, access_token, incident_url, user_agent="M365DPartner-Splunk-M365DefenderAddOn/1.3.0")
        
        for incident in incidents:
            lastUpdateTime = incident["lastUpdateTime"]
            
            if lastUpdateTime > max_incident_date:
                max_incident_date = lastUpdateTime
                
            event = helper.new_event(
                    data=json.dumps(incident),
                    source="%s:%s" % (helper.get_input_type(), tenant_id),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype())
            ew.write_event(event)
            
         # Check point the largest alert lastUpdateTime seen during the query
        helper.save_check_point(check_point_key, max_incident_date)
        
    else:
        raise RuntimeError("Unable to obtain access token. Please check the Application ID, Client Secret, and Tenant ID")
