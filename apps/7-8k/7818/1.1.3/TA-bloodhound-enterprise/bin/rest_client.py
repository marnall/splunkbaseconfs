"""
This module contains functions to interact with the BloodHound Enterprise API,
including making authenticated requests, handling responses, and logging etc.
"""
import datetime
import hmac
import hashlib
import base64
import os
import json
import requests
import logging
import time
from urllib.parse import urlparse


def log_error(helper, ew, function_name, error_message):
    """
    Logs errors in a structured JSON format for easy Splunk indexing
    Fixed to avoid circular reference and proper error handling
    """
    try:
        error_event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "function": function_name,
            "error": str(error_message),
        }

        event_data = json.dumps(error_event)

        # Use helper.log_error instead of calling log_error recursively
        helper.log_error(f"[ERROR] {event_data}")

        # Also write to Splunk as an event
        event = helper.new_event(
            source="BHE_script",
            index="main",  # Change if needed
            sourcetype="BHE:error",
            data=event_data,
        )
        ew.write_event(event)

    except Exception as e:
        # Last resort - just log to helper without creating events
        helper.log_error(f"Critical error in log_error function: {str(e)}")


def log_info(helper, ew, function_name, message, data=None, sourcetype="BHE:info"):
    """Logs informational messages in a structured JSON format for easy Splunk indexing"""
    try:
        info_event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "function": function_name,
            "message": message,
            "data": data if data else {},
        }
        event_data = json.dumps(info_event)
        # Use helper.log_info instead of calling log_info recursively
        helper.log_info(f"[INFO] {event_data}")
        # Also write to Splunk as an event
        event = helper.new_event(
            source="BHE_script",
            index="main",  # Change if needed
            sourcetype=sourcetype,
            data=event_data,
        )
        ew.write_event(event)
    except Exception as e:
        # Last resort - just log to helper without creating events
        helper.log_error(f"Critical error in log_info function: {str(e)}")


def make_cypher_request(helper, ew, query_payload):
    """
    Make a Cypher query request to BloodHound Enterprise API using JWT + HMAC authentication
    Fixed version with better error handling
    """
    try:
        # Get authentication details
        account = helper.get_arg("bloodhound_account")
        token_id = account.get("token_id")
        token_key = account.get("token_key")
        base_url = account.get("domain_name")

        # Debug logging
        helper.log_info(f"Account config - base_url: {base_url}, token_id: {token_id}")

        # Prepare the request
        uri = "/api/v2/graphs/cypher"
        payload_json = json.dumps(query_payload)

        helper.log_info(f"Making Cypher request to: {base_url}{uri}")
        helper.log_debug(f"Query payload: {payload_json}")

        # Use fetch_data to make the request
        response = fetch_data(
            helper=helper,
            ew=ew,
            token_id=token_id,
            token_key=token_key,
            domain_name=base_url,
            uri=uri,
            method="POST",
            payload=payload_json,
        )

        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None

        if response:
            helper.log_info("Cypher query executed successfully")
            return response
        else:
            log_error(
                helper,
                ew,
                "make_cypher_request",
                "Cypher query failed - no response received after retries",
            )
            return None

    except Exception as e:
        log_error(
            helper, ew, "make_cypher_request", f"Error making Cypher request: {str(e)}"
        )
        return None


def header_generator(
    helper,
    ew,
    token_id: str,
    token_key: str,
    method: str,
    uri: str,
    payload: str = None,
) -> dict:
    """
    generates the HMAC header.
    """
    try:
        datetime_formatted = datetime.datetime.now().astimezone().isoformat("T")

        # HMAC calculation: method + uri
        digester = hmac.new(token_key.encode(), None, hashlib.sha256)
        digester.update(f"{method}{uri}".encode())
        digester = hmac.new(digester.digest(), None, hashlib.sha256)

        # Add timestamp (hour precision)
        digester.update(datetime_formatted[:13].encode())
        digester = hmac.new(digester.digest(), None, hashlib.sha256)

        # Add payload if provided
        if payload:
            digester.update(payload.encode())

        signature = base64.b64encode(digester.digest()).decode()

        headers = {
            "User-Agent": "BHE-Splunk-v1.1.0",
            "Authorization": f"bhesignature {token_id}",
            "RequestDate": datetime_formatted,
            "Signature": signature,
            "Content-Type": "application/json",
        }

        return headers
    except Exception as e:
        log_error(helper, ew, "header_generator", e)
        return None


def _ssl_verify(helper):
    """Return True to verify SSL certs, False to skip (e.g. for internal CA). Default True."""
    try:
        val = helper.get_global_setting("verify_ssl_certificates")
        if val is None:
            return True
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("1", "true", "yes")
    except Exception:
        return True


def fetch_data(
    helper, ew, token_id, token_key, domain_name, uri, method="GET", payload=None
):
    """
    fetches data by making API Requests with retry logic.
    Returns:
        - Response data on success
        - "UNAUTHORIZED" if 401/403 (should stop execution)
        - None if retries exhausted (should continue to next item)
    """
    helper.log_info("Fetching data...")
    
    if not domain_name.startswith("https://"):
        domain_name = "https://" + domain_name

    url_parser = urlparse(domain_name)
    domain_name = f"https://{url_parser.netloc}"

    url = f"{domain_name}{uri}"

    # Fetch proxy configuration
    proxy_settings = helper.get_proxy()
    use_proxy = bool(proxy_settings)  # Enable proxy only if configured

    verify_ssl = _ssl_verify(helper)
    helper.log_info(f"[CONFIG] verify_ssl={verify_ssl}")

    max_retries = 10
    retry_count = 0
    base_sleep_time = 2  # Base sleep time in seconds

    while retry_count <= max_retries:
        try:
            # Generate headers for each retry attempt (timestamp changes)
            headers = header_generator(helper, ew, token_id, token_key, method, uri, payload)
            if not headers:
                log_error(helper, ew, "fetch_data", "Failed to generate headers")
                return None

            response = helper.send_http_request(
                url,
                method,
                parameters=None,
                payload=payload,
                headers=headers,
                cookies=None,
                verify=verify_ssl,
                cert=None,
                timeout=None,
                use_proxy=use_proxy,  # Let Splunk handle proxy automatically
            )

            status_code = response.status_code

            # Handle unauthorized/forbidden - stop execution
            if status_code == 401 or status_code == 403:
                msg = f"Unauthorized/Forbidden error [{status_code}] - {response.text}"
                log_error(helper, ew, "fetch_data", msg)
                helper.log_error(f"[ERROR] Authentication failed. Stopping execution. Status: {status_code}")
                return "UNAUTHORIZED"

            # Handle success
            if status_code == 200:
                if "title.md" in uri or "type.md" in uri:
                    r_md = response.text
                    return r_md.strip()
                else:
                    r_json = response.json()
                    return r_json

            # Handle other errors (429 rate limit, 500, etc.) - retry
            else:
                if retry_count < max_retries:
                    # Exponential backoff with jitter
                    sleep_time = base_sleep_time * (2 ** retry_count) + (retry_count * 0.5)
                    helper.log_info(
                        f"[RETRY] Request failed with status {status_code}. "
                        f"Retrying ({retry_count + 1}/{max_retries}) after {sleep_time:.2f}s. "
                        f"URI: {uri}"
                    )
                    time.sleep(sleep_time)
                    retry_count += 1
                    continue
                else:
                    # Max retries exceeded
                    msg = f"Request failed after {max_retries} retries. Status: {status_code}, Response: {response.text}"
                    log_error(helper, ew, "fetch_data", msg)
                    helper.log_error(
                        f"[ERROR] Max retries ({max_retries}) exceeded for URI: {uri}. "
                        f"Status: {status_code}. Skipping and continuing."
                    )
                    return None

        except (ConnectionError, requests.exceptions.RequestException) as e:
            if retry_count < max_retries:
                sleep_time = base_sleep_time * (2 ** retry_count) + (retry_count * 0.5)
                helper.log_info(
                    f"[RETRY] Connection error: {str(e)}. "
                    f"Retrying ({retry_count + 1}/{max_retries}) after {sleep_time:.2f}s. "
                    f"URI: {uri}"
                )
                time.sleep(sleep_time)
                retry_count += 1
                continue
            else:
                log_error(helper, ew, "fetch_data", f"Connection error after {max_retries} retries: {str(e)}")
                helper.log_error(
                    f"[ERROR] Max retries ({max_retries}) exceeded for URI: {uri} due to connection error. "
                    f"Skipping and continuing."
                )
                return None
        except Exception as e:
            # For unexpected exceptions, log and return None to continue
            log_error(helper, ew, "fetch_data", f"Unexpected error: {str(e)}")
            helper.log_error(f"[ERROR] Unexpected error for URI: {uri}. Skipping and continuing.")
            return None

    # Should not reach here, but return None as fallback
    return None


def validate_response_object(helper, ew, result):
    """
    Error handling function on basis of status code.
    """
    code = result.status_code
    logging.info(f"This is response code received {code}")

    if code != requests.codes.ok:
        msg = str()
        if code == requests.codes.unauthorized or code == requests.codes.forbidden:
            code = None
            msg = f"Error authenticating to BloodHound Domain [{result.status_code}] - {result.text}"
        elif code == requests.codes.not_found:
            code = None
            msg = f"Error Domain not Found [{result.status_code}] - Check your Domain"
        else:
            code = None
            msg = f"Unknown Error [{result.status_code}] - {result.text}"

        log_error(helper, ew, "validate_response_object", msg)
    return code


def load_state(log_location, file_name, data_input_directory):
    """
    This method is used by audit logs input type.
    loads the last polling time to avoid redundancy.
    """
    file_dir = os.path.join(log_location, data_input_directory, str(file_name))
    filepath = os.path.join(file_dir, "state.txt")
    state = None
    if os.path.exists(filepath) and os.stat(filepath).st_size != 0:
        with open(filepath, "r") as json_file:
            state_str = json_file.read()
            state = json.loads(state_str)
    return state


def save_state(state, log_location, file_name, data_input_directory):
    """
    This method is used by audit logs input type.
    saves the last polling time for logs to avoid redundancy.
    """
    file_dir = os.path.join(log_location, data_input_directory, str(file_name))
    filepath = os.path.join(file_dir, "state.txt")
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(filepath, "w") as json_file:
        state_str = json.dumps(state)
        json_file.write(str(state_str))


def get_available_domains(helper, ew):
    """
    Fetches all available domains.
    """
    helper.log_info("Initiated fetching domains.")
    bloodhound_account = helper.get_arg("bloodhound_account")
    uri = "/api/v2/available-domains"
    response = fetch_data(
        helper,
        ew,
        token_id=bloodhound_account["token_id"],
        token_key=bloodhound_account["token_key"],
        domain_name=bloodhound_account["domain_name"],
        uri=uri,
    )
    if response == "UNAUTHORIZED":
        helper.log_error("[ERROR] Unauthorized access. Cannot fetch domains. Stopping execution.")
        return None
    if response:
        helper.log_info("Successfully fetched all domains.")
    return response


def get_available_types(helper, ew, available_domains):
    """
    Fetches all the types for each domain.
    """
    helper.log_info("Initiated fetching available types.")
    bloodhound_account = helper.get_arg("bloodhound_account")
    available_types = {}
    for domain in available_domains:
        uri = f"/api/v2/domains/{domain}/available-types"
        response = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )
        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None
        if response:
            # Handle case where data might be None
            available_types[domain] = response.get("data") or []
        # If response is None (retries exhausted), continue to next domain
    helper.log_info("Successfully fetched available types.")
    return available_types


def get_path_titles(helper, ew, available_types):
    """
    Fetches Path titles
    """
    helper.log_info("Initiated fetching attack path titles")
    bloodhound_account = helper.get_arg("bloodhound_account")
    path_titles = {}
    for finding_type in {ft for types in available_types.values() for ft in types}:
        uri = f"/api/v2/assets/findings/{finding_type}/title.md"
        title = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )
        if title == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None
        if title:
            path_titles[finding_type] = title
        # If title is None (retries exhausted), continue to next finding type
    helper.log_info("Successfully fetched all attack path titles.")
    return path_titles


def get_attack_path_details(helper, ew, dom, finding_type):
    """
    Fetches Attack Path Details.
    """
    skip: int = 0
    bloodhound_account = helper.get_arg("bloodhound_account")
    attack_path_details = []
    while True:
        uri = f"/api/v2/domains/{dom}/details?finding={finding_type}&skip={skip}"
        response = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )
        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None
        if not response:
            # Retries exhausted, skip this batch and continue
            helper.log_info(f"Skipping batch at skip={skip} due to failed request")
            skip += 10  # Increment by reasonable batch size to skip failed batch
            continue
        # Handle case where data might be None
        attack_path_detail = response.get("data") or []
        helper.log_debug(
            f" Findings retrive : {len(response)} for domain ID : {dom} and Finding Type : {finding_type} with skip value : {skip}"
        )
        if len(attack_path_detail) == 0:
            break
        for item in attack_path_detail:
            attack_path_details.append(item)
        skip += len(attack_path_detail)
    return attack_path_details


def get_attack_path_timeline(helper, ew, dom, finding_type, fromDate):
    """
    Fetches Attack Path Timeline.
    """
    helper.log_info("Initiated fetching attack path timeline.")
    bloodhound_account = helper.get_arg("bloodhound_account")
    uri = f"/api/v2/domains/{dom}/sparkline?finding={finding_type}&from={fromDate}"
    response = fetch_data(
        helper,
        ew,
        token_id=bloodhound_account["token_id"],
        token_key=bloodhound_account["token_key"],
        domain_name=bloodhound_account["domain_name"],
        uri=uri,
    )
    if response == "UNAUTHORIZED":
        helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
        return None
    if response:
        log_info(
            helper,
            ew,
            "get_attack_path_timeline",
            f"Fetched timeline for domain ID: {dom}, finding type: {finding_type}, from date: {fromDate}",
            sourcetype="BHE:path_timeline",
        )
        helper.log_info("Successfully fetched attack path timeline.")
        # Handle case where data might be None
        return response.get("data") or []
    # Retries exhausted, return empty list to continue
    return []


def get_finding_trends(helper, ew, environment_id, startDate):
    """
    Fetches finding trends from the BloodHound Enterprise API for a given environment SID
    and a specified start date.
    """
    try:
        helper.log_info(
            f"Initiated fetching finding trends for environment: {environment_id} starting from {startDate}"
        )
        bloodhound_account = helper.get_arg("bloodhound_account")

        uri = f"/api/v2/attack-paths/finding-trends?environments={environment_id}&start={startDate}"

        response = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )

        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None

        if not response:
            log_error(
                helper, ew, "get_finding_trends", "Failed to fetch finding trends after retries"
            )
            return []

        if "data" not in response:
            log_error(
                helper, ew, "get_finding_trends", "Response does not contain 'data' key"
            )
            return []

        return response
    except Exception as e:
        log_error(
            helper, ew, "get_finding_trends", f"Error fetching finding trends: {str(e)}"
        )
        return []


def get_posture_history(helper, ew, data_type, environment_id, startDate):
    """
    Fetches posture history data from the BloodHound Enterprise API for a given environment SID.
    """
    try:
        helper.log_info(
            f"Initiated fetching posture history for data type: {data_type} and environment ID: {environment_id}"
        )
        bloodhound_account = helper.get_arg("bloodhound_account")

        uri = f"/api/v2/posture-history/{data_type}?environments={environment_id}&start={startDate}"

        response = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )

        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None

        if not response:
            log_error(
                helper, ew, "get_posture_history", "Failed to fetch posture history after retries"
            )
            return []

        log_info(
            helper,
            ew,
            "get_posture_history",
            f"Fetched posture history for environment ID: {environment_id}, data type: {data_type}, start date: {startDate}",
            sourcetype="BHE:Posture_history",
        )

        if "data" not in response:
            log_error(
                helper,
                ew,
                "get_posture_history",
                "Response does not contain 'data' key",
            )
            return []

        # Handle case where data might be None
        return response.get("data") or []
    except Exception as e:
        log_error(
            helper,
            ew,
            "get_posture_history",
            f"Error fetching posture history: {str(e)}",
        )
        return []


def get_audit_logs(helper, ew, after):
    """
    Fetches Audit Logs
    """
    helper.log_info("Initiated fetching audit logs.")
    skip: int = 0
    bloodhound_account = helper.get_arg("bloodhound_account")
    audit_logs = []
    while True:
        uri = f"/api/v2/audit?after={after}&skip={skip}"
        helper.log_info(f"Fetching data from URI: {uri}")

        response = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )
        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None
        if not response:
            # Retries exhausted, skip this batch and continue
            helper.log_info(f"Skipping audit log batch at skip={skip} due to failed request")
            skip += 10  # Increment by reasonable batch size to skip failed batch
            continue
        # Handle case where data might be None
        data = response.get("data") or {}
        partial_audit_logs = data.get("logs") or []
        helper.log_info(f"Retrieved {len(partial_audit_logs)} logs")

        skip = skip + len(partial_audit_logs)
        if len(partial_audit_logs) == 0:
            helper.log_info("No more logs to fetch, exiting loop")
            break
        for log in partial_audit_logs:
            audit_logs.append(log)
    helper.log_info("Successfully fetched audit logs.")
    return audit_logs


def get_posture_stats(helper, ew, domain):
    """
    Fetches Posture Statistics
    """
    helper.log_info("Initiated fetching posture statistics.")
    bloodhound_account = helper.get_arg("bloodhound_account")
    skip: int = 0
    posture_stats = []
    while True:
        uri = f"/api/v2/posture-stats?skip={skip}&domain_sid=eq:{domain.get('id')}"
        helper.log_info(f"Fetching posture stats from: {uri}")
        response = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )
        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None
        if not response:
            # Retries exhausted, skip this batch and continue
            helper.log_info(f"Skipping posture stats batch at skip={skip} due to failed request")
            skip += 10  # Increment by reasonable batch size to skip failed batch
            continue
        # Handle case where data might be None
        partial_posture_stats = response.get("data") or []
        if len(partial_posture_stats) == 0:
            helper.log_info(f"No more posture stats to fetch for domain {domain.get('id')}")
            break
        skip = skip + len(partial_posture_stats)
        for item in partial_posture_stats:
            posture_stats.append(item)
        helper.log_info(f"Retrieved {len(partial_posture_stats)} posture stats")
    helper.log_info("Successfully fetched posture statistics")
    return posture_stats


def get_asset_group_ids(helper, ew):
    """
    fetches asset group ids.
    """
    bloodhound_account = helper.get_arg("bloodhound_account")
    uri = "/api/v2/asset-groups?tag=eq%3Aadmin_tier_0"
    helper.log_info(f"Fetching asset groups from: {uri}")
    response = fetch_data(
        helper,
        ew,
        token_id=bloodhound_account["token_id"],
        token_key=bloodhound_account["token_key"],
        domain_name=bloodhound_account["domain_name"],
        uri=uri,
    )
    if response == "UNAUTHORIZED":
        helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
        return None
    if not response:
        helper.log_error("[ERROR] Failed to fetch asset group ids after retries")
        return []
    # Handle case where data might be None, and asset_groups might be None
    data = response.get("data") or {}
    asset_groups = data.get("asset_groups") or []
    asset_group_ids = [group["id"] for group in asset_groups]
    helper.log_info(f"Successfully fetched asset groups from: {uri}")
    return asset_group_ids


def get_asset_members(helper, ew, id, domain):
    """
    fetches asset members.
    """
    helper.log_info("Intiated fetching asset members.")
    bloodhound_account = helper.get_arg("bloodhound_account")
    skip: int = 0
    asset_members = []
    while True:
        uri = f"/api/v2/asset-groups/{id}/members?skip={skip}&environment_id=eq:{domain.get('id')}"
        helper.log_info(f"[INFO] Fetching asset members for group {id}")
        response = fetch_data(
            helper,
            ew,
            token_id=bloodhound_account["token_id"],
            token_key=bloodhound_account["token_key"],
            domain_name=bloodhound_account["domain_name"],
            uri=uri,
        )
        if response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            return None
        if not response:
            # Retries exhausted, skip this batch and continue
            helper.log_info(f"Skipping asset members batch at skip={skip} due to failed request")
            skip += 10  # Increment by reasonable batch size to skip failed batch
            continue
        # Handle case where data might be None, and members might be None
        data = response.get("data") or {}
        partial_asset_members = data.get("members") or []

        helper.log_info(
            f"[INFO] Retrieved {len(partial_asset_members)} members for group {id}"
        )
        if len(partial_asset_members) == 0:
            helper.log_info(f"[INFO] No more members to fetch for group {id}")
            break
        skip += len(partial_asset_members)
        for item in partial_asset_members:
            asset_members.append(item)
    helper.log_info("Successfully fetched all tier zero asset members.")
    return asset_members

