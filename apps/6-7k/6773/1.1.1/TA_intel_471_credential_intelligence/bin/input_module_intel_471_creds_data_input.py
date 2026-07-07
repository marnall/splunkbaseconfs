import json
import re
import traceback
from urllib.parse import urlencode
import requests
from datetime import datetime, timezone
from utils import raise_web_message, get_proxy_kwargs, get_version, convert_ts, extract_path


def validate_input(helper, definition):
    '''Implement your own validation logic to validate the input stanza configurations'''
    pass

def adapt_credential(occurence):
    credential = extract_path(occurence, 'data.credential')
    uid = credential.pop('id')
    credential['uid'] = uid

    titan_credential_occurence = {
          "uid": extract_path(occurence, "id"),
          "data": {
            "file_path": extract_path(occurence, "data.file_path"),
            "accessed_url": extract_path(occurence, "data.accessed_url"),
            "credential": credential,
            "credential_set": {
              "uid": extract_path(occurence, "data.credential_set.id"),
              "name": extract_path(occurence, "data.credential_set.name"),
            },
            "detected_malware": {
              "family": extract_path(occurence, "data.info_stealer.malware_family", sentinel="Unidentified"),
            }
          },
          "classification": {
            "intel_requirements": [x.get("path") for x in extract_path(occurence, "classification.girs")]
          },
          "last_updated": convert_ts(extract_path(occurence, "last_updated_ts")),
          "activity": {
            "first": convert_ts(extract_path(occurence, "activity.first_seen_ts")),
            "last": convert_ts(extract_path(occurence, "activity.last_seen_ts")),
          }
        }


    return titan_credential_occurence


def get_api_config(api_name):
    headers = {'User-agent': f'Intel 471 - Credential Intelligence - Splunk App {get_version()}'}
    if api_name == "verity":
        base_url = "https://api.intel471.cloud/integrations/creds/v1/credentials/occurrences/stream"
    else:
        base_url = "https://api.intel471.com/v1/credentials/occurrences/stream"
    return base_url, headers


def make_api_request(session, api_url):
    """Make API request and return parsed response."""
    resp = session.get(api_url)
    resp.raise_for_status()
    return resp.json()

def process_credentials(credentials, helper, ew):
    """Process credentials and write events."""
    backend = helper.get_arg("backend")
    credential_count = 0
    for credential in credentials:
        credential = adapt_credential(credential) if backend == "verity" else credential
        credential_data = credential.get('data', {}).get('credential', {})
        if credential_data:
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype='intel471:credsdata:source',
                data=json.dumps(credential),
            )
            ew.write_event(event)
            credential_count += 1
    return credential_count


def handle_api_error(e, helper):
    helper.log_warning(f'API request exception: {str(e)}')
    msg = 'Intel 471 Credential Intelligence Add-on Data input failed to connect to the API. ' \
          'This could be either due to use of invalid credentials in Add-on Configuration ' \
          f'or connectivity issues. {str(e)}'
    raise_web_message(helper, msg)


def handle_general_error(e, helper):
    helper.log_error(f'Collecting events failed: {str(e)}')
    helper.log_error(traceback.format_exc())
    raise_web_message(helper, 'Intel 471 Credential Intelligence Add-on Data input failed. '
                              'Refer to the logs for more details')


def parse_created_after_date(helper, created_after_arg, checkpoint_key):
    """Parse and validate the created_after date parameter."""
    created_after = helper.get_check_point(checkpoint_key)
    if not created_after:
        created_after = (created_after_arg or "").strip()
        if re.match(r"^\d{13}$", created_after):
            created_after = int(created_after)
        else:
            created_after = int(datetime.now(timezone.utc).timestamp() * 1000)
        helper.save_check_point(checkpoint_key, created_after)

    helper.log_info("Collecting Credential Intelligence since "
                    f"{datetime.fromtimestamp(created_after / 1000).isoformat()} ({created_after}).")
    return created_after


def setup_session(global_account, proxy_settings):
    """Setup authenticated session with proxy configuration."""
    session = requests.Session()
    session.proxies.update(get_proxy_kwargs(proxy_settings))
    session.auth = (global_account["username"], global_account["password"])
    return session


def collect_events(helper, ew):
    helper.set_log_level(helper.get_log_level())
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    account_name = input_stanza[input_name]['global_account']['name']
    backend = helper.get_arg("backend")

    # Get checkpoint keys
    CHECKPOINT_CURSOR_KEY = f'i471_creds_cursor_{input_name}_{account_name}{backend if backend == "verity" else ""}'
    CHECKPOINT_INITIAL_DATE = f'i471_creds_initial_date_{input_name}_{account_name}{backend if backend == "verity" else ""}'

    created_after = parse_created_after_date(helper, helper.get_arg("created_after"), CHECKPOINT_INITIAL_DATE)

    # Get API configuration
    base_url, headers = get_api_config(backend)

    global_account = helper.get_arg('global_account')
    session = setup_session(global_account, helper.get_proxy())
    session.headers = headers

    credential_count = 0
    request_count = 0

    while True:
        try:
            stored_cursor = helper.get_check_point(CHECKPOINT_CURSOR_KEY)
            if backend == "verity":
                api_query = {'from': created_after, 'size': 1000}
                cursor_key = "cursor_next"
            else: # api_name == "titan"
                api_query = {'from': created_after, 'count': 100}
                cursor_key = "cursor_next"

            if stored_cursor:
                api_query['cursor'] = stored_cursor

            api_url = f"{base_url}?{urlencode(api_query)}"
            resp_parsed = make_api_request(session, api_url)
            request_count += 1

            cursor = resp_parsed.get(cursor_key)
            if cursor:
                helper.save_check_point(CHECKPOINT_CURSOR_KEY, cursor)

            credentials = resp_parsed.get('credential_occurrences', [])
            if len(credentials) == 0:
                helper.log_info('No credentials in this iteration.')
                break

            helper.log_info(f'Got {len(credentials)} credentials in this iteration.')

            processed_count = process_credentials(credentials, helper, ew)
            credential_count += processed_count


        except requests.RequestException as e:
            handle_api_error(e, helper)
            break
        except Exception as e:
            handle_general_error(e, helper)
            break

    helper.log_info(f'Collected {credential_count} credentials using {request_count} API calls.')

