import time
import urllib
import splunk.entity
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from datetime import datetime
import os
import sys
import json
import traceback

GRAPH_ALERTS_URL = "https://graph.microsoft.com/v1.0/security/secureScores"
ACCESS_TOKEN = "access_token"
CLIENT_ID = "client_id"
CLIENT_SECRET = "client_secret"
LOCK_FILE = "not_first.lock"
ADDON_NAME = "TA-microsoft-graph-security-score"
LOCK_FILE_DIR = splunk_lib_util.make_splunkhome_path(["etc", "apps", ADDON_NAME, "local", "checkpoint"])
LOCK_FILE_PATH = os.path.join(LOCK_FILE_DIR, LOCK_FILE)


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""

    interval_in_seconds = int(definition.parameters.get("interval"))
    if interval_in_seconds < 300:
        raise ValueError("field 'Interval' should be at least 300")
    pass


def get_access_token(helper, application_id, secret, tenant):
    data = {
        CLIENT_ID: application_id,
        "scope": "https://graph.microsoft.com/.default",
        CLIENT_SECRET: secret,
        "grant_type": "client_credentials",
    }
    url = "https://login.microsoftonline.com/" + tenant + "/oauth2/v2.0/token"
    if sys.version_info > (3, 0):
        resp = helper.send_http_request(
            url, "POST", payload=urllib.parse.urlencode(data), timeout=(15.0, 15.0)
        )
    else:
        resp = helper.send_http_request(
            url, "POST", payload=urllib.urlencode(data), timeout=(15.0, 15.0)
        )
    if resp.status_code not in (201, 200):
        helper.log_error("Failed to get access_token. status_code={}, resp={}".format(resp.status_code, resp.text))
    resp.raise_for_status()
    access_token = resp.json()
    return access_token[ACCESS_TOKEN]


def get_app_version(helper):
    app_version = ""
    if "session_key" in helper.context_meta:
        session_key = helper.context_meta["session_key"]
        entity = splunk.entity.getEntity(
            "/configs/conf-app", "launcher", namespace=helper.get_app_name(), sessionKey=session_key, owner="nobody"
        )
        app_version = entity.get("version")
    return app_version


def get_epoch_time(data):
    utc_time = datetime.strptime(data, "%Y-%m-%dT%H:%M:%SZ")
    epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
    return epoch_time


def write_events(helper, ew, data):
    event = helper.new_event(
        source=helper.get_input_type(),
        index=helper.get_output_index(),
        sourcetype=helper.get_sourcetype(),
        data=json.dumps(data),
        time=get_epoch_time(data.get("createdDateTime")),
    )
    ew.write_event(event)


def check_lock_file(date=None):
    try:
        if not os.path.exists(LOCK_FILE_DIR):
            os.makedirs(LOCK_FILE_DIR)
        if date is None:
            if os.path.exists(LOCK_FILE_PATH):
                f = open(LOCK_FILE_PATH, "r")
                if f.mode == "r":
                    date = f.read()
                    return date
            else:
                return "False"
        else:
            with open(LOCK_FILE_PATH, "w") as fp:
                fp.write(date)

    except Exception:
        raise


def collect_events(helper, ew):
    try:
        start_time = time.time()
        helper.log_info("message=data_collection_start | Script invoked")
        opt_azure_ad_tenant_id = helper.get_arg("azure_ad_tenant_id")
        opt_application_id = helper.get_arg("application_id")
        stanza_name = helper.get_input_stanza_names()
        input_stanza = helper.get_input_stanza()
        opt_client_secret = input_stanza.get(stanza_name).get("client_secret")

        # set the log level for this modular input
        # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
        log_level = helper.get_log_level()
        helper.set_log_level(log_level)

        helper.log_debug("message=access_token | Trying to get access token")
        access_token = get_access_token(helper, opt_application_id, opt_client_secret, opt_azure_ad_tenant_id)
        helper.log_debug("message=access_token | Received the access token")

        headers = {
            "Authorization": "Bearer " + access_token,
            "User-Agent": "MicrosoftGraphSecuritySecureScore-Splunk/" + get_app_version(helper),
        }

        helper.log_info("message=api_call | Trying to get secure score details")
        response = helper.send_http_request(GRAPH_ALERTS_URL, "GET", headers=headers, timeout=(15.0, 15.0)).json()

        if "error" in response:
            helper.log_info(
                'Make sure your app with id {} has the Microsoft Graph "SecurityEvents.Read.All" permission and your tenant admin has given your application admin consent'.format(
                    opt_application_id
                )
            )
            raise ValueError("Error occurred : " + json.dumps(response, indent=4))

        helper.log_info("message=api_call | Received the secure score details")
        checkpoint = check_lock_file()
        helper.log_info("message=get_checkpoint | Received the checkpoint with value: {}".format(checkpoint))

        if checkpoint != "False":
            helper.log_info(
                "message=ingest_events | Ingesting all the events with a date greater than {}".format(checkpoint)
            )
            last_date = checkpoint
            latest_date = ""
            for data in response.get("value"):
                if latest_date == "":
                    latest_date = data.get("id").split("_")[1]
                    check_lock_file(latest_date)
                    helper.log_info(
                        "message=save_checkpoint | Saving the checkpoint with value: {}".format(latest_date)
                    )
                if latest_date != "" and data.get("id").split("_")[1] == latest_date and latest_date != last_date:
                    write_events(helper, ew, data)
        else:
            helper.log_info("message=ingest_events | Ingesting all the events received in response.")
            first_event = 0
            for data in response.get("value"):
                if first_event == 0:
                    check_lock_file(data.get("id").split("_")[1])
                    helper.log_info(
                        "message=save_checkpoint | Saving the checkpoint with value: {}".format(
                            data.get("id").split("_")[1]
                        )
                    )
                    first_event = 1
                write_events(helper, ew, data)

        helper.log_info(
            "message=data_collection_end | Execution of the script is finished. time_taken={} seconds.".format(
                time.time() - start_time
            )
        )

    except Exception as e:
        helper.log_error("message=unknown_error | error={} error_trace={}".format(str(e), traceback.format_exc()))
