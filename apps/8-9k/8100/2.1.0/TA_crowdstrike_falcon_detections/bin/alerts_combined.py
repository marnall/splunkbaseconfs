import time
import random

#local imports
import Send_to_Splunk
from Status_Code_Errors_Splunk import status_code_errors

RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF = 5

def _command_with_retry(falcon, command, log_label, helper, **kwargs):
    """Execute a FalconPy command with rate-limit retry and token expiry handling."""
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        response = falcon.command(command, **kwargs)
        status_code = response.get('status_code', 0) if isinstance(response, dict) else 0

        if status_code == 401 and attempt == 0:
            helper.log_warning(f'{log_label} Token expired (401) on {command}, attempting re-authentication')
            try:
                falcon.authenticate()
                if falcon.authenticated():
                    helper.log_info(f'{log_label} Re-authentication successful, retrying {command}')
                    continue
                else:
                    helper.log_error(f'{log_label} Re-authentication failed for {command}')
            except Exception as e:
                helper.log_error(f'{log_label} Re-authentication exception during {command}: {type(e).__name__}: {e}')
            return response

        if status_code == 429 or status_code >= 500:
            if attempt < RATE_LIMIT_RETRIES:
                wait = RATE_LIMIT_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                helper.log_warning(f'{log_label} Retryable error ({status_code}) on {command}, retrying in {wait:.1f}s (attempt {attempt + 1}/{RATE_LIMIT_RETRIES})')
                time.sleep(wait)
                continue
            else:
                helper.log_error(f'{log_label} {command} failed with {status_code} after {RATE_LIMIT_RETRIES} retries')
                return response

        if attempt > 0:
            helper.log_info(f'{log_label} {command} succeeded after {attempt} retries')

        return response

def collect_alert_data(falcon, body_payload, api_endpoint, log_label, helper):
    #makes API calls to the combined alerts API endpoint using the FalconPy SDK
    try:
        helper.log_info(f"{log_label} Querying the combined alerts API for matching event data")
        helper.log_debug(f"{log_label} Body payload values {body_payload}")
        alert_response = _command_with_retry(falcon, "PostCombinedAlertsV1", log_label, helper, body=body_payload)
        status_code = str(alert_response['status_code'])

    except Exception as api_err:
        helper.log_error(f"{log_label} Unable to make contact with the CrowdStrike API endpoint - {api_endpoint}. Exception: {api_err}")
        raise RuntimeError(f"Unable to contact CrowdStrike API endpoint {api_endpoint}: {api_err}")

    return alert_response, status_code

def get_alerts(updated_timestamp, stanza_checkpoint, chkpt_value, log_label, falcon, ta_data, helper, ew):

    limit = 1000
    sort = "updated_timestamp.asc"

    #if this is not the initial run then the updated_timestamp filter is set to greater than vs greater than or equal to
    if chkpt_value:
        time_filter = f"updated_timestamp:>'{updated_timestamp}'"
    else:
        time_filter = f"updated_timestamp:>='{updated_timestamp}'"

    #if specific product types have been selected then create the filter for that, let blank for all
    if 'all' not in ta_data['Products']:
        alert_filter = f"({time_filter})+(product:{ta_data['Products']})"
    else:
        alert_filter = f"{time_filter}"

    helper.log_debug(f"{log_label} Filter for API details call is {alert_filter}")
    helper.log_info(f"{log_label} Calling API for alert details")

    #FalconPy API config for the query to the combined endpoint
    api_endpoint = 'PostCombinedAlertsV1'
    body_payload = {"after": "", "filter": alert_filter, "limit": limit, "sort": sort}

    #call file to make the API query
    alert_response, status_code = collect_alert_data(falcon, body_payload, api_endpoint, log_label, helper)
    alert_data = []

    #determine if the call was successful, if there were events matching the criteria
    if status_code.startswith('2'):
        helper.log_info(f"{log_label} API call successful")
        meta_data = alert_response['body']['meta']
        alert_resources = alert_response['body']['resources']

        helper.log_debug(f"{log_label} API call details: {meta_data}")
        alert_count = len(alert_resources)

        if alert_count > 0:
            helper.log_info(f"{log_label} There are detections to process")
            alert_data.extend(alert_resources)

            if 'after' not in meta_data['pagination']:
                helper.log_info(f"{log_label} Pagination is not required for this collection")
                pagination = False
                helper.log_info(f"{log_label} Preparing to send initial data to Splunk indexer")
                Send_to_Splunk.send_to_splunk(alert_data, updated_timestamp, stanza_checkpoint, log_label, ta_data, pagination, alert_count, helper, ew)

            else:
                #send the first page before paginating
                helper.log_info(f"{log_label} Pagination is required to collect all the identified data")
                helper.log_info(f"{log_label} Preparing to send initial page to Splunk indexer")
                Send_to_Splunk.send_to_splunk(alert_data, updated_timestamp, stanza_checkpoint, log_label, ta_data, True, alert_count, helper, ew)

                #process remaining pages
                while True:
                    body_payload['after'] = meta_data['pagination']['after']
                    alert_response, status_code = collect_alert_data(falcon, body_payload, api_endpoint, log_label, helper)

                    if status_code.startswith('2'):
                        meta_data = alert_response['body']['meta']
                        alert_data = alert_response['body']['resources']
                        if 'after' not in meta_data['pagination']:
                            helper.log_info(f"{log_label} Pagination has completed for all the identified data")
                            pagination = False
                        else:
                            pagination = True
                        alert_count = alert_count + len(alert_data)
                        helper.log_info(f"{log_label} Preparing to send data to Splunk indexer")
                        Send_to_Splunk.send_to_splunk(alert_data, updated_timestamp, stanza_checkpoint, log_label, ta_data, pagination, alert_count, helper, ew)

                        if not pagination:
                            break
                    else:
                        status_code_errors(alert_response, api_endpoint, log_label, helper)
                        break

        else:
            helper.log_info(f"{log_label} There are no detections that currently meet the requirements, nothing to process")
            helper.log_info(f"{log_label} Collection complete, no detections to process")
            return
    else:
        status_code_errors(alert_response, api_endpoint, log_label, helper)
