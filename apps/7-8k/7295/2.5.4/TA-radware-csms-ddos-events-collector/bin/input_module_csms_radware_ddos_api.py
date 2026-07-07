# encoding = utf-8

import time
import datetime
import json
import requests
import logging
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


processed_event_ids = set()

# --- New: implicit page size for the API ---
PAGE_SIZE = 1000  # Assuming the API returns up to 1000 events per request

def epoch_millis_to_datetime(epoch_millis):
    """
    Convert epoch time in milliseconds to a datetime object.

    Args:
        epoch_millis (int): Time in milliseconds since the epoch.

    Returns:
        datetime: A datetime object representing the epoch time.
    """
    epoch_seconds = epoch_millis / 1000.0
    return datetime.datetime.fromtimestamp(epoch_seconds)


def validate_input(helper, definition):
    """
    Placeholder for input validation logic.

    Args:
        helper: Helper object with utilities.
        definition: Input definition.
    """
    pass


def retry_request(func, retries=3, delay=2):
    """
    A simple retry mechanism that retries the given function if certain exceptions are raised.

    Args:
        func (callable): The function to execute.
        retries (int): The maximum number of retries.
        delay (int): The delay between retries in seconds.

    Returns:
        Response: The response from the successful request.

    Raises:
        Exception: If all retry attempts fail.
    """
    attempt = 0
    while attempt < retries:
        try:
            return func()  # Try to execute the function (API call)
        except (requests.ConnectionError, requests.Timeout) as e:
            attempt += 1
            logger.error(f"Attempt {attempt}/{retries} failed with error: {e}")
            if attempt < retries:
                logger.info(f"Retrying after {delay} seconds...")
                time.sleep(delay)  # Wait before retrying
            else:
                logger.error(f"All {retries} attempts failed. Raising the exception.")
                raise  # Raise the exception after max retries


def getSecurityEvents(helper, api_key, timelower, timeupper, account_id, proxies=None, skip=0):
    """
    Fetch security events from Radware API (paged with 'skip').

    Args:
        helper: Helper object with utilities.
        api_key (str): API key for authentication.
        timelower (int): Lower bound of time window (epoch in ms).
        timeupper (int): Upper bound of time window (epoch in ms). (not used by API filter today)
        account_id (str): Account identifier.
        proxies (dict, optional): Proxy configuration.
        skip (int): Number of documents to skip for pagination.

    Returns:
        dict: Parsed JSON response with security events.
    """
    url = "https://api.radwarecloud.app/api/sdcc/attack/core/analytics/object/vision/securityevents"
    headers = {
        "x-api-key": api_key,
        "Context": account_id,
        "Content-Type": "application/json",
    }
    payload = {
        "criteria": [
            {"key": "startTimestamp", "value": [timelower, None]}
        ],
        # --- New: paginate with skip ---
        "skip": skip
    }

    def make_request():
        response = requests.post(url, headers=headers, data=json.dumps(payload), proxies=proxies)
        response.raise_for_status()
        return response

    try:
        response = retry_request(make_request, retries=3, delay=2)
        docs = response.json().get("documents", [])
        logger.debug(f"[Security] skip={skip} pulled={len(docs)}")
        return response.json()
    except Exception as e:
        logger.error(f"An error occurred while fetching security events (skip={skip}): {e}")
        raise


def severityConverter(severity):
    """
    Convert severity code to a human-readable string.

    Args:
        severity (str): Severity code.

    Returns:
        str: Severity level as a string.
    """
    if severity == "20":
        return "LOW"
    elif severity == "30":
        return "MEDIUM"
    elif severity == "40":
        return "HIGH"
    else:
        return severity


def getOperationalEvents(helper, api_key, timelower, timeupper, account_id, proxies=None, skip=0):
    """
    Fetch operational events from Radware API (paged with 'skip').

    Args:
        helper: Helper object with utilities.
        api_key (str): API key for authentication.
        timelower (int): Lower bound of time window (epoch in ms).
        timeupper (int): Upper bound of time window (epoch in ms). (not used by API filter today)
        account_id (str): Account identifier.
        proxies (dict, optional): Proxy configuration.
        skip (int): Number of documents to skip for pagination.

    Returns:
        dict: Parsed JSON response with operational events.
    """
    url = "https://api.radwarecloud.app/api/sdcc/infrastructure/core/analytics/object/operationalmessages/virtual"
    headers = {
        "x-api-key": api_key,
        "Context": account_id,
        "Content-Type": "application/json",
    }
    payload = {
        "criteria": [
            {"key": "timestamp", "value": [timelower, None]}
        ],
        # --- New: paginate with skip ---
        "skip": skip
    }

    def make_request():
        response = requests.post(url, headers=headers, data=json.dumps(payload), proxies=proxies)
        response.raise_for_status()
        return response

    try:
        response = retry_request(make_request, retries=3, delay=2)
        docs = response.json().get("documents", [])
        logger.debug(f"[Operational] skip={skip} pulled={len(docs)}")
        return response.json()
    except Exception as e:
        logger.error(f"An error occurred while fetching operational events (skip={skip}): {e}")
        raise


def format_speed(mbps):
    """
    Convert Mbps to a human-readable string in Mbps or Gbps.

    Args:
        mbps (float): Speed in Mbps.

    Returns:
        str: Formatted speed in Mbps, Gbps, or Kbps.
    """
    if mbps >= 1000:
        return f"{mbps / 1000:.3f} Gbps"
    elif mbps >= 1:
        return f"{mbps:.3f} Mbps"
    else:
        return f"{mbps * 1000:.3f} Kbps"


def deduplicate_events(new_events):
    """
    Deduplicate events by comparing the new event IDs with the set of processed event IDs.

    Args:
        new_events (list): List of new events to process.

    Returns:
        list: List of deduplicated new events.
    """
    global processed_event_ids
    deduplicated_events = []
    for event in new_events:
        event_id = event["_id"]  # Assuming the event has a unique '_id' field
        if event_id not in processed_event_ids:
            deduplicated_events.append(event)
            processed_event_ids.add(event_id)
    return deduplicated_events


def format_event(helper, ew, dict_events):
    """
    Format and write security and operational events to Splunk.

    Args:
        helper: Helper object with utilities.
        ew: Event writer object for Splunk.
        dict_events (dict): Dictionary of security and operational events.
    """
    security_event_keys = [
        "_id",
        "accountId",
        "timestamp",
        "startTimestamp",
        "attackId",
        "risk",
        "status",
        "sourceCountry",
        "sourceCountryCode",
        "siteName",
        "action",
        "accountName",
        "category",
        "targetAddress",
        "targetPort",
        "targetAddressValue",
        "sourceAddress",
        "sourcePort",
        "protocol",
        "packetBandwidth",
        "assetName",
        "duration",
        "averageBitRate",
        "averageByteRate",
        "averagePacketRate",
        "classification",
        "collectorType",
        "endTimestamp",
        "lastPeriodBitRate",
        "lastPeriodByteRate",
        "lastPeriodPacketRate",
        "maxBitRate",
        "maxByteRate",
        "maxPacketRate",
        "packetCount",
        "vectorId",
        "vectorName",
    ]

    for item in dict_events["security"]:
        build_event = "type=security,"
        for key in security_event_keys:
            if key in {"startTimestamp", "endTimestamp"}:
                value = epoch_millis_to_datetime(int(item.get(key, "")))
            else:
                value = str(item.get(key, ""))
            if value:
                build_event += f"{key}={value},"
        build_event = build_event.rstrip(",")
        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=build_event,
        )
        ew.write_event(event)

    for item in dict_events["operational"]:
        timestamp = item.get("timestamp", "")
        build_event = f"type=operational,_time={timestamp},"
        build_event += f"origin={item.get('triggerOrigin', '')},"
        build_event += f"code={item.get('triggerCode', '')},"
        build_event += f"id={item.get('_id', '')},"
        severity = severityConverter(str(item.get("severity", "")))
        build_event += f"severity={severity},"

        context = item.get("context", {})
        retries = context.get("retries", "")
        context_type = context.get("type", "")
        context_timestamp = context.get("_timestamp", "")

        build_event += f"context_retries={retries},"
        build_event += f"context_type={context_type},"
        build_event += f"context_timestamp={context_timestamp},"

        properties = context.get("properties", {})
        build_event += f"site_name={properties.get('site_name', '')},"
        build_event += f"reason={properties.get('reason', '')},"
        build_event += f"asset_name={properties.get('asset_name', '')},"
        build_event += f"account_notes={properties.get('account_notes', '').replace(',', ';')},"
        build_event += f"subject={properties.get('subject', '')},"
        build_event += f"account_name={properties.get('account_name', '')},"
        build_event += f"asset_ip={properties.get('asset_ip', '')},"
        build_event += f"description={properties.get('description', '')},"
        build_event += f"asset_notes={properties.get('asset_notes', '')},"
        build_event += f"asset={properties.get('asset', '')},"
        build_event += f"description={item.get('description', '')}"

        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=build_event,
        )

        ew.write_event(event)


def collect_events(helper, ew):
    """
    Collect security and operational events and write them to Splunk.
    Includes pagination using the 'skip' mechanism to retrieve all events in the interval.
    """
    proxy = helper.get_proxy()

    try:
        encoded_password = urllib.parse.quote(proxy['proxy_password'])
        proxies = {
            "http": f"http://{proxy['proxy_username']}:{encoded_password}@{proxy['proxy_url']}:{proxy['proxy_port']}",
            "https": f"http://{proxy['proxy_username']}:{encoded_password}@{proxy['proxy_url']}:{proxy['proxy_port']}"
        }
        logger.debug(f"Proxies configured: username {proxy['proxy_username']}, host {proxy['proxy_url']}, port {proxy['proxy_port']}")
    except KeyError:
        proxies = None
        logger.debug("No Proxies configured")

    try:
        stanza = helper.get_input_stanza()

        for key in stanza:
            interval = int(stanza[key]["interval"])
            if interval < 60:
                logger.debug("Interval configured is lower than 60. Aborting.")
                event = helper.new_event(
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype(),
                    data="Interval configured is lower than 60. Aborting."
                )
                ew.write_event(event)
                quit()

        now = int(round(time.time() * 1000))
        past = now - (interval * 1000) * 2  # Look back twice the interval to avoid missing events

        credentials = {
            "account_id": helper.get_arg("account_id"),
            "api_key": helper.get_arg("api_key"),
        }

        dict_events = {"security": [], "operational": []}

        # --- New: Page through SECURITY events ---
        total_sec = 0
        skip = 0
        while True:
            security_resp = getSecurityEvents(helper, credentials["api_key"], past, now, credentials["account_id"], proxies, skip=skip)
            security_docs = security_resp.get("documents", []) or []
            if not security_docs:
                break
            # Deduplicate and accumulate this page
            dict_events["security"].extend(deduplicate_events(security_docs))
            pulled = len(security_docs)
            total_sec += pulled
            if pulled < PAGE_SIZE:
                break
            skip += PAGE_SIZE
        logger.debug(f"Total security events pulled (pre-dedupe pages): {total_sec}, kept (post-dedupe): {len(dict_events['security'])}")

        # --- New: Page through OPERATIONAL events ---
        total_op = 0
        skip = 0
        while True:
            operational_resp = getOperationalEvents(helper, credentials["api_key"], past, now, credentials["account_id"], proxies, skip=skip)
            operational_docs = operational_resp.get("documents", []) or []
            if not operational_docs:
                break
            # Deduplicate and accumulate this page
            dict_events["operational"].extend(deduplicate_events(operational_docs))
            pulled = len(operational_docs)
            total_op += pulled
            if pulled < PAGE_SIZE:
                break
            skip += PAGE_SIZE
        logger.debug(f"Total operational events pulled (pre-dedupe pages): {total_op}, kept (post-dedupe): {len(dict_events['operational'])}")

        format_event(helper, ew, dict_events)

    except Exception as e:
        logger.error(f"Exception in collect_events: {e}")
        raise
