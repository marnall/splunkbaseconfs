"""
Splunk Add-on - SOCRadar Incidents v4 collector
Production-ready script for Splunk Modular Input with API pagination,
rate limit handling, hardcoded severity prioritization, and a per-run total new incident cap.

Version: 1.9.26
Changes:
  - Timestamp-based checkpoint for optimized API queries
  - First run: uses how_many_days (initial backfill)
  - Subsequent runs: uses last_incident_timestamp - 1 hour buffer
  - Added include_total_records for proper pagination tracking
  - Fixed date parsing for ISO 8601 format
  - Keeps alarm_id->status tracking for status change detection
"""

import json
import time
import requests
from datetime import datetime, timedelta, timezone
from collections import OrderedDict

# Splunk Add-on SDK objects (helper, ew) are injected by Splunk when the script runs.

SOCRADAR_API_BASE_URL = "https://platform.socradar.com/api"
API_TIMEOUT_SECONDS = 30
DEFAULT_MAX_NEW_INCIDENTS_PER_RUN = 500

# Hardcoded severity order - critical alarms fetched first
SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

def validate_input(helper, definition):
    """
    Validation for modular input configurations
    """
    pass

def collect_events(helper, ew):
    helper.log_info("SCRIPT_START: SOCRadar Incidents v4 collection run.")

    # --- Stage 1: Get Configuration ---
    # Get proxy settings
    proxy_settings = helper.get_proxy()
    proxies = None

    # Build proxy configuration if enabled
    if proxy_settings:
        proxy_url = proxy_settings.get('proxy_url')
        proxy_port = proxy_settings.get('proxy_port')
        proxy_username = proxy_settings.get('proxy_username')
        proxy_password = proxy_settings.get('proxy_password')

        if proxy_url and proxy_port:
            # Build proxy URL with authentication if provided
            if proxy_username and proxy_password:
                proxy = f"http://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}"
            else:
                proxy = f"http://{proxy_url}:{proxy_port}"

            proxies = {
                'http': proxy,
                'https': proxy
            }
            helper.log_info(f"Proxy configured: {proxy_url}:{proxy_port}")

    # Get credentials from INPUT parameters (not global settings)
    company_id = helper.get_arg("socradar_company_id")
    api_key = helper.get_arg("socradar_api_key")

    # Log what we retrieved (be careful with full API key)
    helper.log_info(f"Retrieved company_id: {company_id}")

    # Check if they might be swapped (company ID is usually shorter)
    if company_id and api_key:
        if len(company_id) > 20 and len(api_key) < 20:
            helper.log_warning("WARNING: API key and company ID might be swapped! Company ID is usually shorter.")
            # Swap them
            helper.log_info("Swapping credentials...")
            company_id, api_key = api_key, company_id
            helper.log_info(f"After swap - company_id: {company_id}")

    if not company_id or not api_key:
        helper.log_error("Missing credentials. Please configure socradar_company_id and socradar_api_key in the input configuration.")
        return

    # Get how many days from GLOBAL settings (add-on level)
    how_many_days_str = helper.get_global_setting("how_many_days")
    if how_many_days_str:
        try:
            how_many_days = max(1, int(how_many_days_str))
        except:
            how_many_days = 1
    else:
        how_many_days = 1

    helper.log_info(f"Configuration: Looking back {how_many_days} days")

    # Get max incidents per run from global settings
    try:
        max_new_incidents_per_run = int(helper.get_global_setting("total_limit") or DEFAULT_MAX_NEW_INCIDENTS_PER_RUN)
    except:
        max_new_incidents_per_run = DEFAULT_MAX_NEW_INCIDENTS_PER_RUN

    # Get Splunk settings
    input_stanza_name = helper.get_input_stanza_names()
    output_index = helper.get_output_index()
    sourcetype = helper.get_sourcetype()
    input_type = helper.get_input_type()

    # Log the actual input stanza name for debugging
    helper.log_info(f"Input stanza name from helper: {input_stanza_name}")

    # --- Stage 2: Calculate End Time (start time determined per-severity based on checkpoint) ---
    current_time = datetime.now(timezone.utc)
    end_timestamp = int(current_time.timestamp())

    helper.log_info(f"Collection end time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # --- Stage 3: Build API URL ---
    api_url = f"{SOCRADAR_API_BASE_URL}/company/{company_id}/incidents/v4"
    helper.log_info(f"API URL: {api_url}")

    # Track total incidents across all severities
    total_new_incidents = 0
    total_indexed = 0

    # --- Stage 4: Process Each Severity Level (CRITICAL first, then HIGH, etc.) ---
    helper.log_info(f"Severity prioritization enabled: {' -> '.join(SEVERITY_ORDER)}")

    for current_severity in SEVERITY_ORDER:
        helper.log_info(f"=== Fetching {current_severity} severity alarms ===")

        # Check if we've hit the per-run limit
        if total_new_incidents >= max_new_incidents_per_run:
            helper.log_info(f"Reached max incidents per run ({max_new_incidents_per_run}), skipping remaining severities")
            break

        # --- Load Checkpoint for this severity ---
        checkpoint_key = f"{input_stanza_name}_socradar_v4_{current_severity.lower()}_processed_alarms"

        processed_alarms = {}  # Dict to store alarm_id -> status
        indexed_version = "1.9.26"  # Default to current version for new checkpoints
        last_incident_ts = None  # Timestamp of last incident (for optimized time window)

        try:
            checkpoint_data_raw = helper.get_check_point(checkpoint_key)
            if checkpoint_data_raw:
                checkpoint_data = json.loads(checkpoint_data_raw)
                # Support both old format (list) and new format (dict)
                if isinstance(checkpoint_data.get("alarm_ids"), list):
                    # Old format - convert to dict with string keys
                    for alarm_id in checkpoint_data.get("alarm_ids", []):
                        processed_alarms[str(alarm_id)] = None
                    indexed_version = "1.0.0"  # Old format = pre-v1.9.20
                else:
                    # New format - dict with status, ensure all keys are strings
                    temp_alarms = checkpoint_data.get("alarm_status", {})
                    processed_alarms = {str(k): v for k, v in temp_alarms.items()}
                    # Get indexed version from checkpoint (default to 1.0.0 if not present)
                    indexed_version = checkpoint_data.get("indexed_version", "1.0.0")
                    # Get last incident timestamp (new in v1.9.26)
                    last_incident_ts = checkpoint_data.get("last_incident_timestamp")
                helper.log_info(f"[{current_severity}] Loaded checkpoint with {len(processed_alarms)} processed alarms (indexed_version: {indexed_version}, last_ts: {last_incident_ts})")
        except:
            helper.log_info(f"[{current_severity}] No checkpoint found, starting fresh")

        # --- Calculate Time Window based on checkpoint ---
        if last_incident_ts:
            # Subsequent runs: use checkpoint timestamp - 1 hour buffer
            start_timestamp = int(last_incident_ts) - 3600
            start_time_str = datetime.fromtimestamp(start_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            end_time_str = datetime.fromtimestamp(end_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            helper.log_info(f"[{current_severity}] Using checkpoint-based window: {start_time_str} to {end_time_str} (1h buffer)")
        else:
            # First run: use how_many_days for initial backfill
            start_timestamp = end_timestamp - (how_many_days * 86400)
            start_time_str = datetime.fromtimestamp(start_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            end_time_str = datetime.fromtimestamp(end_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            helper.log_info(f"[{current_severity}] First run, looking back {how_many_days} days: {start_time_str} to {end_time_str}")

        # Track max incident timestamp for this severity
        max_incident_timestamp = last_incident_ts if last_incident_ts else 0

        # --- Fetch Incidents for this severity ---
        all_incidents = []
        page = 1
        consecutive_rate_limits = 0
        new_incidents_count = 0
        duplicate_count = 0

        # Fetch all pages until API returns no more data
        while True:
            # API parameters
            params = {
                "key": api_key,
                "limit": 100,
                "page": page,
                "start_date": start_timestamp,
                "end_date": end_timestamp,
                "severities": current_severity,  # Hardcoded severity filter
                "include_total_records": "true"  # Enable pagination info
            }

            helper.log_info(f"[{current_severity}] Making request to page {page}")
            helper.log_debug(f"Request params: {params}")

            try:
                response = requests.get(api_url, params=params, timeout=API_TIMEOUT_SECONDS, proxies=proxies)

                helper.log_info(f"[{current_severity}] Response status code: {response.status_code}")

                # Check for rate limit
                if response.status_code == 429 or "rate limit exceeded" in response.text.lower():
                    consecutive_rate_limits += 1

                    if consecutive_rate_limits == 1:
                        wait_time = 30
                    else:
                        wait_time = 60

                    helper.log_warning(f"[{current_severity}] Rate limit hit! Waiting {wait_time} seconds... (attempt {consecutive_rate_limits})")
                    time.sleep(wait_time)
                    continue  # Retry same page

                # Reset rate limit counter on success
                consecutive_rate_limits = 0

                # Check for authentication error
                if response.status_code == 401:
                    helper.log_error(f"API error: HTTP 401 Unauthorized. Please check your API credentials.")
                    helper.log_error(f"Response: {response.text}")
                    break

                # Check for other errors
                if response.status_code != 200:
                    helper.log_error(f"[{current_severity}] API error: HTTP {response.status_code}")
                    helper.log_error(f"Response: {response.text}")
                    break

                # Parse response
                data = response.json()
                response_data = data.get("data", {})

                # Handle both old format (data is array) and new format (data.alarms)
                if isinstance(response_data, list):
                    incidents = response_data
                    total_records = len(incidents)
                    total_pages = 1
                else:
                    incidents = response_data.get("alarms", [])
                    total_records = response_data.get("total_records", 0)
                    total_pages = response_data.get("total_pages", 0)

                # Log pagination info on first page
                if page == 1 and total_records:
                    helper.log_info(f"[{current_severity}] Total records: {total_records}, Total pages: {total_pages}")

                if not incidents:
                    helper.log_info(f"[{current_severity}] No more incidents at page {page}")
                    break

                # Process incidents on this page
                for incident in incidents:
                    # Truncate long text fields to 5000 characters
                    if 'alarm_text' in incident and incident['alarm_text'] and len(str(incident['alarm_text'])) > 5000:
                        incident['alarm_text'] = str(incident['alarm_text'])[:5000] + '...'
                    if 'alarm_response' in incident and incident['alarm_response'] and len(str(incident['alarm_response'])) > 5000:
                        incident['alarm_response'] = str(incident['alarm_response'])[:5000] + '...'
                    if 'alarm_type_details' in incident and isinstance(incident['alarm_type_details'], dict):
                        if 'alarm_default_mitigation_plan' in incident['alarm_type_details'] and incident['alarm_type_details']['alarm_default_mitigation_plan']:
                            if len(str(incident['alarm_type_details']['alarm_default_mitigation_plan'])) > 5000:
                                incident['alarm_type_details']['alarm_default_mitigation_plan'] = str(incident['alarm_type_details']['alarm_default_mitigation_plan'])[:5000] + '...'
                        # Extract alarm main type and sub type
                        incident['alarm_main_type'] = incident['alarm_type_details'].get('alarm_main_type', 'N/A')
                        incident['alarm_sub_type'] = incident['alarm_type_details'].get('alarm_sub_type', 'N/A')
                    else:
                        incident['alarm_main_type'] = 'N/A'
                        incident['alarm_sub_type'] = 'N/A'

                    alarm_id = incident.get("alarm_id")

                    # Generate alarm link
                    if alarm_id and company_id:
                        incident['alarm_link'] = f"https://platform.socradar.com/app/company/{company_id}/alarm-management?tab=approved&alarmId={alarm_id}"
                    else:
                        incident['alarm_link'] = 'N/A'
                    current_status = incident.get("status", "N/A")

                    # Check if already processed and if status changed
                    if alarm_id:
                        alarm_id_str = str(alarm_id)
                        if alarm_id_str in processed_alarms:
                            old_status = processed_alarms.get(alarm_id_str)

                            # Force re-index if indexed with version < 1.9.20 (TRUNCATE fix)
                            if indexed_version < "1.9.20":
                                helper.log_info(f"[{current_severity}] Force re-indexing alarm {alarm_id} (indexed with v{indexed_version})")
                                incident['reindexed'] = True
                                incident['reindex_reason'] = f"Upgraded from v{indexed_version} (TRUNCATE fix)"
                                incident['previous_status'] = old_status
                            elif old_status == current_status:
                                # Status unchanged - skip
                                duplicate_count += 1
                                continue
                            else:
                                # Status changed - index the update
                                helper.log_info(f"[{current_severity}] Status changed for {alarm_id}: {old_status} -> {current_status}")
                                incident['status_changed'] = True
                                incident['previous_status'] = old_status

                    # New incident or status update
                    all_incidents.append(incident)
                    new_incidents_count += 1

                    # Stop if we hit the per-run limit
                    if (total_new_incidents + new_incidents_count) >= max_new_incidents_per_run:
                        helper.log_info(f"[{current_severity}] Reached max incidents per run ({max_new_incidents_per_run})")
                        break

                helper.log_info(f"[{current_severity}] Page {page}: Got {len(incidents)} incidents ({new_incidents_count} new/updated, {duplicate_count} unchanged)")

                # Stop if we hit the limit
                if (total_new_incidents + new_incidents_count) >= max_new_incidents_per_run:
                    break

                # Check if this was the last page
                if len(incidents) < 100:
                    helper.log_info(f"[{current_severity}] Reached last page")
                    break

                page += 1
                time.sleep(3)  # Wait 3 seconds between requests

            except Exception as e:
                helper.log_error(f"[{current_severity}] Error on page {page}: {str(e)}")
                break

        helper.log_info(f"[{current_severity}] Fetching complete. Found {new_incidents_count} new/updated, skipped {duplicate_count} unchanged")

        # --- Index Incidents to Splunk ---
        indexed_count = 0
        indexed_alarms = {}
        batch_size = 15

        for batch_start in range(0, len(all_incidents), batch_size):
            batch_end = min(batch_start + batch_size, len(all_incidents))
            batch = all_incidents[batch_start:batch_end]

            for incident in batch:
                alarm_id = incident.get("alarm_id")

                try:
                    event_time = None
                    date_str = incident.get("date")
                    if date_str:
                        try:
                            # Try ISO 8601 format first (API may return this)
                            if "T" in date_str:
                                # Handle ISO 8601: 2025-12-05T01:27:44.345Z
                                event_datetime = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            else:
                                # Fallback to old format: 2025-12-05 01:27:44
                                event_datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            event_time = event_datetime.timestamp()

                            # Track max incident timestamp for checkpoint
                            if event_time and event_time > max_incident_timestamp:
                                max_incident_timestamp = event_time
                        except Exception as date_err:
                            helper.log_warning(f"[{current_severity}] Failed to parse date '{date_str}': {date_err}")

                    # Create optimized event with critical fields first
                    optimized_incident = OrderedDict()
                    optimized_incident['alarm_id'] = incident.get('alarm_id')
                    optimized_incident['status'] = incident.get('status')
                    optimized_incident['date'] = incident.get('date')
                    optimized_incident['alarm_risk_level'] = incident.get('alarm_risk_level')
                    optimized_incident['alarm_asset'] = incident.get('alarm_asset')
                    optimized_incident['alarm_main_type'] = incident.get('alarm_main_type')
                    optimized_incident['alarm_sub_type'] = incident.get('alarm_sub_type')
                    optimized_incident['alarm_link'] = incident.get('alarm_link')

                    for key, value in incident.items():
                        if key not in optimized_incident:
                            optimized_incident[key] = value

                    event = helper.new_event(
                        data=json.dumps(optimized_incident),
                        index=output_index,
                        source=input_type,
                        sourcetype=sourcetype,
                        time=event_time
                    )
                    ew.write_event(event)

                    indexed_count += 1
                    if alarm_id:
                        indexed_alarms[str(alarm_id)] = incident.get('status')

                except Exception as e:
                    helper.log_error(f"[{current_severity}] Failed to index incident {alarm_id}: {str(e)}")

        helper.log_info(f"[{current_severity}] Indexed {indexed_count} incidents to Splunk")

        # --- Update Checkpoint for this severity ---
        if indexed_alarms or max_incident_timestamp > 0:
            processed_alarms.update(indexed_alarms)

            checkpoint_data = {
                "alarm_status": processed_alarms,
                "indexed_version": "1.9.26",
                "severity": current_severity,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "last_incident_timestamp": max_incident_timestamp if max_incident_timestamp > 0 else None
            }

            try:
                helper.save_check_point(checkpoint_key, json.dumps(checkpoint_data))
                ts_str = datetime.fromtimestamp(max_incident_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if max_incident_timestamp > 0 else "N/A"
                helper.log_info(f"[{current_severity}] Checkpoint updated. Total tracked: {len(processed_alarms)}, last_ts: {ts_str}")
            except Exception as e:
                helper.log_error(f"[{current_severity}] Failed to save checkpoint: {str(e)}")

        # Update totals
        total_new_incidents += new_incidents_count
        total_indexed += indexed_count

        # Small delay between severity levels
        time.sleep(1)

    # --- Final Summary ---
    helper.log_info(f"=== SUMMARY ===")
    helper.log_info(f"Total new/updated incidents: {total_new_incidents}")
    helper.log_info(f"Total indexed to Splunk: {total_indexed}")
    helper.log_info("SCRIPT_END: SOCRadar Incidents v4 collection complete.")


from splunklib.modularinput import Scheme

def get_scheme():
    """Returns scheme parameters for this modular input."""
    scheme = Scheme("SOCRadar Incidents Collector v4")
    scheme.description = "Collects incidents from the SOCRadar v4 API."
    scheme.use_external_validation = True
    scheme.use_single_instance = False
    return scheme
