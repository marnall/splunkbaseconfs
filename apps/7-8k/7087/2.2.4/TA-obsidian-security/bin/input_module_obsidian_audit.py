import json

import jwt
import obsidian_queries
import obsidian_utils
import requests

# encoding = utf-8


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

AUDIT_LOGS_FETCH_TYPE = "obsidian:audit"


def validate_input(helper, definition):
    """Validate the arguments provided during adding of an input"""

    # validate the interval
    try:
        interval = int(definition.parameters.get("interval") or "300")
    except (ValueError, TypeError) as e:
        raise Exception(
            f"Invalid interval value: {definition.parameters.get('interval')} - {str(e)}"
        )
    if interval != -1 and interval < 300:
        raise Exception(
            "Interval must be greater or equal to 300, or -1 for one-time execution"
        )

    # obtain the api_token
    input_name = definition.metadata.get("name")
    session_key = definition.metadata.get("session_key")
    opt_obsidian_api_token = obsidian_utils.lookup_api_token(
        "obsidian_audit", input_name, session_key
    )

    # validate the other fields
    opt_subdomain = definition.parameters.get("subdomain")
    if (
        opt_subdomain.find(":") > -1
        or opt_subdomain.find("/") > -1
        or obsidian_utils.is_full_domain(opt_subdomain)
    ):
        raise Exception(
            "Subdomain: unexpected input. Please input only subdomain, not the full url."
        )
    token_payload = jwt.decode(
        opt_obsidian_api_token, options={"verify_signature": False}
    )
    token_subdomain_name = token_payload.get("aud")
    if token_subdomain_name:
        if token_subdomain_name.lower() != opt_subdomain.lower():
            raise Exception(
                f"The token is not valid for the given subdomain. The subdomain name is {token_subdomain_name}, but your input subdomain name is {opt_subdomain}, please check!"
            )
    else:
        helper.log_info(
            f'msg=The subdomain name in the token is not able to be validated. The subdomain name in token is:{token_subdomain_name}"'
        )

    opt_proxy_setting = definition.parameters.get("proxy_setting") or None
    obsidian_api_url = (
        definition.parameters.get("obsidian_api_url") or "https://api.obsec.io/v1/gql"
    )

    try:
        # set Obsidian API URL
        headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)

        gql_query = obsidian_queries.api_version_query()
        gql_payload = {"query": gql_query, "variables": {}}

        response = obsidian_utils.make_request(
            helper, gql_payload, headers, opt_proxy_setting, obsidian_api_url
        )
        response.raise_for_status()
        helper.log_info(
            f'msg="successfully connected to Obsidian API", org={opt_subdomain}, api_url={obsidian_api_url}'
        )
    except requests.HTTPError as e:
        helper.log_error(
            f'msg="HTTP Error: {e}", org={opt_subdomain}, api_url={obsidian_api_url}'
        )
        raise Exception(f"HTTP Error: {e}")


def fetch_audit_logs(
    helper,
    ew,
    headers,
    proxy_setting,
    subdomain,
    obsidian_api_url,
):
    last_audit_log_id_fetched = helper.get_check_point(f"{subdomain}_audit_logs")
    highest_id = 0
    if not last_audit_log_id_fetched:
        helper.log_info(
            f'msg="No existing checkpoint. Fetching audit logs from last 90 days", org={subdomain}, fetch_type={AUDIT_LOGS_FETCH_TYPE}'
        )
        # on the first run fetch audit logs for the last 90 days
        payload = {
            "filters": [
                {
                    "operator_id": "last",
                    "filter_config_id": "timestamp",
                    "values": [90],
                    "value_type": "number_posInteger",
                    "invert": False,
                    "unit": "days",
                }
            ],
            "limit": 1000,
            "order_by": [],
            "_page_number": 0,
        }
    else:
        last_audit_log_id_fetched = int(last_audit_log_id_fetched)
        helper.log_info(f"Fetching logs newer than id: {last_audit_log_id_fetched}")
        highest_id = last_audit_log_id_fetched
        # fetch all new logs since the last run
        payload = {
            "filters": [
                {
                    "operator_id": "",
                    "filter_config_id": "id",
                    "values": [last_audit_log_id_fetched],
                    "value_type": "number_posInteger",
                    "invert": False,
                    "unit": "",
                }
            ],
            "limit": 1000,
            "order_by": [],
            "_page_number": 0,
        }

    # replace /gql with /audit_logs
    obsidian_api_url = obsidian_api_url.replace("gql", "audit_logs")
    cursor = None
    has_more_results = True
    log_count = 0
    total_saved_logs = 0
    while has_more_results:
        if cursor:
            payload["cursor"] = cursor
        response = obsidian_utils.make_request(
            helper, payload, headers, proxy_setting, obsidian_api_url
        )

        if response.status_code != 200:
            helper.log_error(
                f"Failed to fetch data. Status code: {response.status_code}"
            )
            return total_saved_logs

        json_response = response.json()
        has_more_results = json_response.get("has_more_results", False)

        logs = json_response.get("data", [])
        if logs and len(logs) > 0:
            # the first log fetched should be the most recent and have the highest id
            first_log = logs[0]
            if not isinstance(first_log, dict):
                helper.log_error(f"Expected log to be dict, got {type(first_log)}")
                return total_saved_logs

            log_id = first_log.get("id", 0)
            try:
                current_id = int(log_id)
            except (ValueError, TypeError) as e:
                helper.log_error(f"Invalid log ID value: {log_id}, error: {e}")
                return total_saved_logs
            helper.log_debug(
                f"Current id fetched: {current_id} and highest id: {highest_id}"
            )
            # Compare and store the highest id
            if current_id > highest_id:
                highest_id = current_id
            elif last_audit_log_id_fetched:
                helper.log_debug("Not first run and no new logs fetched.")
                return total_saved_logs

            for log in logs:
                log_count += 1
                log_timestamp = log.get("timestamp")
                log_output = helper.new_event(
                    time=log_timestamp,
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype(),
                    data=json.dumps(log),
                )
                total_saved_logs += 1
                ew.write_event(log_output)

        cursor = json_response.get("cursor", None)

    helper.log_info(f"Saving checkpoint. Last id fetched: {highest_id}")
    helper.save_check_point(f"{subdomain}_audit_logs", highest_id)
    return total_saved_logs


def collect_events(helper, ew):
    """Event collection logic"""

    # Set log level
    helper.set_log_level(helper.get_log_level())

    # Set variables from input args
    opt_subdomain = obsidian_utils.sanitize_subdomain(helper.get_arg("subdomain"))
    opt_obsidian_api_token = helper.get_arg("api_token")
    proxy_setting = helper.get_arg("proxy_setting") or None
    obsidian_api_url = (
        helper.get_arg("obsidian_api_url") or "https://api.obsec.io/v1/gql"
    )

    headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)

    proxy_log_message = ""
    if proxy_setting:
        proxy_log_message = f" (proxy: {proxy_setting})"

    helper.log_info(
        f'msg="starting collection{proxy_log_message}", org={opt_subdomain}, fetch_type={AUDIT_LOGS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
    )

    try:
        count = fetch_audit_logs(
            helper,
            ew,
            headers,
            proxy_setting,
            opt_subdomain,
            obsidian_api_url,
        )
        helper.log_info(
            f'msg="fetch complete, saved {count} audit logs", org={opt_subdomain}, fetch_type={AUDIT_LOGS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            f'msg="caught HTTP exception in fetch_audit_logs: {e}", org={opt_subdomain}, fetch_type={AUDIT_LOGS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
    except Exception as e:
        helper.log_error(
            f'msg="caught exception in fetch_audit_logs: {e}", org={opt_subdomain}, fetch_type={AUDIT_LOGS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
