# encoding = utf-8

import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    opt_airlock_server_url = helper.get_global_setting('airlock_server_url')
    opt_airlock_rest_api_port = helper.get_global_setting('airlock_rest_api_port')
    opt_airlock_rest_api_key = helper.get_global_setting('airlock_rest_api_key')
    opt_airlock_tenant_id = helper.get_global_setting('airlock_tenant_id')
    opt_airlock_directory_id = helper.get_global_setting('airlock_directory_id')

    local_airlock_directory_id = helper.get_arg("local_airlock_cloud_directoryid")
    local_airlock_tenantid = helper.get_arg("local_airlock_cloud_tenantid")
   
    helper.get_input_stanza()
    proxy_settings = helper.get_proxy()

    # Sanitize the URL
    if opt_airlock_server_url.startswith("https://"):
        opt_airlock_server_url = opt_airlock_server_url[len("https://"):]
    opt_airlock_server_url = opt_airlock_server_url.split("/")[0]

    # Check if the FQDN contains "appenforcement.com" and modify the URL if needed
    if "appenforcement.com" in opt_airlock_server_url:
        if opt_airlock_server_url.startswith("portal."):
            opt_airlock_server_url = opt_airlock_server_url[len("portal."):]
        endpoint = "/willard/v1/agent/find"
        headers = {
                "UserApiKey": opt_airlock_rest_api_key, 
                "directoryid": (local_airlock_directory_id if local_airlock_directory_id else opt_airlock_directory_id),
                "tenantID": (local_airlock_tenantid if local_airlock_tenantid else opt_airlock_tenant_id)
            }
    else:
        #On-prem/hosted
        endpoint = "/v1/agent/find"
        headers = {
                "X-ApiKey": opt_airlock_rest_api_key
            }
        
    url = "https://" + opt_airlock_server_url + (":" + opt_airlock_rest_api_port if opt_airlock_rest_api_port else "") + endpoint

    ###
    #IF RUNNING ON PREM AIRLOCK WITH SELF SIGNED CERT
    ###

    #1. Put ca.crt (AirlockCA) in `/opt/splunk/etc/auth/mycerts/`. This can be obtained from the settings menu in the Airlock console under the 'other' tab.
    #2. Replace line below - verify="/opt/splunk/etc/auth/mycerts/ca.crt"
    #3. Errors will be logged and can be seen by running a search:
    #   index=_internal sourcetype="taairlockdigitalrestapiloggercloud:log"

    response = helper.send_http_request(
        url, 
        method="POST", 
        parameters=None, 
        headers=headers, 
        cookies=None, 
        verify=True, 
        cert=None, 
        timeout=None, 
        use_proxy=True
    )

    r_json = response.json()

    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()


    for i in r_json['response']['agents']:
        agents=i
        event = helper.new_event(source=helper.get_input_stanza_names(), index=helper.get_output_index(), sourcetype="airlock:agent", data=json.dumps(agents),unbroken=True,time=time.time())
        ew.write_event(event)