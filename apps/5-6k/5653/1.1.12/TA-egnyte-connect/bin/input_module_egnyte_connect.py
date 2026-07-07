# encoding = utf-8
import datetime
import json
import os
import time
import uuid
from datetime import datetime, timedelta

import splunk.rest as rest

import ta_egnyte_connect_constants as tec
import splunk.rest as rest
import sentry_sdk

from ta_egnyte_connect_utility import *

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]

import splunklib.client as client

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

MAX_QUERYING_DURATION = 50


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # data_type = definition.parameters.get('data_type', None)
    # global_account = definition.parameters.get('global_account', None)
    pass


def get_checkpoint(helper, key, start_date=None):
    checkpoint = helper.get_check_point(key)
    if checkpoint is None:
        checkpoint = {}

    if start_date is None or start_date == "":
        # If start_date is not provided or is an empty string, set it to 1 day ago
        start_date = datetime.utcnow() - timedelta(days=1)
        start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        checkpoint['start_date'] = start_date
    else:
        # If start_date is provided (not None and not empty), update it in the checkpoint
        checkpoint['start_date'] = start_date

    # Convert the start_date from the checkpoint to a datetime object
    start_date_dt = datetime.strptime(checkpoint['start_date'], '%Y-%m-%dT%H:%M:%SZ')

    # Calculate the date 7 days ago from the current date
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    # If the start_date from the checkpoint is older than 7 days ago, update it to the current date
    if start_date_dt <= seven_days_ago:
        checkpoint['start_date'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    return checkpoint


def set_checkpoint(helper, key, checkpoint):
    return helper.save_check_point(key, checkpoint)


def collect_events(helper, ew):
    session_id = str(uuid.uuid4())

    sentry_sdk.init(dsn="https://c168c32ef5bf4d418f790ed2b0ef985d@sentry-prod.egnyte.com/9")

    start_time = time.time()

    # getting setup parameters
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    global_account = helper.get_arg('global_account')

    domain_name = global_account.get("egnyte_domain", "N/A")
    helper.log_info("Domain name: {}".format(domain_name))

    clientid = input_stanza[input_name]['global_account']['client_id']
    account_name = input_stanza[input_name]['global_account']['name']
    client_secret = input_stanza[input_name]['global_account']['client_secret']
    code = input_stanza[input_name]['global_account']['password']
    stanza_name = list(input_stanza.keys())[0]
    stanza = list(input_stanza.values())[0]
    session_key = helper.context_meta['session_key']
    egnyte_domain_url = helper.get_arg('egnyte_domain_url')
    egnyte_domain_url = "https://{}".format(egnyte_domain_url)
    start_date = helper.get_arg('start_date')
    data_type = helper.get_arg('data_type')
    number_of_events = 0
    REDIRECT_URI = tec.REDIRECT_URI
    auth_url = str(egnyte_domain_url) + "/puboauth/token"
    mapping_data_type = {"FILE_AUDIT": "file", "PERMISSION_AUDIT": "permission", "LOGIN_AUDIT": "login",
                         "USER_AUDIT": "user", "WG_SETTINGS_AUDIT": "wg_settings", "GROUP_AUDIT": "group",
                         "WORKFLOW_AUDIT": "workflow"}
    checkpoint = get_checkpoint(helper, key=account_name, start_date=start_date) or dict()

    service = client.connect(host='localhost', port=8089, token=session_key)

    # Going to take access/refresh token if it is not available in the checkpoint
    if not checkpoint or str(checkpoint.get("code")) != str(code):
        helper.log_info(
            "Checkpoint is not available or code changed from setup page. Hence requesting new access token. Session ID: {}".format(session_id))
        if is_debug_enabled(helper):
            helper.log_debug("Authentication details - Domain: {}, Auth URL: {}, Account: {}, Session ID: {}"
                             .format(domain_name, auth_url, account_name, session_id))
        try:
            # Use retry version to handle temporary Egnyte API failures
            # Raises TemporaryTokenError if retries exhausted on 5xx/429
            response = generate_or_refresh_token_with_retry(
                helper=helper,
                auth_url=auth_url,
                clientid=clientid,
                client_secret=client_secret,
                code=code,
                redirect_uri=REDIRECT_URI,
                session_id=session_id,
                scope=tec.SCOPE
            )

            # Handle permanent auth errors (400 = invalid grant/code)
            if response.status_code == 400:
                helper.log_error("Error while getting access/refresh token. Session ID: {}".format(session_id))
                helper.log_error("Please generate new code and update the input with new code.")
                if is_debug_enabled(helper):
                    helper.log_debug("Token generation failed with 400 - Response: {}".format(response.text[:500]))
                postargs = {
                    'severity': "error",
                    'name': APP_NAME,
                    'value': "Egnyte Collaborate Add-on: Please generate new code and update the input with new code."
                }
                rest.simpleRequest('/services/messages', session_key, postargs=postargs)
                return

            # Handle other non-200 responses (5xx/429 already handled via TemporaryTokenError)
            if response.status_code != 200:
                helper.log_error(
                    "Token generation failed with status {}. Response: {}. Session ID: {}".format(
                        response.status_code, response.text[:500], session_id
                    )
                )
                return

            # Parse and validate the token response
            try:
                response_json = response.json()
            except json.JSONDecodeError as e:
                helper.log_error("Token response is not valid JSON: {}. Session ID: {}".format(str(e), session_id))
                return

            # Validate token response contains access_token
            if not validate_token_response(response_json, helper, session_id):
                helper.log_error("Token response validation failed. Session ID: {}".format(session_id))
                return

            checkpoint["code"] = code
            set_checkpoint(helper, key=account_name, checkpoint=checkpoint)
            if is_debug_enabled(helper):
                helper.log_debug("Token generation successful - Token type: {}, Expires in: {} seconds"
                                 .format(response_json.get("token_type", "N/A"), response_json.get("expires_in", "N/A")))

            storage_passwords = service.storage_passwords
            access_token = response_json.get("access_token")
            try:
                # Try to retrieve existing password first. This handles the case where
                # the password was already created by a previous run. Updating the token
                # is not necessary as it is deterministic based on client_id, secret & domain.
                # Note: Single-threaded execution per input stanza is assumed.
                body = storage_passwords.get(account_name + "/" + code)["body"]
                if is_debug_enabled(helper):
                    helper.log_debug("Existing storage password found for account")
            except HTTPError:
                # Only create if we have a valid access_token
                if access_token:
                    storage_passwords.create(access_token, account_name + "/" + code)
                    if is_debug_enabled(helper):
                        helper.log_debug("New storage password entry created.")
                else:
                    helper.log_error("Cannot store empty access token. Session ID: {}".format(session_id))
                    return

        except TemporaryTokenError as e:
            # Egnyte token endpoint is temporarily unavailable (e.g., 5xx/429).
            # Skip this polling cycle without corrupting stored tokens.
            helper.log_warning(
                "Egnyte token endpoint temporarily unavailable (status {}). "
                "Skipping this polling cycle. Session ID: {}".format(e.status_code, session_id)
            )
            return
        except Exception as e:
            helper.log_error("Exception during token generation: {}. Session ID: {}".format(str(e), session_id))
            raise e

    checkpoint_for_input = get_checkpoint(helper, key=stanza_name, start_date=start_date)
    data_url = ""
    end_date = datetime.utcnow().isoformat() + "Z"
    data = {}

    start_date_done = True
    params = {}
    if checkpoint_for_input.get("nextCursor"):
        params['nextCursor'] = checkpoint_for_input.get("nextCursor")

    token = get_token_from_secure_password(account_name, code, service, helper, checkpoint, checkpoint_for_input)
    # Only format data collection start details if debug logging is enabled
    if is_debug_enabled(helper):
        helper.log_debug(
            "Starting data collection loop - Data type: {}, Start date: {}, End date: {}, Max duration: {} seconds"
            .format(data_type, checkpoint_for_input.get("start_date"), end_date, MAX_QUERYING_DURATION))

    loop_iteration = 0
    while start_date_done and (time.time() - start_time < MAX_QUERYING_DURATION):
        loop_iteration += 1
        elapsed_time = time.time() - start_time
        if is_debug_enabled(helper):
            helper.log_debug("Data collection loop iteration {} - Elapsed time: {:.2f}s, Events collected so far: {}"
                             .format(loop_iteration, elapsed_time, number_of_events))
        try:
            # collecting issues from the Egnyte server
            params['startDate'] = checkpoint_for_input.get("start_date")
            params['endDate'] = end_date
            params['auditType'] = data_type
            if params.get("nextCursor"):
                params.pop("startDate")
                params.pop("endDate")
                if is_debug_enabled(helper):
                    helper.log_debug("Using cursor-based pagination - NextCursor present")
            data_url = str(egnyte_domain_url) + "/pubapi/v2/audit/stream"

            # collect_issues raises TemporaryTokenError on 5xx/429
            data, error = collect_issues(helper, token, data_url, params, session_id)

            if error is not None:
                helper.log_error(error)
                if is_debug_enabled(helper):
                    helper.log_debug("Data collection failed at iteration {} after {:.2f}s with {} events collected"
                                     .format(loop_iteration, elapsed_time, number_of_events))
                send_ui_message(helper=helper, app_name=APP_NAME, session_key=session_key,
                                message="Unexpected response from Egnyte audit streaming API. See error log.")
                return

            # Handle case where data is None (shouldn't happen if error is None, but be safe)
            if data is None:
                helper.log_warning("No data returned from collect_issues. Skipping this iteration. Session ID: {}"
                                   .format(session_id))
                break

        except TemporaryTokenError as e:
            # Egnyte API temporarily unavailable (5xx/429) - skip polling cycle gracefully
            helper.log_warning(
                "Egnyte API temporarily unavailable during data collection (status {}). "
                "Skipping this polling cycle. Session ID: {}".format(e.status_code, session_id)
            )
            break
        except Exception as e:
            helper.log_error("Exception in data collection loop at iteration {}: {}. Session ID: {}"
                             .format(loop_iteration, str(e), session_id))
            raise e

        if data.get("events", ""):
            events = data.get("events")
            event_count = len(events)
            event_time = time.time()
            index = stanza.get("index", "main")
            source = "egnyte"
            sourcetype = "egnyte:connect:audit:{}".format(mapping_data_type.get(data_type))
            moreEventsflag = data.get("moreEvents")
            # Only format event processing details if debug logging is enabled
            if is_debug_enabled(helper):
                helper.log_debug("Processing {} events - Index: {}, Sourcetype: {}, MoreEvents: {}"
                                 .format(event_count, index, sourcetype, moreEventsflag))
            for i in events:
                event = helper.new_event(data=json.dumps(i), time=event_time, host=None, index=index, source=source,
                                         sourcetype=sourcetype, done=True, unbroken=True)
                ew.write_event(event)
            number_of_events = number_of_events + event_count
            # Only format batch processing details if debug logging is enabled
            if is_debug_enabled(helper):
                helper.log_debug(
                    "Batch processed {} events - Total events so far: {}".format(event_count, number_of_events))
        else:
            # Only log if debug logging is enabled
            if is_debug_enabled(helper):
                helper.log_debug("No events in response - continuing loop")

        if data.get("nextCursor"):
            params['nextCursor'] = data.get("nextCursor")
            checkpoint_for_input["nextCursor"] = data.get("nextCursor")
            set_checkpoint(helper, key=stanza_name, checkpoint=checkpoint_for_input)
            # Only log if debug logging is enabled
            if is_debug_enabled(helper):
                helper.log_debug("Checkpoint updated with nextCursor for pagination")
        else:
            start_date_done = False
            helper.log_info("Total indexed events into Splunk: {}".format(number_of_events))
            # Only log if debug logging is enabled
            if is_debug_enabled(helper):
                helper.log_debug("Data collection completed - No more cursors available")
        time.sleep(1)

    # Final summary for production monitoring
    total_duration = time.time() - start_time
    helper.log_info(
        "Data collection session completed - Total events: {}, Duration: {:.2f}s, Iterations: {}, Session ID: {}"
        .format(number_of_events, total_duration, loop_iteration, session_id))
