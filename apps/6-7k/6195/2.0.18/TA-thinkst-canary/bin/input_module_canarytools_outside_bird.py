
# encoding = utf-8

import base64
import json
import os
import sys
import time

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # Add validation logic here if needed
    return True

def collect_events(helper, ew):
    DEFAULT_TIMEOUT = (10.0, 30.0)
    PAGE_LIMIT = 1000
    CANARY_DOMAIN_SUFFIX = ".canary.tools"

    helper.log_info("TA-thinkst-canary: = = Start Log  = =")
    
    global_account = helper.get_arg("canary_console")
    domain_hash = global_account["username"]
    api_key = global_account["password"]
    if not domain_hash.endswith(CANARY_DOMAIN_SUFFIX):
        domain_hash += CANARY_DOMAIN_SUFFIX

    helper.log_info(f"TA-thinkst-canary: Canary Console hosted at = {domain_hash}")

    proxy = helper.get_proxy()
    if proxy:
        helper.log_info("TA-thinkst-canary: Proxy is set")
        helper.log_debug(f"TA-thinkst-canary: Proxy Type: {proxy['proxy_type']}, Proxy URL: {proxy['proxy_url']}, Proxy Port: {proxy['proxy_port']}")
        if proxy["proxy_username"]:
            helper.log_info("TA-thinkst-canary: Proxy is configured for authentication")
        else:
            helper.log_info("TA-thinkst-canary: Proxy is configured without authentication")
        proxy_config = True 
    else:
        helper.log_info("TA-thinkst-canary: Proxy is not set")
        proxy_config = False
    
    try:
        ta_version = [ i for i in helper.service.apps.list() if i.name == helper.app][0].content["version"]
        helper.log_info(f"TA-thinkst-canary: TA version retrieved = {ta_version}")
    except:
        ta_version = "N/A"
        helper.log_info("TA-thinkst-canary: No TA version available.")
    
    try:
        splunk_version =  helper.service.info["version"]
        helper.log_info(f"TA-thinkst-canary: Splunk version retrieved = {splunk_version}")
    except KeyError:
        splunk_version = "Unknown_version"
        helper.log_info("TA-thinkst-canary: No Splunk version available.")

    def get_update_id_from_cursor(cursor):
        return int(base64.b64decode(cursor).decode().split(':')[1])
    
    def get_change_count(last_updates, current_entry):
        key = f"{current_entry['node_id']}:{current_entry['ip_address']}"
        if not last_updates or key not in last_updates:
            return 1
        return current_entry["count"] - last_updates[key]
            

    def send_request(url, params=None, timeout=DEFAULT_TIMEOUT):
        """Helper function to send HTTP requests with consistent parameters."""
        return helper.send_http_request(url, "GET", parameters=params, payload=None,
                                       headers=headers, cookies=None, verify=True, cert=None,
                                       use_proxy=proxy_config, timeout=timeout)

    def write_event(entry, now):
        """Helper function to create and write an event."""
        event_data = {
            "node_id": entry["node_id"],
            "ip_address": entry["ip_address"],
            "total_count": entry["count"],
            "total_per_incident_count": entry["incident_counts"],
            "collected_at": time.strftime('%Y-%m-%d %H:%M:%S (UTC)', time.gmtime(now)),
            "alerted_since_last_poll": True,
            # duplicate events are unlikely, but possible if the polling interval is long, this can be used in Splunk search to deduplicate
            "dedupe_key": f"{entry['node_id']}:{entry['ip_address']}:{entry['count']}" 
        }
        event = helper.new_event(json.dumps(event_data), time=now, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)

    # Get previous checkpoint data
    stanza_name = str(helper.get_input_stanza_names())
    last_updated_id = helper.get_check_point(f"{stanza_name}_update_id") or 0
    last_most_recent_updates = helper.get_check_point(f"{stanza_name}_most_recent_updates") or {}

    now = time.time()

    headers = {"User-Agent": f"Splunk API Call TA-Canary ({ta_version}) Splunk ({splunk_version}) ",
               "X-Canary-Auth-Token": api_key}
    url = f"https://{domain_hash}/api/v1/incidents/outside_bird/search"

    # Get update ID from newest record
    try:
        response = send_request(url, {"limit": 1})
        r_json = response.json()
        entry = r_json["src_ips"][0] if r_json.get("src_ips") else None
    except:
        helper.log_error("TA-thinkst-canary: Error fetching initial data")
        return

    if not entry:
        helper.log_info("TA-thinkst-canary: There are no outside bird alerts to fetch.")
        return
    next_update_id = get_update_id_from_cursor(r_json["cursor"]["next"]) if r_json["cursor"]["next"] else 0
    latest_update_key = f"{entry['node_id']}:{entry['ip_address']}"
    latest_update_count = entry["count"]

    if last_most_recent_updates and list(last_most_recent_updates.keys())[0] == latest_update_key and last_most_recent_updates[latest_update_key] == latest_update_count:
        helper.log_info("TA-thinkst-canary: No new outside bird alerts since last checkpoint.")
        return

    # Get first page
    response = send_request(url, {"limit": PAGE_LIMIT})
    r_json = response.json()
    next_link = r_json["cursor"]["next_link"]
    current_min_update_id = get_update_id_from_cursor(r_json["cursor"]["next"]) if r_json["cursor"]["next"] else 0
    
    # It's possible that the first page already contains new updates since we fetched the newest record above,
    # which means there could be duplicate events in the next poll (dependant on where the events fall in the pagination)
    # but these can be handled by the dedupe_key field in the event
    next_most_recent_updates = {f"{entry['node_id']}:{entry['ip_address']}": entry["count"] for entry in r_json["src_ips"]}

    while response.status_code == 200:
        # In the scenario that all of the IPs from the previous poll saved in last_most_recent_updates
        # have been changed, the allowed_change_count is used to make sure we don't write more events that are possibly new
        # (This is an unlikely scenario, but possible if the polling interval is long, e.g. more than 24 hours)
        allowed_change_count = last_updated_id - current_min_update_id
        for entry in r_json["src_ips"]:
            if last_updated_id != 0 and current_min_update_id <= last_updated_id: 
                next_link = None
                min_changes_since_last = get_change_count(last_most_recent_updates, entry)
                allowed_change_count -= min_changes_since_last
                if min_changes_since_last == 0 or allowed_change_count <= 0:
                    break
            write_event(entry, now)
            
        if not next_link:
            break
        response = send_request(next_link)
        r_json = response.json()
        next_link = r_json["cursor"]["next_link"]
        current_min_update_id = get_update_id_from_cursor(r_json["cursor"]["next"]) if r_json["cursor"]["next"] else 0
    
    # save checkpoint
    helper.save_check_point(f"{stanza_name}_update_id", next_update_id)
    helper.save_check_point(f"{stanza_name}_most_recent_updates", next_most_recent_updates)

    helper.log_info("TA-thinkst-canary: = = End Log  = =")

