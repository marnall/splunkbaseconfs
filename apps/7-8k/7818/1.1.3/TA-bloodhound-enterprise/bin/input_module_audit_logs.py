"""
Module for Audit Logs data input for BloodHound Enterprise.
"""
import json
import time

from rest_client import save_state, load_state, get_audit_logs, log_error
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

_APP_NAME = "TA-bloodhound-enterprise"
LOG_PATH = make_splunkhome_path(["var", "log", "splunk", _APP_NAME])


def validate_input(helper, definition):
    """
    Validation function as required by the Splunk add-on framework.
    """
    pass


def convert_days_to_rfc_timestamp(helper, days: int) -> str:
    """
    Converts a number of days in the past into an RFC 3339 timestamp string.
    """
    helper.log_info(f"[INFO] Converting {days} days to RFC timestamp")
    current_epoch_time = time.time()
    start_epoch_time = int(current_epoch_time - days * 24 * 3600)
    rfc_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_epoch_time))
    helper.log_debug(f"[DEBUG] Converted timestamp: {rfc_timestamp}")
    return rfc_timestamp


def load_last_polling_time(
    helper, file_identifier: str, historical_days: int, account_domain: str
) -> str:
    """
    Loads the last polling time from state, or calculates it based on
    historical days.
    """
    state = load_state(LOG_PATH, file_identifier, "audit_log_data_input")
    if state:
        last_poll_time = state.get("latest_polling_time")
        helper.log_info(
            f"[INFO] Loaded previous state, polling after: " f"{last_poll_time}"
        )
    else:
        last_poll_time = convert_days_to_rfc_timestamp(helper, historical_days)
        helper.log_info(
            f"[INFO] No previous state found, starting polling "
            f"from: {last_poll_time}"
        )
    return last_poll_time


def save_latest_polling_time(helper, file_identifier: str):
    """
    Saves the latest polling time to state.
    """
    latest_state = {"latest_polling_time": convert_days_to_rfc_timestamp(helper, 0)}
    helper.log_info(f"[INFO] Saving new state: {latest_state}")
    save_state(latest_state, LOG_PATH, file_identifier, "audit_log_data_input")


def write_audit_log_event(helper, ew, log_entry: dict):
    """
    Prepares and writes a single audit log entry as a Splunk event.
    """
    event_json = json.dumps(log_entry)
    splunk_event = helper.new_event(
        event_json,
        time=None,
        host=None,
        index=helper.get_output_index(),
        source=None,
        sourcetype="BHE:audit_logs",
        done=True,
        unbroken=True,
    )
    ew.write_event(splunk_event)


def process_audit_logs(helper, ew, domain_name: str, last_poll_time: str):
    """
    Fetches audit logs and writes them as events to Splunk.
    """
    audit_logs = get_audit_logs(helper, ew, last_poll_time)
    if audit_logs is None: 
        helper.log_error("[ERROR] Unauthorized access. Stopping audit log collection.")
        return
    if not audit_logs: 
        helper.log_info("[INFO] No audit logs retrieved or retries exhausted.")
        return
    for log_entry in audit_logs:
        log_entry["source_domain"] = domain_name
        write_audit_log_event(helper, ew, log_entry)


def collect_events(helper, ew):
    """
    Main event collection function for Audit Logs.
    Handles all exceptions here and logs errors.
    """
    helper.log_info("[INFO] collect_events started")
    try:
        source_name = helper.get_arg("name")
        index_name = helper.get_arg("index")
        file_identifier = f"{source_name}-{index_name}"
        bloodhound_account_info = helper.get_arg("bloodhound_account")
        historical_days = int(helper.get_arg("historical_polling_days"))
        domain_name = bloodhound_account_info.get("domain_name")

        helper.log_info(
            f"[INFO] Source: {source_name}, Index: {index_name}, "
            f"File: {file_identifier}"
        )
        helper.log_info(f"[INFO] Historical polling days: {historical_days}")

        last_poll_time = load_last_polling_time(
            helper, file_identifier, historical_days, domain_name
        )

        # Process audit logs and write events
        process_audit_logs(helper, ew, domain_name, last_poll_time)

        save_latest_polling_time(helper, file_identifier)

    except Exception as e:
        log_error(helper, ew, "audit_logs_collect_events", e)

