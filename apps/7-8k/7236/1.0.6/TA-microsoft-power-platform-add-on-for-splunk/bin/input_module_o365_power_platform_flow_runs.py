
# encoding = utf-8

import os
import sys
import time
import json
import datetime
import requests

from o365_power_platform_main import get_access_token, get_api_data, API_VERSION


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    opt_client_id = helper.get_arg('client_id')
    opt_tenant_id = helper.get_arg('tenant_id')
    opt_client_secret = helper.get_arg('client_secret')
    
    ms_url = f"https://login.microsoftonline.com/{opt_tenant_id}/oauth2/v2.0/token"
    resource = "https://service.flow.microsoft.com"
    scope = f"{resource}/.default"

    data = {
        'client_id': opt_client_id,
        'client_secret': opt_client_secret,
        'grant_type': 'client_credentials',
        'scope': scope
    }
    
    def get_env_ids():
        ms_url = f"https://login.microsoftonline.com/{opt_tenant_id}/oauth2/v2.0/token"
        resource = "https://api.bap.microsoft.com"
        scope = f"{resource}/.default"
    
        url = f"{resource}/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments?api-version={API_VERSION}"
        
        data = {
            'client_id': opt_client_id,
            'client_secret': opt_client_secret,
            'grant_type': 'client_credentials',
            'scope': scope
        }
    
        token = get_access_token(data, ms_url)
        env_data = get_api_data(token, url)
        env_data = json.loads(env_data)
        
        envs = []
        
        for env in env_data["value"]:
            envs.append(env["name"])
        
        return envs
    
    def get_flow_runs(env_id, flow_id):
        if not flow_id:
            # Skip if flow_id is blank
            return []

        url = f"https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/scopes/admin/environments/{env_id}/flows/{flow_id}/runs?api-version={API_VERSION}"
        token = get_access_token(data, ms_url)
        flow_runs_data = get_api_data(token, url)
        flow_runs_data = json.loads(flow_runs_data)
        return flow_runs_data.get("value", [])

            
    envs = get_env_ids()

    token = get_access_token(data, ms_url)
    
    final_result = []

    for env_id in envs:
        url = f"https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/scopes/admin/environments/{env_id}/flows?api-version={API_VERSION}"

        env_data = get_api_data(token, url)
        env_data = json.loads(env_data)

        for flow in env_data["value"]:
            flow_id = flow["name"]

            flow_runs = get_flow_runs(env_id, flow_id)

            for flow_run in flow_runs:
                # Process flow run data as needed
                flow_run_id = flow_run["id"]

                # Check if the event is already indexed
                state = helper.get_check_point(flow_run_id)
                if state is None:
                    final_result.append(flow_run)
                    # Save the checkpoint to mark the event as indexed
                    helper.save_check_point(flow_run_id, "Indexed")

                # Cleanup - delete checkpoint for the last environment
                #helper.delete_check_point(flow_run_id)

    # Create a Splunk event for each flow run
    res = json.dumps(final_result)
    event = helper.new_event(res, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    ew.write_event(event)
