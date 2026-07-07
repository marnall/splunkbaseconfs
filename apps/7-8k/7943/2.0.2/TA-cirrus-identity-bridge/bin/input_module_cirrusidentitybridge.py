# encoding = utf-8

import os
import sys
import time
import datetime
import json
import base64
current_value=None
# Get your add-on's local directory
local_dir = os.path.join(
    os.environ['SPLUNK_HOME'], 
    'etc', 
    'apps', 
    'TA-cirrus-identity-bridge', 
    'local'
)

os.makedirs(local_dir, exist_ok=True)

file_path = os.path.join(local_dir, 'persistent_vars.json')
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    current_value = data.get('token')
else:
    data = {'token': None}
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
def validate_input(helper, definition):
    """Validate the API URL is provided."""
    api_url = definition.parameters.get("domain", None)
    if not api_url:
        raise ValueError("The 'domain' parameter (API URL) is required.")

def collect_events(helper, ew):
    # Hardcoded base URL
    base_url = "https://api.cirrusidentity.com/logs/v1/orgLogs"
    with open(file_path, 'r') as f:
        current_value=json.load(f).get("token")
    if current_value is not None:
        creds = helper.get_arg('global_account')
        username = creds.get('username')
        password = creds.get('password')
        auth_str = f"{username}:{password}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {b64_auth}"
        }
        org_url = helper.get_arg('domain')  # Example: https://ww.institution.edu/

        # Construct final URL with raw orgUrl (not URL-encoded)
        final_url = f"{base_url}?orgUrl={org_url}&nextToken={current_value}"

        # Get user-provided domain (used as orgUrl query param)
   
  
        if not username or not password:
            helper.log_error("Credentials are missing username or password fields")
            return

        try:
            helper.log_info(f"Requesting Cirrus logs from: {final_url}")

            response = helper.send_http_request(
                final_url,
                method="GET",
                headers=headers,
                timeout=30,
                use_proxy=True
            )

            response.raise_for_status()
    
            # Parse the response
            data = response.json()
            helper.log_info(f"Response JSON: {json.dumps(data)[:500]}")  # Limit log size
            # Parse the JSON response

    # Extract only the logEvents list
            log_events = data.get("logEvents", [])
            token = {'token': data.get("nextToken")}
            with open(file_path, 'w') as f:
                json.dump(token, f, indent=2)
            helper.log_info(f"Retrieved {len(log_events)} log events")
    
    
            events = data if isinstance(data, list) else [data]
    
            for item in log_events:
                event = helper.new_event(
                    data=json.dumps(item),
                    source=final_url,
                    sourcetype=helper.get_sourcetype(),
                    index=helper.get_output_index()
                )
                ew.write_event(event)
    
            helper.log_info(f"Successfully wrote {len(events)} events to Splunk.")
    
        except Exception as e:
            helper.log_error(f"Error fetching Cirrus logs: {str(e)}")
    else:
        creds = helper.get_arg('global_account')
        username = creds.get('username')
        password = creds.get('password')
        auth_str = f"{username}:{password}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {b64_auth}"
        }
        org_url = helper.get_arg('domain')  # Example: https://ww.institution.edu/

        # Construct final URL with raw orgUrl (not URL-encoded)
        final_url = f"{base_url}?orgUrl={org_url}"

        # Get user-provided domain (used as orgUrl query param)
   
  
        if not username or not password:
            helper.log_error("Credentials are missing username or password fields")
            return

        try:
            helper.log_info(f"Requesting Cirrus logs from: {final_url}")

            response = helper.send_http_request(
                final_url,
                method="GET",
                headers=headers,
                timeout=30,
                use_proxy=True
            )

            response.raise_for_status()
    
            # Parse the response
            data = response.json()
            helper.log_info(f"Response JSON: {json.dumps(data)[:500]}")  # Limit log size
            # Parse the JSON response

    # Extract only the logEvents list
            log_events = data.get("logEvents", [])
            token = {'token': data.get("nextToken")}
            with open(file_path, 'w') as f:
                json.dump(token, f, indent=2)
            helper.log_info(f"Retrieved {len(log_events)} log events")
    
    
            events = data if isinstance(data, list) else [data]
    
            for item in log_events:
                event = helper.new_event(
                    data=json.dumps(item),
                    source=final_url,
                    sourcetype=helper.get_sourcetype(),
                    index=helper.get_output_index()
                )
                ew.write_event(event)
    
            helper.log_info(f"Successfully wrote {len(events)} events to Splunk.")
    
        except Exception as e:
            helper.log_error(f"Error fetching Cirrus logs: {str(e)}")
        
