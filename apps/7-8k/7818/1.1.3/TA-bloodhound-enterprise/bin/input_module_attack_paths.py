"""
Module for BloodHound Enterprise Attack Paths Input.
"""
import json
import time

from rest_client import (
    get_attack_path_timeline,
    get_attack_path_details,
    get_available_domains,
    get_path_titles,
    get_available_types,
    get_finding_trends,
    log_error,
    save_state,
    load_state,
    log_info,
)
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# --- Global Configurations ---
_APP_NAME = "TA-bloodhound-enterprise"
LOG_LOCATION = make_splunkhome_path(["var", "log", "splunk", _APP_NAME])

TIME_PERIOD_MAP = {
    365: "1 year",
    180: "6 months",
    90: "3 months",
    30: "1 month",
    7: "1 week",
}


# --- Helper Functions ---
def validate_input(helper, definition):
    """Validation function as required by Splunk add-on framework."""
    pass


def get_severity(exposure_percentage: int) -> str:
    """Determine severity based on exposure percentage."""
    if exposure_percentage > 95:
        return "Critical"
    if exposure_percentage > 80:
        return "High"
    if exposure_percentage > 40:
        return "Moderate"
    return "Low"


def convert_days_to_rfc(helper, days: int) -> str:
    """Convert number of past days into RFC timestamp."""
    try:
        helper.log_info(f"[INFO] Converting {days} days to RFC timestamp")
        timestamp = int(time.time() - days * 24 * 3600)
        rfc_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
        helper.log_debug(f"[DEBUG] Converted timestamp: {rfc_time}")
        return rfc_time
    except Exception as exc:
        log_error(helper, None, "convert_days_to_rfc", exc)


def update_domain_latest_timestamp(domain_latest_timestamps, domain_id, new_timestamp):
    """Update latest timestamp for a domain."""
    if new_timestamp and (
        domain_latest_timestamps.get(domain_id) is None
        or new_timestamp > domain_latest_timestamps.get(domain_id)
    ):
        domain_latest_timestamps[domain_id] = new_timestamp
        
def get_domain_name(domain_id, available_domains):
    """
    Return the domain name for a given domain_id.
    If not found, returns 'Unknown'.
    """
    # Handle case where data might be None
    domains = available_domains.get("data") or []
    return next(
        (domain["name"] for domain in domains
         if isinstance(domain, dict) and domain.get("id") == domain_id),
        "Unknown"
    )



# --- Attack Path Processing ---
def process_single_attack_path(
    helper, ew, domain_name, source_domain, path_title_map, path_item
):
    """Process a single attack path item and write event."""
    path_item["path_title"] = path_title_map.get(path_item["Finding"], "Unknown")
    path_item["domain_name"] = domain_name
    path_item["source_domain"] = source_domain
    path_item["remediation"] = (
        f"{source_domain}/ui/remediation?findingType={path_item['Finding']}"
    )
    try:
        event = helper.new_event(
            json.dumps(path_item),
            sourcetype="BHE:attack_paths",
            done=True,
            unbroken=True,
        )
        ew.write_event(event)
    except Exception as exc:
        log_error(helper, ew, "process_single_attack_path", exc)


def process_finding_type_attack_paths(
    helper,
    ew,
    domain_id,
    finding_type,
    domain_name,
    source_domain_name,
    path_title_map,
    last_timestamp,
    domain_latest_timestamps,
):
    """Process all attack paths for a specific finding type."""
    attack_paths = get_attack_path_details(helper, ew, domain_id, finding_type)
    if attack_paths is None: 
        return
    if not attack_paths: 
        return
    for path_item in attack_paths:
        item_timestamp = path_item.get("updated_at")
        if item_timestamp and (
            last_timestamp is None or item_timestamp > last_timestamp
        ):
            process_single_attack_path(
                helper,
                ew,
                domain_name,
                source_domain_name,
                path_title_map,
                path_item,
            )
        update_domain_latest_timestamp(
            domain_latest_timestamps, domain_id, item_timestamp
        )


def process_domain_attack_paths(
    helper,
    ew,
    domain_id,
    finding_types,
    domain_name,
    source_domain_name,
    path_title_map,
    last_timestamp,
    domain_latest_timestamps,
):
    """Process all finding types for a single domain."""
    for finding_type in finding_types:
        process_finding_type_attack_paths(
            helper,
            ew,
            domain_id,
            finding_type,
            domain_name,
            source_domain_name,
            path_title_map,
            last_timestamp,
            domain_latest_timestamps,
        )


def process_all_attack_paths(
    helper,
    ew,
    domain_types_map,
    path_title_map,
    available_domains,
    state_file,
):
    """Process all attack paths for all domains."""
    helper.log_info("Fetching new attack path details.")
    last_timestamps = (
        load_state(LOG_LOCATION, state_file, "attack_path_data_input") or {}
    )
    domain_latest_timestamps = last_timestamps.copy()
    source_domain_name = helper.get_arg("bloodhound_account").get("domain_name")

    for domain_id, finding_types in domain_types_map.items():
        domain_name = get_domain_name(domain_id, available_domains)
        last_timestamp = last_timestamps.get(domain_id)
        helper.log_info(
            f"Processing domain '{domain_name}' (ID: {domain_id}) for attack "
            f"paths. Last timestamp: {last_timestamp}"
        )
        process_domain_attack_paths(
            helper,
            ew,
            domain_id,
            finding_types,
            domain_name,
            source_domain_name,
            path_title_map,
            last_timestamp,
            domain_latest_timestamps,
        )

    save_state(
        domain_latest_timestamps, LOG_LOCATION, state_file, "attack_path_data_input"
    )
    helper.log_info("Attack path processing completed.")


# --- Timeline Processing ---
def process_single_timeline_item(
    helper,
    ew,
    domain_name,
    source_domain,
    path_title_map,
    timeline_item,
    finding_type,
):
    """Process a single timeline item."""
    timeline_item["path_title"] = path_title_map.get(finding_type, "Unknown")
    timeline_item["domain_name"] = domain_name
    timeline_item["severity"] = get_severity(int(timeline_item.get("CompositeRisk", 0)))
    timeline_item["source_domain"] = source_domain
    try:
        event = helper.new_event(
            json.dumps(timeline_item),
            index=helper.get_output_index(),
            sourcetype="BHE:path_timeline",
            done=True,
            unbroken=True,
        )
        ew.write_event(event)
    except Exception as exc:
        log_error(helper, ew, "process_single_timeline_item", exc)


def process_finding_type_timeline(
    helper,
    ew,
    domain_id,
    finding_type,
    domain_name,
    source_domain_name,
    path_title_map,
    last_timestamp,
    domain_latest_timestamps,
):
    """Process all timeline items for a specific finding type."""
    timelines = get_attack_path_timeline(
        helper, ew, domain_id, finding_type, last_timestamp or ""
    )
    if timelines is None:  
        return
    if not timelines:  
        return
    for timeline_item in timelines:
        process_single_timeline_item(
            helper,
            ew,
            domain_name,
            source_domain_name,
            path_title_map,
            timeline_item,
            finding_type,
        )
        update_domain_latest_timestamp(
            domain_latest_timestamps, domain_id, timeline_item.get("updated_at")
        )


def process_domain_timelines(
    helper,
    ew,
    domain_id,
    finding_types,
    domain_name,
    source_domain_name,
    path_title_map,
    last_timestamp,
    domain_latest_timestamps,
):
    """Process all finding types for a single domain timeline."""
    for finding_type in finding_types:
        process_finding_type_timeline(
            helper,
            ew,
            domain_id,
            finding_type,
            domain_name,
            source_domain_name,
            path_title_map,
            last_timestamp,
            domain_latest_timestamps,
        )


def process_all_timelines(
    helper,
    ew,
    domain_types_map,
    path_title_map,
    available_domains,
    state_file,
):
    """Process all path timelines for all domains."""
    helper.log_info("Fetching attack path timeline data.")
    last_timestamps = (
        load_state(LOG_LOCATION, state_file, "path_timeline_data_input") or {}
    )
    domain_latest_timestamps = last_timestamps.copy()
    source_domain_name = helper.get_arg("bloodhound_account").get("domain_name")

    for domain_id, finding_types in domain_types_map.items():
        domain_name = get_domain_name(domain_id, available_domains)
        last_timestamp = last_timestamps.get(domain_id)
        helper.log_info(
            f"Processing domain '{domain_name}' (ID: {domain_id}) for timeline. "
            f"Last timestamp: {last_timestamp}"
        )
        process_domain_timelines(
            helper,
            ew,
            domain_id,
            finding_types,
            domain_name,
            source_domain_name,
            path_title_map,
            last_timestamp,
            domain_latest_timestamps,
        )

    save_state(
        domain_latest_timestamps, LOG_LOCATION, state_file, "path_timeline_data_input"
    )
    helper.log_info("Path timeline processing completed.")


# --- Finding Trends Processing ---
def process_single_finding(
    helper,
    ew,
    finding_item,
    period,
    domain_name,
    source_domain,
    start_date,
    end_date,
):
    """Process single finding trend item."""
    finding_item["domain_name"] = domain_name
    finding_item["source_domain"] = source_domain
    finding_item["period"] = period
    finding_item["start_date"] = start_date
    finding_item["end_date"] = end_date
    try:
        event = helper.new_event(
            json.dumps(finding_item),
            sourcetype="BHE:finding_trends",
            done=True,
            unbroken=True,
        )
        ew.write_event(event)
    except Exception as exc:
        log_error(helper, ew, "process_single_finding", exc)


def process_timeframe_for_domain(
    helper,
    ew,
    domain_id,
    days,
    domain_name,
    source_domain,
):
    """Process a single timeframe for a domain."""
    start_date_rfc = convert_days_to_rfc(helper, days)
    period_label = TIME_PERIOD_MAP.get(days, f"{days} days")
    trends_response = get_finding_trends(helper, ew, domain_id, start_date_rfc)
    if trends_response is None:  
        return
    if not trends_response:  
        return
    # Handle case where data might be None or missing, and findings might be None
    data = trends_response.get("data") or {}
    findings = data.get("findings") or []
    start_date_api = trends_response.get("start", "null")
    end_date_api = trends_response.get("end", "null")

    for finding_item in findings:
        process_single_finding(
            helper,
            ew,
            finding_item,
            period_label,
            domain_name,
            source_domain,
            start_date_api,
            end_date_api,
        )


def process_domain_finding_trends(
    helper,
    ew,
    domain_id,
    domain_name,
    source_domain,
):
    """Process all timeframes for a single domain."""
    time_frames = [365, 180, 90, 30, 7]
    for days in time_frames:
        process_timeframe_for_domain(
            helper, ew, domain_id, days, domain_name, source_domain
        )


def process_all_finding_trends(helper, ew, domain_ids, available_domains):
    """Process all domains for finding trends."""
    source_domain_name = helper.get_arg("bloodhound_account").get("domain_name")
    for domain_id in domain_ids:
        domain_name = get_domain_name(domain_id, available_domains)
        process_domain_finding_trends(
            helper, ew, domain_id, domain_name, source_domain_name
        )


# --- Main Event Collector ---
def collect_events(helper, ew):
    """Primary entry point to fetch and ingest all BloodHound data."""
    try:
        source_input = helper.get_arg("name")
        index_name = helper.get_arg("index")
        state_file_name = f"{source_input}-{index_name}"

        available_domains_response = get_available_domains(helper, ew)
        if not available_domains_response or available_domains_response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Failed to fetch available domains or unauthorized. Stopping execution.")
            return
        
        # Handle case where data might be None
        domains = available_domains_response.get("data") or []
        domain_ids_to_collect = [
            domain["id"]
            for domain in domains
            if domain.get("collected") is True
        ]
        domain_types_map = get_available_types(helper, ew, domain_ids_to_collect)
        if not domain_types_map or domain_types_map == "UNAUTHORIZED":
            helper.log_error("[ERROR] Failed to fetch available types or unauthorized. Stopping execution.")
            return
        
        path_title_map = get_path_titles(helper, ew, domain_types_map)
        if not path_title_map or path_title_map == "UNAUTHORIZED":
            helper.log_error("[ERROR] Failed to fetch path titles or unauthorized. Stopping execution.")
            return

        process_all_attack_paths(
            helper,
            ew,
            domain_types_map,
            path_title_map,
            available_domains_response,
            state_file_name,
        )
        process_all_timelines(
            helper,
            ew,
            domain_types_map,
            path_title_map,
            available_domains_response,
            state_file_name,
        )
        process_all_finding_trends(
            helper, ew, domain_ids_to_collect, available_domains_response
        )

        helper.log_info("Successfully ingested all BloodHound data.")
    except Exception as exc:
        log_error(helper, ew, "attack_collect_events", exc)

