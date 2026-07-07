# encoding = utf-8
import os
import uuid

import sentry_sdk
import splunklib.client as client

import ta_egnyte_constants as tec
from ta_egnyte_protect_utility import *

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]


def validate_input(helper, definition):
    interval = float(definition.parameters.get('interval', None))
    if interval < 600:
        helper.log_error("Interval must be at least 600 seconds.")
        raise Exception('Interval must be at least 600 seconds')


def get_checkpoint(helper, stanza_name):
    return helper.get_check_point(stanza_name)


def set_checkpoint(helper, stanza_name, state):
    return helper.save_check_point(stanza_name, state)


def collect_events(helper, ew):
    session_id = str(uuid.uuid4())

    sentry_sdk.init(dsn="https://19851a77c8d0489b8638f25f0728d964@sentry-prod.egnyte.com/10")

    helper.log_info("Starting event collection. Session ID: {}".format(session_id))

    # getting setup parameters
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    clientid = input_stanza[input_name]['global_account']['client_id']
    client_secret = input_stanza[input_name]['global_account']['client_secret']
    code = input_stanza[input_name]['global_account']['password']
    stanza_name = list(input_stanza.keys())[0]
    stanza = list(input_stanza.values())[0]
    session_key = helper.context_meta['session_key']
    endpoint = helper.get_arg('endpoint')
    format_value = helper.get_arg('format')
    number_of_events = 0
    if endpoint == "US":
        base_url = tec.us_url
    else:
        base_url = tec.europe_url
    auth_url = str(base_url) + "/oauth2/token"

    # Connect to Splunk service
    helper.log_info("Connecting to Splunk service. Session ID: {}".format(session_id))
    service = client.connect(host='localhost', port=8089, token=session_key)

    # Wait for StoragePassword API to be available (critical for token management)
    helper.log_info("Checking StoragePassword API availability. Session ID: {}".format(session_id))
    try:
        wait_for_storage_password_api(service, helper, max_retries=10, initial_delay=1)
    except Exception as e:
        helper.log_error("StoragePassword API unavailable. Cannot proceed. Error: {}. Session ID: {}"
                         .format(str(e), session_id))
        sys.exit(1)

    # Get OAuth access token (refresh_token parameter is not used by provide_token, set to None)
    helper.log_info("Obtaining OAuth access token. Session ID: {}".format(session_id))
    try:
        token = provide_token(
            helper,
            auth_url,
            clientid,
            client_secret,
            code,
            stanza_name,
            None,
            APP_NAME,
            service,
            session_key,
            session_id,
        )
    except TemporaryTokenError as e:
        # Egnyte token endpoint is temporarily unavailable (e.g., 5xx/429 on
        # refresh or token generation). We keep the stored token and skip this
        # polling cycle so the next scheduled run can retry.
        helper.log_warning(
            "Egnyte token endpoint temporarily unavailable while obtaining access token (status {}). "
            "Skipping this polling cycle. Session ID: {}".format(e.status_code, session_id)
        )
        return

    # Get checkpoint for tracking data collection progress
    checkpoint = get_checkpoint(helper, stanza_name) or dict()

    if checkpoint.get("modifiedAfter"):
        data_url = str(base_url) + "/api/v1/issueupdates?modifiedAfter=" + str(checkpoint.get("modifiedAfter"))
        helper.log_info("Resuming from checkpoint modifiedAfter: {}. Session ID: {}"
                        .format(checkpoint.get("modifiedAfter"), session_id))
    else:
        data_url = str(base_url) + "/api/v1/issueupdates"
        helper.log_info("Starting fresh data collection (no checkpoint). Session ID: {}".format(session_id))

    modifiedAfter_done = True

    while modifiedAfter_done:
        try:
            # collecting issues from the Egnyte server
            if format_value and "modifiedAfter" in data_url and "format" not in data_url:
                data_url = "{}&format=full".format(data_url)
            else:
                data_url = "{}?format=full".format(data_url)

            helper.log_debug("Collecting issues from URL: {}. Session ID: {}".format(data_url, session_id))
            data = collect_issues(helper, token, data_url, session_id)

        except Exception as e:
            helper.log_error("Exception while collecting issues: {}. Session ID: {}".format(str(e), session_id))
            raise e

        # If data is None, Egnyte returned a non-200/401 response or a non-JSON
        # body. We treat this as a temporary/unexpected error and skip the rest of
        # this polling cycle without exiting the modular input.
        if data is None:
            helper.log_warning(
                "Egnyte API returned non-JSON or error response while collecting issues. "
                "Skipping this polling cycle. Session ID: {}".format(session_id)
            )
            break

        # Check if token is expired (401 Unauthorized)
        if data == 401:
            helper.log_error(
                "Received 401 Unauthorized. Access token may be expired or invalid. "
                "Please generate new code and update the input with new code. Egnyte session id: {}".format(
                    session_id
                )
            )
            sys.exit(1)

        # Validate data is a dictionary before accessing
        if not isinstance(data, dict):
            helper.log_error(
                "Unexpected data type received from API: {}. Session ID: {}".format(
                    type(data).__name__,
                    session_id,
                )
            )
            sys.exit(1)

        # indexing issues into Splunk
        if data.get("issues", ""):
            issues = data.get("issues")
            event_count = len(issues)
            event_time = time.time()
            index = stanza.get("index", "main")
            source = "egnyte"
            sourcetype = "egnyte:protect:incidents"

            helper.log_info("Indexing {} events. Session ID: {}".format(event_count, session_id))

            for i in issues:
                event = helper.new_event(data=json.dumps(i), time=event_time, host=None, index=index, source=source,
                                         sourcetype=sourcetype, done=True, unbroken=True)
                ew.write_event(event)

            number_of_events = number_of_events + event_count

            if data.get("modifiedAfter"):
                final_modifiedAfter = data.get("modifiedAfter")
                helper.log_debug("Collected events till: {}. Session ID: {}".format(final_modifiedAfter, session_id))
                data_url = str(base_url) + "/api/v1/issueupdates?modifiedAfter=" + str(final_modifiedAfter)

                checkpoint["modifiedAfter"] = int(final_modifiedAfter)
                set_checkpoint(helper, stanza_name, checkpoint)
                helper.log_debug("Checkpoint saved. Session ID: {}".format(session_id))
        else:
            modifiedAfter_done = False
            helper.log_info("No more issues to collect. Total indexed events into Splunk: {}. Session ID: {}"
                            .format(number_of_events, session_id))
