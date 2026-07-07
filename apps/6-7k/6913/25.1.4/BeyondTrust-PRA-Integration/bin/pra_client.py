# Functions specific to PRA REST API operations

from datetime import datetime
import time
import traceback
import os
import common_utils as utils

########## Retrieves an authentication token from the PRA REST API to be used for subsequent calls
def get_auth_token(helper, hostname: str, client_id: str, client_secret: str):
    auth_token = None
    auth_url = f'https://{hostname}/oauth2/token'
    auth_headers = {
                'Accept': '*/*',
                'Authorization': 'Basic ' + utils.base64_encode(f'{client_id}:{client_secret}'),
                'Content-Type': 'application/x-www-form-urlencoded'
            }
    auth_body = 'grant_type=client_credentials'

    try:
        helper.log_debug(f'Preparing to attempt authentication call to {hostname}')
        
        response = helper.send_http_request(auth_url, 'POST', parameters=None, payload=auth_body,
                                        headers=auth_headers, cookies=None, verify=True, cert=None,
                                        timeout=None)
        # Check the response status, if the status is not successful, raise requests.HTTPError
        if response.status_code == 200:
            helper.log_debug('Successfully authenticated')
        else:
            helper.log_debug(f'Error response: {str(response.status_code)} -- {response.text}')
            response.raise_for_status()

        data = response.json()
        auth_token = data['access_token']
    except Exception as e:
        helper.log_error(f'Authentication attempt failed: {str(e)}')
        traceback.print_exc()

    return auth_token
########## -----------------------------------------------

########## Retrieves a batch of events from the PRA REST API beginning with events ingested at the specified start date
def get_session_report(helper, auth_token: str, hostname: str, end_date: int, connection_timeout:float, read_timeout:float):
    events_url = f'https://{hostname}/api/reporting'
    events_headers = {
                'Authorization': f'Bearer {auth_token}'
            }
    events_params = {
                'end_time': end_date,
                'duration': 0,
                'generate_report': 'AccessSession'
            }
    
    try:
        helper.log_debug(f'Preparing to attempt event ingestion from {hostname} starting at {end_date} using connection timeout {connection_timeout} and read timeout {read_timeout}')

        response = helper.send_http_request(events_url, 'GET', parameters=events_params, payload=None,
                                        headers=events_headers, cookies=None, verify=True, cert=None,
                                        timeout=(connection_timeout,read_timeout))
        # check the response status, if the status is not successful, raise requests.HTTPError
        if response.status_code == 200:
            data = response.content
            helper.log_debug(f'Successfully retrieved data for events in this batch')
        else:
            helper.log_debug(f'Error response: {str(response.status_code)} -- {response.text}')
            response.raise_for_status()

        return data
    except Exception as e:
        helper.log_error(f'Event ingestion failed: {str(e)}')
        traceback.print_exc()

    return None
########## -----------------------------------------------