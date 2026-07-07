# Functions specific to PM Cloud REST API operations

from datetime import datetime, timedelta
import traceback
import common_utils as utils

API_RATE_LIMIT_WINDOW = 100

########## Retrieves an authentication token from the PMC REST API to be used for subsequent calls
def get_auth_token(helper, hostname: str, client_id: str, client_secret: str):
    auth_token = None
    auth_url = f'https://{hostname}/oauth/connect/token'
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
        elif response.status_code == 429:
            helper.log_warning('Encountered HTTP 429 indicating too many requests within the specified window. The polling process for this interval ' \
                f'will exit and the add-on will attempt to pull data again on the next interval run that is at least {API_RATE_LIMIT_WINDOW} seconds from now')
            # populate the sleep-until 
            trigger_rate_limit_sleep(helper)
            raise Exception(f'API limit hit; no further attempts will be made for at least {API_RATE_LIMIT_WINDOW} seconds from now')
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


########## Retrieves a batch of client events from the PMC REST API beginning with events ingested at the specified start date
def get_client_events_batch(helper, auth_token: str, hostname: str, start_date: datetime, batch_size: int, connection_timeout: float, read_timeout: float):
    events_url = f'https://{hostname}/management-api/v1/Events/FromStartDate'
    events_headers = {
                # 'Accept': 'application/json',
                'Authorization': f'Bearer {auth_token}'
            }
    events_params = {
                'StartDate': start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'RecordSize': batch_size
            }
    try:
        helper.log_debug(f'Preparing to attempt client event ingestion from {hostname} starting at {start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")} using connection timeout {connection_timeout} and read timeout {read_timeout}')
        response = helper.send_http_request(events_url, 'GET', parameters=events_params, payload=None,
                                        headers=events_headers, cookies=None, verify=True, cert=None,
                                        timeout=(connection_timeout, read_timeout))
        # check the response status, if the status is not successful, raise requests.HTTPError
        if response.status_code == 200:
            data = response.json()
            helper.log_debug(f'Successfully retrieved data for {str(data["totalRecordsReturned"])} client events in this batch')
        elif response.status_code == 429:
            helper.log_warning('Encountered HTTP 429 indicating too many requests within the specified window. The polling process for this interval ' \
                f'will exit and the add-on will attempt to pull data again on the next interval run that is at least {API_RATE_LIMIT_WINDOW} seconds from now')
            # populate the sleep-until 
            trigger_rate_limit_sleep(helper)
            raise Exception(f'API limit hit; no further attempts will be made for at least {API_RATE_LIMIT_WINDOW} seconds from now')
        else:
            helper.log_debug(f'Error response: {str(response.status_code)} -- {response.text}')
            response.raise_for_status()

        return data
    except Exception as e:
        helper.log_error(f'Client event ingestion failed: {str(e)}')
        traceback.print_exc()

    return None
########## -----------------------------------------------


########## Retrieves a page of activity audits from the PMC REST API beginning with activity that occurred at the specified start date
def get_activity_audits_batch(helper, auth_token: str, hostname: str, start_date: datetime, end_date: datetime, page_size: int, page_number: int, connection_timeout: float, read_timeout: float):
    audits_url = f'https://{hostname}/management-api/v1/ActivityAudits/Details'
    audits_headers = {
                # 'Accept': 'application/json',
                'Authorization': f'Bearer {auth_token}'
            }
    audits_params = {
                'Filter.Created.Dates': [ start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'), end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ') ],
                'Filter.Created.SelectionMode': 'Range',
                'Pagination.PageSize': page_size,
                'Pagination.PageNumber': page_number
            }
    try:
        helper.log_debug(f'Preparing to attempt activity audit ingestion from {hostname} starting at {start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")} through {end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")} (Page: {page_number} - Page Size: {page_size}) using connection timeout {connection_timeout} and read timeout {read_timeout}')
        response = helper.send_http_request(audits_url, 'GET', parameters=audits_params, payload=None,
                                        headers=audits_headers, cookies=None, verify=True, cert=None,
                                        timeout=(connection_timeout, read_timeout))
        # check the response status, if the status is not successful, raise requests.HTTPError
        if response.status_code == 200:
            data = response.json()
            helper.log_debug(f'Successfully retrieved data for {len(data["data"])} (out of {str(data["totalRecordCount"])} total) activity audits in this API call')
        elif response.status_code == 429:
            helper.log_warning('Encountered HTTP 429 indicating too many requests within the specified window. The polling process for this interval ' \
                f'will exit and the add-on will attempt to pull data again on the next interval run that is at least {API_RATE_LIMIT_WINDOW} seconds from now')
            # populate the sleep-until 
            trigger_rate_limit_sleep(helper)
            raise Exception(f'API limit hit; no further attempts will be made for at least {API_RATE_LIMIT_WINDOW} seconds from now')
        else:
            helper.log_debug(f'Error response: {str(response.status_code)} -- {response.text}')
            response.raise_for_status()

        return data
    except Exception as e:
        helper.log_error(f'Activity audits ingestion failed: {str(e)}')
        traceback.print_exc()

    return None
########## -----------------------------------------------


########## Sets a timestamp to tell calling code when it is safe to start attempting API calls again after hitting a rate limit error
def trigger_rate_limit_sleep(helper):
    sleep_until_date = datetime.now() + timedelta(seconds=API_RATE_LIMIT_WINDOW)
    utils.save_sleep_until(helper, sleep_until_date)
########## -----------------------------------------------