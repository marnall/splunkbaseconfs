
# encoding = utf-8

import os
import sys
import time
import datetime

import import_job
import date_utils

SCAN_CHECKPOINT_KEY = "{}-last_import_time"
ASSESSED_CHECKPOINT_KEY = "{}-last_assessed_time"
LAST_FULL_IMPORT_CHECKPOINT_KEY = "{}-last_full_import_time"

# The assets whose scan AND assessed dates are both NULL will not be returned using date filters. Including the NULL
# conditions on the initial filter will return all data up until the import starts.
INITIAL_FILTER = "last_scan_end <= {} || last_assessed_for_vulnerabilities <= {} || last_scan_end IS NULL && last_assessed_for_vulnerabilities IS NULL"

SCAN_FILTER = "last_scan_end > {} && last_scan_end <= {} && asset.agentKey IS NULL"
ASSESSED_FILTER = "last_assessed_for_vulnerabilities > {} && last_assessed_for_vulnerabilities <= {} && asset.agentKey IS NOT NULL"

LAST_SCAN_END_DATE = "last_scan_end_date"
LAST_ASSESSED_DATE = "last_assessed_date"
AGENT_SUCCESS = "agent_success"
SCAN_SUCCESS = "scan_success"
SUCCESS = "success"

def build_asset_filter_from_configuration(helper):
    payload = {}

    asset_filter = helper.get_arg("asset_filter")
    if asset_filter != "":
        payload["asset"] = asset_filter

    vulns_filter = helper.get_arg("vulnerability_filter")
    if vulns_filter != "":
        payload["vulnerability"] = vulns_filter
    
    return payload

def build_asset_filter_with_check_point(helper, filter_str, checkpoint_time, before_time):
    payload = build_asset_filter_from_configuration(helper)
    checkpoint_filter = filter_str.format(checkpoint_time, before_time)
    
    if payload.get("asset") is None or payload.get("asset") == "":
        payload["asset"] = checkpoint_filter
    else:
        payload["asset"] = "({}) && ({})".format(payload.get("asset"), checkpoint_filter)

    return payload

def build_before_now_filter(current_filter, before_time):
    payload = current_filter

    if payload is None:
        payload = {}

    before_filter_complete = INITIAL_FILTER.format(before_time, before_time)
    
    if payload.get("asset") is not None and payload.get("asset") != "":
        payload["asset"] = "({}) && ({})".format(payload.get("asset"), before_filter_complete)
    else:
       payload["asset"] = before_filter_complete

    return payload

def save_check_point(helper, state_key, value):
    # Attempt up to 3 times to update checkpoint. If not able to update in those three attempts we will fail the
    # import and reattempt the next time the input is run on schedule. This appears to be necessary due to
    # `ConnectionError` response when the Splunk server is overwhelmed, resulting in a `Connection aborted`. If this
    # persists in a customer environment, investigate the KV Store health and metrics/overuse of the Splunk system:
    # https://dev.splunk.com/enterprise/docs/developapps/manageknowledge/kvstore/debugslowoperations
    if value is not None and value != "":
        for attempt in range(1,4):
            try:
                helper.save_check_point(state_key, value)
                helper.log_info("Checkpoint {} for {} is set as {}".format(state_key, 
                    helper.get_input_stanza_names(), value))
            except ConnectionError:
                # Sleep before attempting again; will increase sleep by number of attempt for further backoff
                helper.log_info("Failed to update checkpoint state of KV store for {} key, "
                                "attempt {}".format(state_key, attempt))
                time.sleep(attempt * 5)
            else:
                break
        else:
            # Log error saying it failed due to inability to save KV state and may result in duplicate data
            helper.log_error("Failed all attempts to update KV store for {} key".format(state_key))
    else:
        helper.log_info("Last import time {} for {} has not been updated and remains at {}".format(state_key, 
            helper.get_input_stanza_names(), helper.get_check_point(state_key)))  

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # rapid7_region = definition.parameters.get('rapid7_region', None)
    # rapid7_api_key = definition.parameters.get('rapid7_api_key', None)
    # asset_filter = definition.parameters.get('asset_filter', None)
    # vulnerability_filter = definition.parameters.get('vulnerability_filter', None)
    pass

def collect_events(helper, ew):
    helper.log_info("Fetching asset data...")
    
    import_vulns = helper.get_arg("import_vulnerabilities")
    include_same_vulns = helper.get_arg("include_same_vulnerabilities")
    full_import_schedule = helper.get_arg("full_import_schedule")

    if not import_vulns and include_same_vulns:
        helper.log_warning("Include same vulnerabilities will have no effect without enabling Import vulnerabilities")

    now = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)  # Get current UTC time a minute ago
    current_time = now.strftime('%Y-%m-%dT%H:%M:%S') + now.strftime('.%f')[:4] + 'Z'  # Convert to proper format

    # Retrieve any previously saved checkpoints
    state_key, assessed_key, last_full_import_key = get_state_keys(helper)
    comparison_time, assessed_time, last_initial_import_date = get_checkpoint_values(helper)
    fallback_assessed_time = now - datetime.timedelta(hours=24)

    print_checkpoint(helper, state_key, comparison_time)
    print_checkpoint(helper, assessed_key, assessed_time)
    print_checkpoint(helper, last_full_import_key, last_initial_import_date)

    results_from_import_jobs = {}

    if is_force_full_import(helper, last_initial_import_date, full_import_schedule, now):
        comparison_time = None

    if not comparison_time:
        # INITIAL IMPORT
        # Create and start an import job configured to perform an initial import. This import job will use only the 
        # filtered configured as part of user configuration and will not include a checkpoint in the filter, meaning
        # that all data is included in the initial import.
        initial_import_job = import_job.AssetImportJob(helper, ew, endpoint="assets",
                                                                   is_initial_import=True, 
                                                                   is_save_last_scan=True, 
                                                                   is_save_last_assessed=True,
                                                                   is_import_vulns=import_vulns,
                                                                   is_include_same=True)

        initial_filter = build_before_now_filter(build_asset_filter_from_configuration(helper), current_time)        
        success = initial_import_job.start(initial_filter, current_time, None)

        results_from_import_jobs[LAST_ASSESSED_DATE] = initial_import_job.last_assessed_date
        results_from_import_jobs[LAST_SCAN_END_DATE] = initial_import_job.last_scan_end_date
        results_from_import_jobs[AGENT_SUCCESS] = success
        results_from_import_jobs[SCAN_SUCCESS] = success

        # Record the time of last successful full import
        if success is True:
            save_check_point(helper, last_full_import_key, current_time)

    else:
        # AGENT IMPORT
        # Create and start an import job configured to import data made available by Agent collections. In addition to
        # any configured filters this import job will use the ASSESSED_FILTER for results filtering.
        agent_import_job = import_job.AssetImportJob(helper, ew, endpoint="assets",
                                                                 is_initial_import=False, 
                                                                 is_save_last_scan=False, 
                                                                 is_save_last_assessed=True, 
                                                                 is_cache_imports=False, 
                                                                 is_import_vulns=import_vulns,
                                                                 is_include_same=include_same_vulns)
        
        # A fallback is required when upgrading, or after an initial import that has not been able to set a 
        # last_assessed_for_vulnerabilities from an Agent asset. This fallback ensures that the initial import does not
        # import all agent assets which would result in a large amount of duplicate data.
        agent_checkpoint = assessed_time
        if agent_checkpoint is None:
            agent_checkpoint = date_utils.datetime_to_string(fallback_assessed_time)    
        
        agent_payload = build_asset_filter_with_check_point(helper, ASSESSED_FILTER, agent_checkpoint, current_time)
        agent_success = agent_import_job.start(agent_payload, current_time, comparison_time=agent_checkpoint)

        # SCAN IMPORT
        # Create and start an import job configured to import data made available by Console scans. In addition to
        # any configured filters this import job will use the SCAN_FILTER for results filtering.
        scan_import_job = import_job.AssetImportJob(helper, ew, endpoint="assets",
                                                                is_save_last_scan=True, 
                                                                is_save_last_assessed=False, 
                                                                is_cache_imports=False,
                                                                is_initial_import=False, 
                                                                is_import_vulns=import_vulns,
                                                                is_include_same=include_same_vulns)

        scan_payload = build_asset_filter_with_check_point(helper, SCAN_FILTER, comparison_time, current_time)
        scan_success = scan_import_job.start(scan_payload, current_time, comparison_time)

        # merge result
        results_from_import_jobs[LAST_ASSESSED_DATE] = agent_import_job.last_assessed_date
        results_from_import_jobs[LAST_SCAN_END_DATE] = scan_import_job.last_scan_end_date
        results_from_import_jobs[AGENT_SUCCESS] = agent_success
        results_from_import_jobs[SCAN_SUCCESS] = scan_success

    # A success value means that all endpoint requests were successful. Only when this is the case will the checkpoint
    # be updated. Events are imported on a per page basis so an endpoint request could fail mid way through an import.
    # A checkpoint could still be returned, but using it may result in missed data during the next import. If an
    # endpoint request (including all retries) fails mid way through an import this will result in some duplicate data.
    if results_from_import_jobs.get(AGENT_SUCCESS) is True:
        next_agent_checkpoint_date = results_from_import_jobs.get(LAST_ASSESSED_DATE)

        # Save the fallback assessed time when we have no persisted assessed time. This means we wont recalculate the 
        # fallback assessed time every time the integration is executed.
        if next_agent_checkpoint_date is None and assessed_time is None:
            helper.log_info("No Agent assets that qualify to set {} were returned, using fallback time".format(assessed_key))
            next_agent_checkpoint_date = fallback_assessed_time
        
        valid_agent_checkpoint = True
        if assessed_time is not None and next_agent_checkpoint_date is not None:
            prev_assessed_date = date_utils.string_to_datetime(assessed_time)
            if prev_assessed_date is not None and prev_assessed_date > next_agent_checkpoint_date:
                helper.log_error("Most recent last_assessed_for_vulnerabilities is in the past, checkpoint {} will not be updated".format(assessed_key))
                valid_agent_checkpoint = False
        
        if valid_agent_checkpoint is True:
            next_agent_checkpoint = date_utils.datetime_to_string(next_agent_checkpoint_date)
            save_check_point(helper, assessed_key, next_agent_checkpoint)
    else:
        helper.log_info("Processing of Agent collection API requests failed. Latest import time: {}; will pull new data "
                        "from this time, or all data if None the next time import executes".format(assessed_time))
    
    if results_from_import_jobs.get(SCAN_SUCCESS) is True:
        next_scan_checkpoint_date = results_from_import_jobs.get(LAST_SCAN_END_DATE)

        valid_scan_checkpoint = True
        if comparison_time is not None and next_scan_checkpoint_date is not None:
            prev_scan_date = date_utils.string_to_datetime(comparison_time) 
            if prev_scan_date is not None and prev_scan_date > next_scan_checkpoint_date:
                helper.log_error("Most recent last_scan_end is in the past, checkpoint {} will not be updated".format(state_key))
                valid_scan_checkpoint = False
        
        if valid_scan_checkpoint is True:
            next_scan_checkpoint = date_utils.datetime_to_string(next_scan_checkpoint_date)
            save_check_point(helper, state_key, next_scan_checkpoint)
    else:
        helper.log_info("Processing of Scan data API requests failed. Latest import time: {}; will pull new data from "
                        "this time or all data if None, the next time import executes".format(comparison_time))

    # For upgrades we may not perform a full import, but have set a full_import_schedule. In this case the current
    # time becomes the last_initial_import date.
    if not last_initial_import_date and full_import_schedule is not None and full_import_schedule != '':
        save_check_point(helper, last_full_import_key, current_time)

def is_force_full_import(helper, last_initial_import_date, full_import_schedule, now):
    if last_initial_import_date and full_import_schedule is not None and full_import_schedule != '':
        last_initial_import_date = date_utils.string_to_datetime(last_initial_import_date)
        full_import_scheduled_date = last_initial_import_date + datetime.timedelta(days=int(full_import_schedule))

        # Logic to allow user to run an initial import every x days, as defined by the full_import_schedule
        if now >= full_import_scheduled_date:
            helper.log_info("{} is after the number of days ({}) since the last full import ({}). Forcing a full import."
                .format(now, full_import_schedule, last_initial_import_date))
            return True
        else:
            helper.log_debug("{} is before the number of days ({}) since the last full import ({})."
                .format(now, full_import_schedule, last_initial_import_date))

    return False

def print_checkpoint(helper, name, value):
    helper.log_info("[checkpoint] {} is {}".format(name, value))

def get_state_keys(helper):
    input_name = helper.get_input_stanza_names()
    scan_key = SCAN_CHECKPOINT_KEY.format(input_name)
    assessed_key = ASSESSED_CHECKPOINT_KEY.format(input_name)
    last_import_key = LAST_FULL_IMPORT_CHECKPOINT_KEY.format(input_name)

    return scan_key, assessed_key, last_import_key

def get_checkpoint_values(helper):
    state_key, assessed_key, last_import_key = get_state_keys(helper)

    comparison_time = helper.get_check_point(state_key)
    assessed_time = helper.get_check_point(assessed_key)
    last_initial_import_date = helper.get_check_point(last_import_key)

    return comparison_time, assessed_time, last_initial_import_date
