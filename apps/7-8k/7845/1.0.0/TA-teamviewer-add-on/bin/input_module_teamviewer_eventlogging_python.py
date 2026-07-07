# encoding = utf-8

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta

def validate_input(helper, definition):
    """
    Validate user input when setting up the modular input.
    This function is required by Splunk's Add-on Builder.
    """
    helper.log_info("Validating input settings...")
    pass
    
def collect_events(helper, ew):
    # Get token securely from Splunk add-on settings
    access_token = helper.get_global_setting("access_token")
    if not access_token:
        helper.log_error("Missing access token for TeamViewer API")
        return

    # Generate StartDate & EndDate dynamically (last 2 minutes)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(seconds=120)
    
    start_date = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Define API URL
    api_url = "https://webapi.teamviewer.com/api/v1/EventLogging"

    # Set headers (Authorization + Content-Type)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Set body (StartDate & EndDate)
    payload = {
        "StartDate": start_date,
        "EndDate": end_date
    }

    helper.log_info(f"Sending request to {api_url} with payload: {json.dumps(payload)}")
    helper.log_info(f"Request URL: {api_url}")
    helper.log_info(f"Request Headers: {json.dumps(headers)}")
    helper.log_info(f"Request Payload: {json.dumps(payload)}")
    # Make API request
    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        helper.log_info(f"API Response: {json.dumps(data)}")

        # Process each event
        audit_events = data.get("AuditEvents", [])
        if not audit_events:
            helper.log_warning("No audit events found in API response.")
        else :
            for event in audit_events:
                event_data = json.dumps(event)
                event_obj = helper.new_event(data=event_data, index="teamviewer")
                ew.write_event(event_obj)
                helper.log_info(f"Event Data: {event_data}")
        helper.log_info(f"Successfully ingested {len(data.get('AuditEvents', []))} events")

    else:
        helper.log_error(f"Failed API Call: {response.status_code} - {response.text}")