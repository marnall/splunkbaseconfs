# Fetching the audit logs
# encoding = utf-8
import json
import time
from datetime import datetime
from urllib.parse import urlencode

import urllib3

urllib3.disable_warnings()

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # password = definition.parameters.get('password', None)


def collect_events(helper, ew):
    try:
        fqdn = helper.get_arg("cluster_fqdn")
        username = helper.get_arg("username")
        password = helper.get_arg("password")
        domain = helper.get_arg("user_domain")

        # Access Token
        token = get_access_token(helper, fqdn, username, password, domain)

        # Latest indexed timestamp.
        audit_cp_key = f"{helper.get_input_type()}-{fqdn}-audit-logs-ts"
        last_indexed_time_usecs = helper.get_check_point(audit_cp_key)

        # Current epoch time.
        curr_epoch_time_usecs = int(time.time() * 1_000_000)

        if last_indexed_time_usecs is None:
            helper.log_info("Last indexed time for audits is nil.")
            run_interval_in_secs = helper.get_arg("interval")
            helper.log_info(f"Run interval every {run_interval_in_secs} seconds.")

            if run_interval_in_secs is None:
                run_interval_in_secs = 60

            last_indexed_time_usecs = curr_epoch_time_usecs - (int(run_interval_in_secs) * 1_000_000)

        # Collect the alert logs
        helper.log_info(
            f"Collecting audit logs b/w time "
            f"{convert_usec_timestamp(last_indexed_time_usecs)}({last_indexed_time_usecs}) & "
            f"{convert_usec_timestamp(curr_epoch_time_usecs)}({curr_epoch_time_usecs})")

        collect_audit_logs(helper, ew, fqdn, token, last_indexed_time_usecs, curr_epoch_time_usecs, 0)  # noqa: E501

        # Save the index time.
        helper.save_check_point(audit_cp_key, curr_epoch_time_usecs)

    except Exception as e:
        raise e


# Function to generate the access token.
def get_access_token(helper, fqdn, username, password, domain):
    try:
        url = "https://%s/irisservices/api/v1/public/accessTokens" % fqdn  # Replace with the actual URL
        payload = {"username": username, "password": password, "domain": domain}
        headers = {"Content-Type": "application/json"}

        # REST Req
        response = helper.send_http_request(
            url,
            "POST",
            parameters=None,
            payload=payload,
            headers=headers,
            cookies=None,
            verify=False,
            cert=None,
            timeout=None,
            use_proxy=True,
        )

        # Check if the response status code is 201 (Created)
        if response.status_code == 201:
            token = response.json().get("accessToken")
            return token
        else:
            err_msg = f"Failed to obtain token. Status code: {response.status_code}, Response: {response.text}"
            helper.log_error(err_msg)
            raise RuntimeError(err_msg)

    except Exception as e:
        helper.log_error('Failed to obtain access token. Status code: ' + str(e))
        raise e


# Function to collect audit logs from configured cohesity cluster
def collect_audit_logs(helper, ew, fqdn, token, start_time_usecs, end_time_usecs, start_index):
    try:
        def_count = 100
        audit_logs = []
        # Query parameters
        params = {
            "count": def_count,
            "startIndex": start_index if start_index is not None else 0,
        }

        # Add start time param.
        if start_time_usecs is not None:
            params["startTimeUsecs"] = start_time_usecs

        # Add end time param.
        if end_time_usecs is not None:
            params["endTimeUsecs"] = end_time_usecs

        # Encode the query parameters
        query_string = urlencode(params)

        url = f"https://{fqdn}/v2/audit-logs?{query_string}"
        helper.log_info("Fetching audit logs using API %s" % url)

        # Headers.
        headers = {
            "Authorization": "Bearer %s" % token,
            "Content-Type": "application/json",
        }

        response = helper.send_http_request(
            url,
            "GET",
            parameters=None,
            headers=headers,
            cookies=None,
            verify=False,
            cert=None,
            timeout=None,
            use_proxy=True,
        )
        if response.status_code == 200:
            # json response
            audit_response_json = response.json()
            # Checkpoint
            for auditLog in audit_response_json["auditLogs"]:
                # Custom properties in the log.
                auditLog["timestamp"] = convert_usec_timestamp(auditLog["timestampUsecs"])
                auditLog["clusterHost"] = fqdn

                # Append to array.
                audit_logs.append(auditLog)

        # Log the count of audit log.
        helper.log_info("Processed %d audit logs" % len(audit_logs))

        # If there are records to add.
        if len(audit_logs) > 0:
            # To create a splunk event
            event = helper.new_event(
                json.dumps(audit_logs),
                time=None,
                host=None,
                index=None,
                source=None,
                sourcetype=None,
                done=True,
                unbroken=True,
            )
            ew.write_event(event)

        # Possibility of more records.
        if len(audit_logs) == def_count:
            return collect_audit_logs(helper, ew, fqdn, token, start_time_usecs, end_time_usecs,
                                      start_index + def_count)
    except Exception as e:
        helper.log_error('Failed to collect audit logs. Status code: ' + str(e))
        raise e


# Converts usec time to string format.
def convert_usec_timestamp(usec_timestamp):
    # Convert epoch time to a datetime object
    c_time = datetime.fromtimestamp(int(usec_timestamp / 1_000_000))
    # Format the datetime object to a human-readable string
    return c_time.strftime('%Y-%m-%d %H:%M:%S')
