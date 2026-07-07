# encoding = utf-8

import os
import sys
import time
import datetime
import json

url = "https://{api_url}/api/v1/Audits/{id}"
ack_url = "https://{api_url}/api/v1/Audits/{id}"
TIMEOUT_IN_SECONDS = 20


def validate_input(helper, validation_definition):
    pass


def log_audit(helper, ew, data):
    timestamp = datetime.datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
    final_time = (timestamp - datetime.datetime.fromtimestamp(0)).total_seconds()
    try:
        event = helper.new_event(
            source=helper.get_input_stanza_names(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            time=final_time,
            data=json.dumps(data))
        ew.write_event(event)

    except Exception as e:
        helper.log_error('Error on parse event. ' + str(e))


def log_all_audits(helper, ew, siem_id, api_key, proxy_enabled, api_url):
    formatted_audits_url = url.format(api_url=api_url, id=siem_id)

    # Fetch the audit logs until there is no more audits to fetch
    while True:
        response = fetch_audit_logs(helper, formatted_audits_url, api_key, proxy_enabled)
        if response is None:
            break

        result = response.json()
        audit_logs, timestamp, page_id = parse_response(result)

        if audit_logs and page_id is not None:
            try:
                process_audits(helper, ew, audit_logs)
                helper.log_debug(f"Successfully sent logs, logs count: {len(audit_logs)}")
                acknowledge(helper, api_url, siem_id, api_key, proxy_enabled, timestamp, page_id)
            except Exception as e:
                helper.log_error(f"Error log audit: {e}")
                break
        else:
            # Exit the loop if there are no more audit logs
            break


def fetch_audit_logs(helper, formatted_audits_url, api_key, proxy_enabled):
    try:
        response = helper.send_http_request(
            formatted_audits_url, 'GET',
            headers={'Authorization': 'Bearer ' + api_key},
            timeout=TIMEOUT_IN_SECONDS,
            use_proxy=proxy_enabled)

        helper.log_debug(f'API status code is: {response.status_code}')
        return response
    except Exception as e:
        helper.log_error(f"Error fetching audit logs: {e}")
        return None


def parse_response(result):
    return (
        result.get('audits', '').strip().split('\n'),
        result.get('lastAuditTimestamp'),
        result.get('pageId')
    )


def process_audits(helper, ew, audits):
    for audit in audits:
        try:
            if audit:
                parsed_audit = json.loads(audit)
                log_audit(helper, ew, parsed_audit)
        except Exception as e:
            helper.log_error(f"Error formatting audit: {e}")
            helper.log_error(audit)
            raise e


def acknowledge(helper, api_url, siem_id, api_key, proxy_enabled, timestamp, page_id):
    helper.set_log_level('DEBUG')
    formatted_ack_url = url.format(api_url=api_url, id=siem_id)
    try:
        helper.send_http_request(
            formatted_ack_url, 'POST',
            payload={'timestamp': timestamp, 'pageId': page_id},
            headers={'Authorization': 'Bearer ' + api_key},
            timeout=TIMEOUT_IN_SECONDS,
            use_proxy=proxy_enabled)
        helper.log_debug(f"Successfully sent ack message, pageId: {page_id}, timestamp: {timestamp}")
    except Exception as e:
        helper.log_error(f"Error sending acknowledge message: {e}")
        raise e


def collect_events(helper, ew):
    """
    This method collects the oldest audits batch from Island Api.
    This script should run constantly in order to be near real time.
    :param helper: This is
    :param ew:
    :type ew splunklib.modularinput.EventWriter
    """
    helper.set_log_level('DEBUG')

    proxy_settings = helper.get_proxy()
    proxy_enabled = bool(proxy_settings)
    global_api_url = helper.get_global_setting("api_url")
    api_key_and_siem_id = helper.get_arg('api_key')
    siem_id, api_key = api_key_and_siem_id.split('|')

    log_all_audits(helper, ew, siem_id, api_key, proxy_enabled, global_api_url)
