# encoding = utf-8

import os
import sys
import time
from datetime import datetime, timedelta
import json
import httplib2
from urllib.parse import urlencode, quote

def validate_input(helper, definition):
    """Validate input configurations"""
    # Check API credentials
    api_credentials = definition.parameters.get('auguria_skl_api_credentials', None)
    if not api_credentials:
        raise ValueError("API credentials must be provided")
    
    # Check API base URL
    api_url = definition.parameters.get('auguria_skl_api_base_url', None)
    if not api_url:
        raise ValueError("API base URL must be provided")
    if not api_url.startswith("https://"):
        raise ValueError("API base URL must start with https:// for secure communication")
    
    # Check token refresh URL
    token_refresh_url = definition.parameters.get('token_refresh_url', None)
    if not token_refresh_url:
        raise ValueError("Token refresh URL must be provided")
    if not token_refresh_url.startswith("https://"):
        raise ValueError("Token refresh URL must start with https:// for secure communication")

def format_ontology_response(ontology_data):
    """Format ontology data into an array of paths"""
    paths = set()  # Using set to avoid duplicates
    
    # Add empty and partial paths
    paths.add("")
    paths.add("::")
    paths.add("::::")
    
    for item in ontology_data:
        ont1 = item.get('ontology1', '')
        ont2 = item.get('ontology2', '')
        ont3 = item.get('ontology3', '')
        
        # Add individual levels
        if ont1:
            paths.add(ont1)
        
        # Add combined paths
        if ont1 and ont2:
            paths.add(f"{ont1}::{ont2}")
        
        if ont1 and ont2 and ont3:
            paths.add(f"{ont1}::{ont2}::{ont3}")
    
    # Convert set to sorted list
    return sorted(list(paths))

def format_product_eventtype(product_data):
    """Format product eventtype data into an array of paths"""
    paths = set()  # Using set to avoid duplicates
    
    for item in product_data:
        product = item.get('product', '').lower().replace('_', '-')
        eventtype = item.get('event_type', '').lower()
        
        # Add individual product
        if product:
            paths.add(product)
        
        # Add combined path if both product and eventtype exist
        if product and eventtype:
            paths.add(f"{product}::{eventtype}")
    
    # Convert set to sorted list
    return sorted(list(paths))

def get_http_client(helper):
    """Configure and return HTTP client"""
    try:
        helper.log_debug("Initializing HTTP client with system CA certificates")
        return httplib2.Http()
    except Exception as e:
        helper.log_error(f"Error configuring HTTP client: {str(e)}")
        return httplib2.Http()

def collect_events(helper, ew):
    """Collect data from Auguria API and write to Splunk"""
    # Get configuration parameters
    opt_api_credentials = helper.get_arg('auguria_skl_api_credentials')
    
    # Get API URLs
    API_BASE_URL = helper.get_arg('auguria_skl_api_base_url')
    TOKEN_REFRESH_URL = helper.get_arg('token_refresh_url')
    
    # Security check: Ensure URLs use HTTPS protocol
    if not API_BASE_URL.startswith("https://"):
        helper.log_error("API base URL must use HTTPS protocol for security. Aborting data collection.")
        return
        
    if not TOKEN_REFRESH_URL.startswith("https://"):
        helper.log_error("Token refresh URL must use HTTPS protocol for security. Aborting data collection.")
        return
    
    # Continue with existing function after security checks pass
    api_client_id = opt_api_credentials['username']
    api_client_secret = opt_api_credentials['password']
    
    # Get the interval from input configuration
    interval = int(helper.get_arg('interval'))  # Interval in seconds
    
    # Get the last checkpoint time or set to 30 days ago if none exists
    checkpoint_key = "auguria_skl_analysis"
    last_run_time = helper.get_check_point(checkpoint_key)
    
    now = datetime.utcnow()
    date_to = now.strftime("%Y-%m-%dT%H:%M:%S")
    
    if last_run_time:
        # If checkpoint exists, use it as the start time
        date_from = datetime.fromtimestamp(float(last_run_time)).strftime("%Y-%m-%dT%H:%M:%S")
        helper.log_debug(f"Using checkpoint time: {date_from}")
    else:
        # If no checkpoint, get last 30 days of data
        date_from = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        helper.log_debug("No checkpoint found, collecting last 30 days of data")
    
    # API Constants
    AUTH0_API_AUDIENCE = API_BASE_URL + "/"
    AUTH0_API_GRANT_TYPE = "client_credentials"
    
    try:
        # Initialize HTTP client
        h = get_http_client(helper)
        
        # Get authentication token
        helper.log_debug("Requesting authentication token")
        (resp, auth_content) = h.request(
            TOKEN_REFRESH_URL,
            "POST",
            body=urlencode({
                "grant_type": AUTH0_API_GRANT_TYPE,
                "client_id": api_client_id,
                "client_secret": api_client_secret,
                "audience": AUTH0_API_AUDIENCE
            }),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if resp.status != 200:
            helper.log_error(f"Failed to get auth token. Status: {resp.status}")
            helper.log_error(f"Response content: {auth_content}")
            return
            
        auth_data = json.loads(auth_content)
        access_token = auth_data["access_token"]
        helper.log_info("Successfully obtained access token")

        # Get ontology data
        helper.log_debug("Retrieving ontology data")
        (resp, ontology_content) = h.request(
            f"{API_BASE_URL}/v1/api/analysis/filter/ontology",
            "GET",
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if resp.status != 200:
            helper.log_error(f"Failed to get ontology data. Status: {resp.status}")
            return
            
        ontology_data = json.loads(ontology_content)
        formatted_ontology = format_ontology_response(ontology_data)
        
        # Get product eventtype data
        helper.log_debug("Retrieving product eventtype data")
        (resp, product_content) = h.request(
            f"{API_BASE_URL}/v1/api/analysis/filter/producteventtype",
            "GET",
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if resp.status != 200:
            helper.log_error(f"Failed to get product eventtype data. Status: {resp.status}")
            return
            
        product_data = json.loads(product_content)
        formatted_product = format_product_eventtype(product_data)
        
        # Construct payload for metaclusters
        payload = {
            "data": {
                "page": 1,
                "size": 50,
                "filters": {
                    "ontology": {
                        "values": formatted_ontology,
                        "filterType": "set"
                    },
                    "producteventtype": {
                        "values": formatted_product,
                        "filterType": "set"
                    },
                    "score": {
                        "filter": [0, 100],
                        "filterType": "number",
                        "type": "greaterThanOrEqual"
                    },
                    "lastSeen": {
                        "dateFrom": date_from,
                        "dateTo": date_to,
                        "filterType": "date",
                        "type": "inRange"
                    }
                },
                "sort": []
            }
        }
        
        # Get metaclusters data
        helper.log_debug("Retrieving metaclusters data")
        (resp, metaclusters_content) = h.request(
            f"{API_BASE_URL}/v1/api/metaclusters",
            "POST",
            body=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if resp.status != 200:
            helper.log_error(f"Failed to get metaclusters data. Status: {resp.status}")
            return
            
        metaclusters_data = json.loads(metaclusters_content)
        
        # Extract and write individual message events to Splunk
        messages = metaclusters_data.get('message', [])
        helper.log_debug(f"Processing {len(messages)} individual messages")
        
        for message in messages:
            # Parse the last_seen_timestamp for the event time
            event_time = None
            try:
                last_seen = message.get('last_seen_timestamp')
                if last_seen:
                    # Convert ISO timestamp to epoch time
                    event_time = datetime.strptime(last_seen, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
            except Exception as e:
                helper.log_warning(f"Error parsing timestamp: {str(e)}")
            
            # Create individual event for each message
            event = helper.new_event(
                data=json.dumps(message),
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                time=event_time
            )
            ew.write_event(event)
        
        helper.log_info(f"Successfully processed {len(messages)} individual message events")
        
        # Save the current time as a checkpoint for the next run
        helper.save_check_point(checkpoint_key, now.timestamp())
        helper.log_debug(f"Saved checkpoint time: {now.timestamp()}")
        
    except Exception as e:
        helper.log_error(f"Error collecting events: {str(e)}")
        raise