# encoding = utf-8

import os
import sys
import time
from datetime import datetime, timedelta
import json
import httplib2
from urllib.parse import urlencode
from urllib.parse import quote

def validate_input(helper, definition):
    """Validate input configurations"""
    # Check if API credentials are provided
    api_credentials = definition.parameters.get('auguria_skl_api_credentials', None)
    if not api_credentials:
        raise ValueError("API credentials must be provided")
    
    # Check if API base URL starts with https://
    api_base_url = definition.parameters.get('auguria_skl_api_base_url', None)
    if not api_base_url:
        raise ValueError("API base URL must be provided")
    if not api_base_url.startswith("https://"):
        raise ValueError("API base URL must start with https:// for secure communication")
    
    # Check if token refresh URL starts with https://
    token_refresh_url = definition.parameters.get('token_refresh_url', None)
    if not token_refresh_url:
        raise ValueError("Token refresh URL must be provided")
    if not token_refresh_url.startswith("https://"):
        raise ValueError("Token refresh URL must start with https:// for secure communication")
        
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
    opt_auguria_skl_api_credentials = helper.get_arg('auguria_skl_api_credentials')
    API_BASE_URL = helper.get_arg('auguria_skl_api_base_url')
    TOKEN_REFRESH_URL = helper.get_arg('token_refresh_url')
    
    # Ensure URLs use HTTPS protocol before proceeding
    if not API_BASE_URL.startswith("https://"):
        helper.log_error("API base URL must use HTTPS protocol for security. Aborting data collection.")
        return
        
    if not TOKEN_REFRESH_URL.startswith("https://"):
        helper.log_error("Token refresh URL must use HTTPS protocol for security. Aborting data collection.")
        return
    
    # Continue with existing code
    api_client_id = opt_auguria_skl_api_credentials['username']
    api_client_secret = opt_auguria_skl_api_credentials['password']
    
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
        
        # Check API health
        helper.log_debug("Checking API health")
        (resp, health_check_content) = h.request(
            f"{API_BASE_URL}/v1/api/health-check",
            "GET",
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if resp.status != 200:
            helper.log_error(f"Health check failed. Status: {resp.status}")
            helper.log_error(f"Health check response: {health_check_content}")
            return
        
        helper.log_debug("API health check successful")
        
        # Get checkpoint and current time
        checkpoint_key = "auguria_skl_eventdashboard"
        check_point = helper.get_check_point(checkpoint_key)
        current_time = datetime.now()
        
        # Initialize events list to store all collected data
        all_events = []
        
        if check_point:
            # Get interval from configuration
            interval = int(helper.get_arg('interval'))  # Interval in seconds
            helper.log_debug(f"Using configured interval of {interval} seconds")
            
            # Convert checkpoint to datetime
            check_point_time = datetime.fromisoformat(check_point)
            
            # Calculate number of intervals to process
            time_diff = current_time - check_point_time
            total_intervals = int(time_diff.total_seconds() / interval)
            
            helper.log_debug(f"Processing {total_intervals} intervals from checkpoint")
            
            # Iterate through intervals from checkpoint to current time
            for i in range(total_intervals + 1):
                query_time = check_point_time + timedelta(seconds=i * interval)
                if query_time <= current_time:  # Prevent future data queries
                    end_time = min(query_time + timedelta(seconds=interval), current_time)
                    
                    # Format times for API request in ISO format
                    from_time = query_time.isoformat()
                    to_time = end_time.isoformat()
                    
                    helper.log_debug(f"Fetching data from {from_time} to {to_time}")
                    
                    signals_url = f"{API_BASE_URL}/v1/api/dashboard/signals?from={quote(from_time)}&to={quote(to_time)}"
                    (resp, signals_content) = h.request(
                        signals_url,
                        "GET",
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Authorization': f'Bearer {access_token}'
                        }
                    )
                    
                    if resp.status == 200:
                        if isinstance(signals_content, bytes):
                            signals_content = signals_content.decode('utf-8')
                        
                        signals_data = json.loads(signals_content)
                        
                        if isinstance(signals_data, dict):
                            signals_data = [signals_data]
                        
                        timestamped_signals = []
                        for signal in signals_data:
                            event_data = dict(signal)
                            event_data['timestamp'] = from_time
                            timestamped_signals.append(event_data)
                            
                        all_events.extend(timestamped_signals)
                    else:
                        helper.log_error(f"Failed to get signals for period {from_time} to {to_time}. Status: {resp.status}")
        else:
            # No checkpoint - get last 30 days of data
            helper.log_debug("No checkpoint found. Collecting last 30 days of data")
            
            current_midnight = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            
            for day in range(30):
                end_time = current_midnight - timedelta(days=day)
                start_time = end_time - timedelta(days=1)
                
                from_time = start_time.isoformat()
                to_time = end_time.isoformat()
                
                helper.log_debug(f"Fetching data for day {30-day}: {from_time} to {to_time}")
                
                signals_url = f"{API_BASE_URL}/v1/api/dashboard/signals?from={quote(from_time)}&to={quote(to_time)}"
                (resp, signals_content) = h.request(
                    signals_url,
                    "GET",
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': f'Bearer {access_token}'
                    }
                )
                
                if resp.status == 200:
                    if isinstance(signals_content, bytes):
                        signals_content = signals_content.decode('utf-8')
                    
                    signals_data = json.loads(signals_content)
                    
                    if isinstance(signals_data, dict):
                        signals_data = [signals_data]
                    
                    timestamped_signals = []
                    for signal in signals_data:
                        event_data = dict(signal)
                        event_data['timestamp'] = from_time
                        timestamped_signals.append(event_data)
                        
                    all_events.extend(timestamped_signals)
                else:
                    helper.log_error(f"Failed to get signals for day {from_time}. Status: {resp.status}")
        
        # Write all collected events to Splunk
        if all_events:
            helper.log_debug(f"Writing {len(all_events)} events to Splunk")
            for event_data in all_events:
                if isinstance(event_data, str):
                    event_data = json.loads(event_data)
                
                transformed_data = {"timestamp": event_data.get("timestamp")}
                
                for key, value in event_data.items():
                    if key in ['metadata', 'timestamp']:
                        continue
                    elif key == 'high_pirority':
                        transformed_data['high_priority'] = value
                    elif key == 'low_pirority':
                        transformed_data['low_priority'] = value
                    else:
                        transformed_data[key] = value
                
                helper.log_debug("Original event data: " + json.dumps(event_data))
                helper.log_debug("Transformed event data: " + json.dumps(transformed_data))
                
                event = helper.new_event(
                    data=json.dumps(transformed_data),
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype(),
                    time=transformed_data['timestamp']
                )
                ew.write_event(event)
            
            helper.log_info(f"Successfully processed {len(all_events)} events")
            
            helper.save_check_point("lastRunTime", current_time.isoformat())
        else:
            helper.log_info("No new events found to process")
        
    except Exception as e:
        helper.log_error(f"Error collecting events: {str(e)}")
        raise