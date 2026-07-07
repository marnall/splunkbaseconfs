import json
from datetime import datetime, timezone

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

POSTURE_RULES_FETCH_TYPE = "obsidian:posture_rules"


def validate_input(helper, definition):
    """Validate the arguments provided during adding of an input"""

    # validate the interval
    try:
        interval = int(definition.parameters.get("interval") or "86400")
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
        "obsidian_posture_rules", input_name, session_key
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


def fetch_posture_rules(
    helper,
    ew,
    headers,
    proxy_setting,
    subdomain,
    obsidian_api_url,
):
    helper.log_info(
        f'msg="Fetching posture rules", org={subdomain}, fetch_type={POSTURE_RULES_FETCH_TYPE}'
    )

    saved_rules = 0
    session_key = helper.context_meta.get("session_key")
    if not session_key:
        helper.log_error("Session key not found in context metadata")
        return saved_rules

    payload = {"limit": 1000, "cursor": ""}

    # https://api.obsec.io/v1/gql
    # https://api.obsec.io/posture/v1_0/rules/list
    obsidian_api_url = obsidian_api_url.replace("v1/gql", "posture/v1_0/rules/list")
    rules = obsidian_utils.fetch_list(
        helper, "rules", "rules", payload, headers, proxy_setting, obsidian_api_url
    )
    current_time = datetime.now(timezone.utc)

    for rule in rules:
        rule_output = helper.new_event(
            time=current_time,  # using current time since creation time is not available in the list endpoint
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=json.dumps(rule),
        )
        ew.write_event(rule_output)
        saved_rules += 1

    helper.log_info(f"Saved {saved_rules} rules")
    return saved_rules


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
        f'msg="starting collection{proxy_log_message}", org={opt_subdomain}, fetch_type={POSTURE_RULES_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
    )

    try:
        count = fetch_posture_rules(
            helper,
            ew,
            headers,
            proxy_setting,
            opt_subdomain,
            obsidian_api_url,
        )
        helper.log_info(
            f'msg="fetch complete, saved {count} posture rules", org={opt_subdomain}, fetch_type={POSTURE_RULES_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            f'msg="caught HTTP exception in fetch_posture_rules: {e}", org={opt_subdomain}, fetch_type={POSTURE_RULES_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
    except Exception as e:
        helper.log_error(
            f'msg="caught exception in fetch_posture_rules: {e}", org={opt_subdomain}, fetch_type={POSTURE_RULES_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
