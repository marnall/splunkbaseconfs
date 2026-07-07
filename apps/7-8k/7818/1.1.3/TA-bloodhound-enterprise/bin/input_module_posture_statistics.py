"""
Module for Posture Statistics input for BloodHound Enterprise.
"""
import json
from rest_client import (
    get_available_domains,
    get_posture_stats,
    get_posture_history,
    log_error,
    save_state,
    load_state,
    log_info,
)
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# --- Global Configurations ---
_APP_NAME = "TA-bloodhound-enterprise"
LOG_LOCATION = make_splunkhome_path(["var", "log", "splunk", _APP_NAME])

# --- Global Constants ---
DATA_TYPES = ["findings", "exposure", "assets", "attack-paths"]


def validate_input(helper, definition):
    """Validation function as required by the Splunk add-on framework."""
    pass


def initialize_domain_state(existing_state, domain_id):
    """Ensure domain exists in state and initialize if not."""
    if domain_id not in existing_state:
        existing_state[domain_id] = {data_type: None for data_type in DATA_TYPES}
    return existing_state


def update_domain_timestamp(domain_state, domain_id, data_type, timestamp):
    """Update the latest timestamp for a domain/data_type."""
    current_timestamp = domain_state[domain_id][data_type]
    if timestamp and (current_timestamp is None or timestamp > current_timestamp):
        domain_state[domain_id][data_type] = timestamp
    return domain_state


def create_event(helper, ew, posture_item, domain_info, domain_name_source,
                 data_type, sourcetype):
    """Prepare and write a single posture event to Splunk."""
    date_value = posture_item.pop("date", None)
    posture_item["metric_date"] = date_value if date_value is not None else "null"
    posture_item["domain_name"] = domain_info.get("name", "null")
    posture_item["impact_value"] = domain_info.get("impactValue", "null")
    posture_item["domain_type"] = domain_info.get("type", "null")
    posture_item["source_domain"] = domain_name_source
    posture_item["data_type"] = data_type

    event_data = json.dumps(posture_item)
    event = helper.new_event(
        event_data,
        time=None,
        host=None,
        index=helper.get_output_index(),
        source=None,
        sourcetype=sourcetype,
        done=True,
        unbroken=True,
    )
    ew.write_event(event)
    return date_value


def fetch_and_process_domain_data(helper, ew, domain_info, domain_name_source,
                                  last_timestamps, new_timestamps, sourcetype):
    """Fetch posture history for a single domain for all data types."""
    domain_id = domain_info.get("id")
    initialize_domain_state(new_timestamps, domain_id)

    for data_type in DATA_TYPES:
        last_timestamp = last_timestamps.get(domain_id, {}).get(data_type, "")
        helper.log_info(
            f"Fetching posture history for domain '{domain_id}' "
            f"data type '{data_type}' after '{last_timestamp}'"
        )

        posture_items = get_posture_history(
            helper, ew, data_type, domain_id, last_timestamp or ""
        )

        if posture_items is None:  
            helper.log_error("[ERROR] Unauthorized access. Stopping posture history collection.")
            return
        
        if not posture_items:
            helper.log_info(
                f"No posture history for domain '{domain_id}', type '{data_type}'"
            )
            continue

        helper.log_info(
            f"Retrieved {len(posture_items)} items for domain '{domain_id}', "
            f"type '{data_type}'"
        )

        for posture_item in posture_items:
            item_timestamp = create_event(
                helper,
                ew,
                posture_item,
                domain_info,
                domain_name_source,
                data_type,
                sourcetype,
            )
            update_domain_timestamp(new_timestamps, domain_id, data_type, item_timestamp)


def process_posture_history(helper, ew, source_domain_name, available_domains,
                            state_file_name):
    """Main posture history processing function, per domain and data type."""
    helper.log_info(f"Processing {len(available_domains)} domains for posture history")
    sourcetype = "BHE:Posture_history"

    previous_state = load_state(
        LOG_LOCATION, state_file_name, "posture_history_data_input"
    ) or {}
    last_timestamps = previous_state.get("last_posture_history_timestamp", {})

    new_timestamps = {**last_timestamps}

    for domain_info in available_domains:
        fetch_and_process_domain_data(
            helper, ew, domain_info, source_domain_name,
            last_timestamps, new_timestamps, sourcetype
        )

    log_info(
        helper,
        ew,
        "process_posture_history",
        "Updated timestamps",
        data=new_timestamps,
        sourcetype=sourcetype,
    )

    save_state(
        {"last_posture_history_timestamp": new_timestamps},
        LOG_LOCATION,
        state_file_name,
        "posture_history_data_input",
    )

    helper.log_info("Finished processing all posture history")


def collect_events(helper, ew):
    """
    Main event collection function for Posture Statistics.
    Only function with try/except for error handling.
    """
    try:
        helper.log_info("Starting collect_events function")

        source_domain_name = helper.get_arg("bloodhound_account").get("domain_name")
        input_name = helper.get_arg("name")
        index_name = helper.get_arg("index")
        state_file_name = f"{input_name}-{index_name}"

        domains_response = get_available_domains(helper, ew)
        if not domains_response or domains_response == "UNAUTHORIZED":
            helper.log_error("[ERROR] Failed to fetch available domains or unauthorized. Stopping execution.")
            return
        # Handle case where data might be None
        available_domains = domains_response.get("data") or []

        process_posture_history(
            helper, ew, source_domain_name, available_domains, state_file_name
        )

    except Exception as exc:
        log_error(helper, ew, "posture_history_collect_events", exc)

