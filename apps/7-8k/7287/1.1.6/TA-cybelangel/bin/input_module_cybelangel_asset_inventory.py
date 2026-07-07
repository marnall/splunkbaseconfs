

import os
import sys
import time
import datetime
import json

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''








def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # cybelangel_reports = definition.parameters.get('cybelangel_reports', None)
    pass


def send_request_with_retries(helper, url, method, headers, parameters=None, max_retries=5, backoff_factor=2):
    for attempt in range(max_retries):
        try:
            response = helper.send_http_request(
                url, method, parameters=parameters, payload=None, headers=headers,
                cookies=None, verify=True, cert=None, timeout=30, use_proxy=False
            ).json()
            return response
        except requests.exceptions.ReadTimeout:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                helper.log_warning(f"Timeout occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                helper.log_error("Max retries reached. Unable to fetch data.")
                raise
        except Exception as e:
            helper.log_error(f"Error during request: {e}")
            raise

def collect_events(helper, ew):
    # Authentication
    helper.log_info("Authenticating to CybelAngel")
    auth_url = 'https://auth.cybelangel.com/oauth/token'
    auth_params = {'content-type': 'application/json'}
    auth_payload = {
        'client_id': helper.get_global_setting("cybelangel_client_id"),
        'client_secret': helper.get_global_setting("cybelangel_client_secret"),
        'audience': "https://platform.cybelangel.com/",
        'grant_type': "client_credentials"
    }

    try:
        auth_response = helper.send_http_request(
            auth_url, 'POST', parameters=auth_params, payload=auth_payload, headers=None,
            cookies=None, verify=True, cert=None, timeout=30, use_proxy=False
        ).json()
        token = 'Bearer ' + auth_response.get('access_token')
    except Exception as e:
        helper.log_critical(f"Error fetching token: {e}")
        raise

    # Fetch Asset Inventory
    helper.log_info("Requesting Asset Inventory from CybelAngel")
    platform_url = "https://platform.cybelangel.com/api/v1/inventory/assets"
    headers = {'Content-Type': "application/json", 'Authorization': token}
    assets = []
    parameters = {}

    try:
        while True:
            response = send_request_with_retries(
                helper, platform_url, 'GET', headers, parameters=parameters
            )
            for item in response.get('items'):
                assets.append(item)

            if response.get('next_cursor') is not None:
                parameters['cursor'] = response.get('next_cursor')
            else:
                break
    except Exception as e:
        helper.log_critical(f"Failed to fetch assets: {e}")
        raise

    # Process and Write Events
    max_event_size = 1048576  # 1MB
    for asset in assets:
        if 'data' in asset:
            data_size = len(json.dumps(asset['data']).encode('utf-8'))
            if data_size > max_event_size:
                helper.log_warning(f"Data size exceeds {max_event_size} bytes. Stripping data field.")
                asset['data'] = "Field stripped due to size limits."

        try:
            event = helper.new_event(
                json.dumps(asset), time=asset.get('last_seen_at'),
                host=None, index=None, source=None, sourcetype='cybelangelassets',
                done=True, unbroken=True
            )
            ew.write_event(event)
        except Exception as e:
            helper.log_error(f"Error writing event: {e}")
            raise                               
                                        
                                        
    

