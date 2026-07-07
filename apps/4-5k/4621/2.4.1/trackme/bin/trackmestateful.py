#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import json
import logging
import os
import sys
import time

# Third-party library imports
import requests
import urllib3
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_stateful.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# Import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo, run_splunk_search, trackme_idx_for_tenant, get_splunkd_timeout
from trackme_libs_get_data import search_kv_collection_sdkmode
from trackme_libs_decisionmaker_engine import DecisionMakerEngine
import splunklib.client as client

# Import trackme libs utils
from trackme_libs_utils import decode_unicode, normalize_anomaly_reason, remove_leading_spaces

# Import helper functions from stateful alert helper (these are utility functions, not filtering logic)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trackme"))
from modalert_trackme_stateful_alert_helper import (
    get_keyid_from_main_kvstore,
    get_object_state_from_main_kvstore,
    get_stateful_records_for_object_id,
    validate_object_state,
)

def generate_fields(records):
    """
    Fhis function ensures that records have the same list of fields to allow Splunk to automatically extract these fields
    If a given result does not have a given field, it will be added to the record as an empty value
    """
    all_keys = set()
    for record in records:
        all_keys.update(record.keys())

    for record in records:
        for key in all_keys:
            if key not in record:
                record[key] = ""
        yield record

def get_event_filtering_context(
    helper,
    service,
    server_uri,
    header,
    event,
    maintenance_info,
    alerting_states,
    ack_collection_keys=None,
    ack_collection_dict=None,
    bank_holidays_info=None,
    object_id_cache=None,
    object_state_cache=None,
    stateful_record_cache=None,
):
    """
    Function to gather all context needed for filtering a stateful alert event.
    This includes object_id, object_state, stateful_record, ack status, etc.

    Args:
        helper: The helper object (can be None for custom command usage)
        service: The Splunk service object
        server_uri: The server URI
        header: The authorization header
        event: The event dictionary
        maintenance_info: The maintenance info dictionary
        alerting_states: List of alerting states (e.g., ["red", "orange"])
        ack_collection_keys: Set of object names that have acks (for efficient lookup)
        ack_collection_dict: Dictionary mapping object -> ack_record (for efficient lookup)

    Returns:
        dict: Context dictionary with all filtering-related information
    """
    # Helper function for logging
    def log_debug(msg):
        if helper:
            helper.log_debug(msg)
        else:
            log.debug(msg)

    def log_error(msg):
        if helper:
            helper.log_error(msg)
        else:
            log.error(msg)

    def log_warn(msg):
        if helper:
            helper.log_warn(msg)
        else:
            log.warning(msg)

    # get tenant_id
    tenant_id = event["tenant_id"]

    # get alias, object, object_category, priority
    alias = event.get("alias", None)

    # get object, we may have to deal with problematic non ASCII chars
    object = decode_unicode(event["object"])

    object_category = event["object_category"]
    priority = event.get("priority", "medium")

    # get component from object_category (splk-<component>)
    component = object_category.split("-")[1]

    # check if the ack is active for the object using KVstore lookup
    ack_active = False
    ack_age = 0

    # Use KVstore lookup if ack collection data is provided, otherwise fall back to REST call
    if ack_collection_keys is not None and ack_collection_dict is not None:
        # Efficient KVstore lookup using composite key (object::object_category)
        composite_key = f"{object}::{object_category}"
        if composite_key in ack_collection_keys:
            ack_record = ack_collection_dict.get(composite_key)
            # Record should match since we use composite key
            if ack_record:
                ack_active_string = ack_record.get("ack_state", "inactive")
                ack_mtime_raw = ack_record.get("ack_mtime", None)
                if ack_mtime_raw:
                    try:
                        ack_mtime = float(ack_mtime_raw)
                    except (ValueError, TypeError):
                        ack_mtime = time.time()
                else:
                    ack_mtime = time.time()
                
                if ack_active_string == "active":
                    ack_age = time.time() - ack_mtime
                    ack_active = True
                else:
                    ack_active = False
                    ack_age = 0
            else:
                ack_active = False
                ack_age = 0
        else:
            ack_active = False
            ack_age = 0
        
        # Log the result (object_id will be available after we get it from KVstore)
        if ack_active:
            log_debug(
                f"activity=ack_check, tenant_id={tenant_id}, object={object}, decision=ack_active, "
                f"reason=acknowledgment_is_active, ack_age_seconds={ack_age:.2f}"
            )
        else:
            log_debug(
                f"activity=ack_check, tenant_id={tenant_id}, object={object}, decision=ack_inactive, "
                f"reason=no_active_acknowledgment"
            )
    else:
        # Fallback to REST call if ack collection data not provided
        try:
            ack_response = requests.post(
                f"{server_uri}/services/trackme/v2/ack/get_ack_for_object",
                headers=header,
                data=json.dumps(
                    {
                        "tenant_id": tenant_id,
                        "object_category": object_category,
                        "object_list": object,
                    }
                ),
                verify=False,
                timeout=600,
            )
            ack_response.raise_for_status()
            ack_response_json = ack_response.json()

            if ack_response_json:
                ack_response_json = ack_response_json[0]
                ack_active_string = ack_response_json.get("ack_state", "inactive")
                ack_mtime = float(ack_response_json.get("ack_mtime", time.time()))
                if ack_active_string == "active":
                    ack_age = time.time() - ack_mtime
                    ack_active = True
                    log_debug(
                        f"activity=ack_check, tenant_id={tenant_id}, object={object}, decision=ack_active, "
                        f"reason=acknowledgment_is_active, ack_age_seconds={ack_age:.2f}"
                    )
                else:
                    ack_active = False
                    ack_age = 0
                    log_debug(
                        f"activity=ack_check, tenant_id={tenant_id}, object={object}, decision=ack_inactive, "
                        f"reason=no_active_acknowledgment"
                    )

        except Exception as e:
            log_error(
                f"activity=ack_check, tenant_id={tenant_id}, object={object}, object_category={object_category}, "
                f"decision=error, reason=exception_during_ack_retrieval, exception={str(e)}"
            )
            ack_active = False
            ack_age = 0

    # connect to the main tenant KVstore collection
    collection_main_name = f"kv_trackme_{component}_tenant_{tenant_id}"
    collection_main = service.kvstore[collection_main_name]

    # connect to the stateful KVstore collection
    collection_stateful_alerting_name = (
        f"kv_trackme_stateful_alerting_tenant_{tenant_id}"
    )
    collection_stateful_alerting = service.kvstore[
        collection_stateful_alerting_name
    ]

    # get object_id, if not part of the upstream event, get it from the main KVstore
    # try both "keyid" and "key" fields as some events use different field names
    object_id = event.get("keyid", None)
    if not object_id:
        object_id = event.get("key", None)
    if not object_id:
        # Use cache if available
        cache_key = (object, object_category)
        if object_id_cache is not None and cache_key in object_id_cache:
            object_id = object_id_cache[cache_key]
        else:
            object_id = get_keyid_from_main_kvstore(helper, collection_main, object)
            if object_id_cache is not None:
                object_id_cache[cache_key] = object_id
    if not object_id:
        log_error(
            f"activity=context_gathering, tenant_id={tenant_id}, object={object}, object_category={object_category}, "
            f"object_id=None, decision=skip, reason=no_object_id_found_for_object"
        )
        return None

    # get the object_state from the main KVstore collection (use cache if available)
    if object_state_cache is not None and object_id in object_state_cache:
        (
            collection_object_state,
            collection_anomaly_reason,
            collection_status_message_json,
            collection_monitored_state,
        ) = object_state_cache[object_id]
    else:
        (
            collection_object_state,
            collection_anomaly_reason,
            collection_status_message_json,
            collection_monitored_state,
        ) = get_object_state_from_main_kvstore(helper, collection_main, object_id)
        if object_state_cache is not None:
            object_state_cache[object_id] = (
                collection_object_state,
                collection_anomaly_reason,
                collection_status_message_json,
                collection_monitored_state,
            )

    # get object_state, collection_anomaly_reason and status_message_json from the event, if not present fallback to the collection values
    event_object_state = event.get("object_state", collection_object_state)
    event_anomaly_reason = event.get("anomaly_reason", collection_anomaly_reason)
    # normalize the anomaly_reason
    event_anomaly_reason = normalize_anomaly_reason(event_anomaly_reason)
    event_status_message_json = event.get(
        "status_message_json", collection_status_message_json
    )
    event_monitored_state = event.get("monitored_state", collection_monitored_state)

    # merge
    object_state = (
        event_object_state if event_object_state else collection_object_state
    )
    anomaly_reason = (
        event_anomaly_reason if event_anomaly_reason else collection_anomaly_reason
    )
    status_message_json = (
        event_status_message_json
        if event_status_message_json
        else collection_status_message_json
    )

    # for monitored_state, prefer the collection value instead of the event value
    monitored_state = (
        collection_monitored_state
        if collection_monitored_state
        else event_monitored_state
    )

    # cannot process if object_state is None
    if not object_state:
        log_warn(
            f"activity=context_gathering, tenant_id={tenant_id}, object={object}, object_id={object_id}, "
            f"object_state=None, decision=skip, reason=failed_to_retrieve_object_state_from_kvstore"
        )
        return None

    # get the stateful record, if any (use cache if available)
    if stateful_record_cache is not None and object_id in stateful_record_cache:
        stateful_record = stateful_record_cache[object_id]
    else:
        stateful_record = get_stateful_records_for_object_id(
            helper, collection_stateful_alerting, object_id
        )
        if stateful_record_cache is not None:
            stateful_record_cache[object_id] = stateful_record
    if stateful_record:
        stateful_record_state = stateful_record.get("object_state", "unknown")
        stateful_record_incident_id = stateful_record.get("incident_id", "unknown")
        stateful_record_alert_status = stateful_record.get("alert_status", "unknown")
        log_debug(
            f"activity=context_gathering, tenant_id={tenant_id}, object={object}, object_id={object_id}, "
            f"object_state={object_state}, decision=stateful_record_found, "
            f"reason=active_stateful_record_exists, stateful_record_state={stateful_record_state}, "
            f"incident_id={stateful_record_incident_id}, alert_status={stateful_record_alert_status}"
        )
    else:
        log_debug(
            f"activity=context_gathering, tenant_id={tenant_id}, object={object}, object_id={object_id}, "
            f"object_state={object_state}, decision=no_stateful_record, reason=no_active_stateful_record_found"
        )

    # Helper function for tenant_in_scope
    def tenant_in_scope(tenant_id, tenants_scope):
        try:
            if isinstance(tenants_scope, list):
                scope_list = tenants_scope
            elif isinstance(tenants_scope, str):
                ts = tenants_scope.strip()
                if ts == "" or ts == "*":
                    scope_list = ["*"]
                else:
                    scope_list = [s.strip() for s in ts.split(",") if s.strip()]
            else:
                scope_list = ["*"]
        except Exception:
            scope_list = ["*"]
        if "*" in scope_list:
            return True
        return tenant_id in scope_list

    # Check maintenance status
    maintenance_active = False
    try:
        if maintenance_info and maintenance_info.get("maintenance"):
            if tenant_in_scope(tenant_id, maintenance_info.get("tenants_scope", ["*"])):
                maintenance_active = True
    except Exception:
        maintenance_active = False

    # Check bank holidays status
    bank_holidays_active = False
    try:
        if bank_holidays_info:
            payload = bank_holidays_info.get("payload", bank_holidays_info)
            if payload.get("is_active", False):
                bank_holidays_active = True
    except Exception:
        bank_holidays_active = False

    # Get event time
    event_time = float(event.get("_time", time.time()))

    # Get mtime from stateful_record if it exists
    mtime = None
    if stateful_record:
        mtime_raw = stateful_record.get("mtime")
        if mtime_raw is not None:
            try:
                mtime = float(mtime_raw)
            except (ValueError, TypeError) as e:
                log_warn(
                    f"stateful_record exists but mtime cannot be converted to float: tenant_id={tenant_id}, object={object}, object_id={object_id}, mtime_raw={mtime_raw}, error={str(e)}. Skipping mtime check."
                )
                mtime = None

    return {
        "tenant_id": tenant_id,
        "object": object,
        "object_category": object_category,
        "object_id": object_id,
        "object_state": object_state,
        "monitored_state": monitored_state,
        "component": component,
        "ack_active": ack_active,
        "ack_age": ack_age,
        "stateful_record": stateful_record,
        "maintenance_active": maintenance_active,
        "bank_holidays_active": bank_holidays_active,
        "event_time": event_time,
        "mtime": mtime,
        "priority": priority,
        "anomaly_reason": anomaly_reason,
    }


def get_stateful_alert_config(service, tenant_id):
    """
    Retrieve the stateful alert configuration for a tenant.
    Specifically, finds the stateful alert and extracts the orange_as_alerting_state parameter.
    
    Args:
        service: The Splunk service object
        tenant_id: The tenant identifier
        
    Returns:
        dict: Configuration dict with 'orange_as_alerting_state' (int, 0 or 1) and 'alerting_states' (list)
    """
    try:
        # Search for stateful alerts for this tenant
        # Alert name pattern: "TrackMe alert tenant_id:{tenant_id} - *"
        alert_name_pattern = f"TrackMe alert tenant_id:{tenant_id} -"
        
        # Get all saved searches
        saved_searches = service.saved_searches
        
        # Find the stateful alert
        # Note: Iterating over saved_searches yields SavedSearch objects, not strings
        # We need to access the .name property to get the string name
        stateful_alert = None
        for alert_obj in saved_searches:
            alert_name = alert_obj.name
            if alert_name.startswith(alert_name_pattern):
                # Check if this alert has trackme_stateful_alert action
                actions = alert_obj.content.get("actions", "")
                if isinstance(actions, str):
                    actions_list = [a.strip() for a in actions.split(",") if a.strip()]
                elif isinstance(actions, list):
                    actions_list = actions
                else:
                    actions_list = []
                
                if "trackme_stateful_alert" in actions_list:
                    stateful_alert = alert_obj
                    log.info(
                        f"activity=config_retrieval, tenant_id={tenant_id}, decision=found, "
                        f"reason=stateful_alert_found, alert_name={alert_name}"
                    )
                    break
        
        if not stateful_alert:
            log.info(
                f"activity=config_retrieval, tenant_id={tenant_id}, decision=use_default, "
                f"reason=no_stateful_alert_found"
            )
            # Default: orange is not considered an alerting state
            return {
                "orange_as_alerting_state": 0,
                "alerting_states": ["red"]
            }
        
        # Extract orange_as_alerting_state parameter
        orange_as_alerting_state = 0
        try:
            param_value = stateful_alert.content.get("action.trackme_stateful_alert.param.orange_as_alerting_state")
            if param_value is not None:
                orange_as_alerting_state = int(param_value)
        except (ValueError, TypeError) as e:
            log.warning(
                f"activity=config_retrieval, tenant_id={tenant_id}, decision=use_default, "
                f"reason=failed_to_parse_orange_as_alerting_state, exception={str(e)}"
            )
            orange_as_alerting_state = 0
        
        # Determine alerting states based on configuration
        alerting_states = ["red"]
        if orange_as_alerting_state:
            alerting_states.append("orange")
        
        log.info(
            f"activity=config_retrieval, tenant_id={tenant_id}, decision=retrieved, "
            f"reason=stateful_alert_config_retrieved, orange_as_alerting_state={orange_as_alerting_state}, "
            f"alerting_states={alerting_states}"
        )
        
        return {
            "orange_as_alerting_state": orange_as_alerting_state,
            "alerting_states": alerting_states
        }
        
    except Exception as e:
        log.error(
            f"activity=config_retrieval, tenant_id={tenant_id}, decision=use_default, "
            f"reason=error_retrieving_stateful_alert_configuration, exception={str(e)}"
        )
        # On error, use default configuration
        return {
            "orange_as_alerting_state": 0,
            "alerting_states": ["red"]
        }


def should_prefilter_yield_event(event, context, alerting_states, sourcetype):
    """
    Pre-filtering function to determine if an event meets the basic conditions
    for being investigated by the stateful backend.
    
    Conditions:
    1. No stateful record AND in alerting state (taking into account orange_as_alerting_state config)
    2. Has stateful record BUT state changed (closure, update, or reopening)
    3. SLA breach events (sourcetype=trackme:sla_breaches) - yield as updates if stateful record exists
    
    Args:
        event: The event dictionary
        context: The context dictionary from get_event_filtering_context()
        alerting_states: List of alerting states (e.g., ["red", "orange"])
        sourcetype: The sourcetype of the event
        
    Returns:
        tuple: (should_yield: bool, reason: str or None)
    """
    if context is None:
        return (False, "Failed to gather event context")
    
    stateful_record = context.get("stateful_record")
    object_state = context.get("object_state")
    
    # Condition 3: SLA breach events - yield if there's a stateful record (update scenario)
    # or if in alerting state (new incident scenario)
    if sourcetype == "trackme:sla_breaches":
        if stateful_record:
            return (True, "SLA breach event with existing stateful record - yield as update")
        elif object_state in alerting_states:
            return (True, f"SLA breach event in alerting state - object_state={object_state} is in alerting_states={alerting_states}")
        else:
            return (False, f"SLA breach event but object_state={object_state} is not in alerting_states={alerting_states}")
    
    # Condition 1: No stateful record AND in alerting state
    if not stateful_record:
        if object_state in alerting_states:
            return (True, f"No stateful record and object_state={object_state} is in alerting_states={alerting_states}")
        else:
            return (False, f"No stateful record but object_state={object_state} is not in alerting_states={alerting_states}")
    
    # Condition 2: Has stateful record BUT state changed (closure, update, or reopening)
    # Always yield when state changes, regardless of sourcetype
    stateful_record_object_state = stateful_record.get("object_state")
    if stateful_record_object_state != object_state:
        return (True, f"State changed: previous_state={stateful_record_object_state}, new_state={object_state}")
    
    # Condition 3: Has stateful record, state unchanged, but sourcetype indicates discrete event
    # For discrete events (SLA breaches, notables, flips), yield updates even if state unchanged
    # For continuous events (trackme:state), skip to avoid repeated updates
    
    # Check for flip events (state transitions) - discrete events
    if sourcetype == "trackme:flip":
        return (True, f"Flip event with existing stateful record - yield as update even if state unchanged")
    
    # Check for notable events (sourcetype might be from trackme_notable_idx) - discrete events
    if sourcetype and "notable" in sourcetype.lower():
        return (True, f"Notable event with existing stateful record - yield as update even if state unchanged")
    
    # For trackme:state (continuous events), don't yield if state unchanged
    # This prevents repeated updates for entities that remain in the same alerting state
    # Continuous events should only create updates when state actually changes
    if sourcetype == "trackme:state":
        mtime = context.get("mtime")
        event_time = context.get("event_time")
        if mtime is not None and event_time is not None:
            return (False, f"Has stateful record, state unchanged, trackme:state continuous event - skipping to avoid duplicate updates: object_state={object_state}, event_time={event_time}, mtime={mtime}")
        return (False, f"Has stateful record and state unchanged: object_state={object_state}, sourcetype={sourcetype}")
    
    # For other sourcetypes (including SLA breaches handled earlier, but as fallback), yield if state unchanged
    # Discrete events should create updates even when state hasn't changed
    return (True, f"Has stateful record, state unchanged, but discrete event type - yield as update: object_state={object_state}, sourcetype={sourcetype}")


def filter_stateful_alert_event(
    helper,
    server_uri,
    splunkd_port,
    header,
    event,
    context,
    alerting_states,
    validation_engine_cache,
    validation_cache=None,
    sourcetype=None,
):
    """
    Function to filter a stateful alert event based on all filtering criteria.
    Returns True if the event should be processed, False if it should be skipped.

    Args:
        helper: The helper object (can be None for custom command usage)
        server_uri: The server URI
        splunkd_port: The splunkd REST port — passed through to
            validate_object_state so the engine can open its own splunklib
            service connection. Caller must pass this explicitly (typically
            reqinfo["server_rest_port"]); no fallback host/port is invented.
        header: The authorization header
        event: The event dictionary
        context: The context dictionary from get_event_filtering_context()
        alerting_states: List of alerting states (e.g., ["red", "orange"])
        validation_engine_cache: Dict shared across every
            validate_object_state call within this trackmestateful run,
            keyed by (tenant_id, component) → DecisionMakerEngine (or
            None for cached construction failures). Caller-supplied so
            the engine load() pass is paid once per unique
            (tenant, component), not once per validation.

    Returns:
        tuple: (should_process: bool, skip_reason: str or None)
    """
    if context is None:
        return (False, "Failed to gather event context")

    # Helper function for logging
    def log_info(msg):
        if helper:
            helper.log_info(msg)
        else:
            log.info(msg)

    def log_debug(msg):
        if helper:
            helper.log_debug(msg)
        else:
            log.debug(msg)

    tenant_id = context["tenant_id"]
    object = context["object"]
    object_id = context["object_id"]
    object_state = context["object_state"]
    monitored_state = context["monitored_state"]
    component = context["component"]
    ack_active = context["ack_active"]
    ack_age = context["ack_age"]
    stateful_record = context["stateful_record"]
    maintenance_active = context["maintenance_active"]
    bank_holidays_active = context.get("bank_holidays_active", False)
    event_time = context["event_time"]
    mtime = context["mtime"]

    # if the monitored_state is "disabled", we need to skip the processing
    if monitored_state == "disabled":
        return (
            False,
            f'monitored_state is disabled: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}',
        )

    # if the stateful record is not found, we need to check if we should create a new thread
    if not stateful_record:
        if maintenance_active and object_state in alerting_states:
            return (
                False,
                f"maintenance active, skipping new incident creation: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}",
            )
        if bank_holidays_active and object_state in alerting_states:
            return (
                False,
                f"bank holidays active, skipping new incident creation: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}",
            )
        # Check if ack is active and older than 5 minutes - if yes, skip creating new incident
        if ack_active and ack_age > 300:  # 300 seconds = 5 minutes
            return (
                False,
                f'Ack is active and older than 5 minutes: tenant_id={tenant_id}, object={object}, object_id={object_id}, ack_active=True, ack_age={ack_age:.2f} seconds',
            )

        # Safety check: Validate object_state via REST call before accepting entity for alert
        # This ensures the entity is actually in an alerting state according to the decision maker
        if object_state in alerting_states:
            # Use cache if available (with short TTL since state can change)
            cache_key = (object_id, tuple(sorted(alerting_states)))
            cache_ttl = 5  # Cache validation results for 5 seconds
            current_time = time.time()
            
            if validation_cache is not None and cache_key in validation_cache:
                cached_result, cached_time = validation_cache[cache_key]
                if current_time - cached_time < cache_ttl:
                    is_valid, actual_object_state, error_message = cached_result
                else:
                    # Cache expired, refresh
                    is_valid, actual_object_state, error_message = validate_object_state(
                        helper=helper,
                        server_uri=server_uri,
                        splunkd_port=splunkd_port,
                        header=header,
                        tenant_id=tenant_id,
                        component=component,
                        object_id=object_id,
                        alerting_states=alerting_states,
                        engine_cache=validation_engine_cache,
                    )
                    validation_cache[cache_key] = ((is_valid, actual_object_state, error_message), current_time)
            else:
                is_valid, actual_object_state, error_message = validate_object_state(
                    helper=helper,
                    server_uri=server_uri,
                    splunkd_port=splunkd_port,
                    header=header,
                    tenant_id=tenant_id,
                    component=component,
                    object_id=object_id,
                    alerting_states=alerting_states,
                    engine_cache=validation_engine_cache,
                )
                if validation_cache is not None:
                    validation_cache[cache_key] = ((is_valid, actual_object_state, error_message), current_time)

            if not is_valid:
                # Skip this event - the actual object_state from the decision maker is not in alerting_states
                return (
                    False,
                    f"Object state validation failed: actual_object_state={actual_object_state}, expected_states={alerting_states}: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}",
                )

        # do not process if no stateful_record and object_state is green/blue
        if object_state not in alerting_states:
            return (
                False,
                f'no stateful record and non-alerting state: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}, event_id={event.get("event_id")}',
            )

    # check if the event should be skipped (for existing stateful records)
    if stateful_record:
        # Check if the current event's message_source_id (event_id) matches the one used for opened status
        # If they match, we should not allow an updated status
        event_id = event.get("event_id")
        stateful_record_message_source_id = stateful_record.get("message_source_id")
        if stateful_record_message_source_id and event_id and stateful_record_message_source_id == event_id:
            # The event_id (message_source_id) is the same as the one used for opened status
            # Skip processing this event to prevent duplicate updates
            return (
                False,
                f"event_id matches the one used for opened status, preventing duplicate update: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}, event_id={event_id}",
            )
        
        # Additional check: If the action would be updated BUT the sourcetype is trackme:state or trackme:flip
        # AND anomaly_reason has not changed, we should skip the updated event
        if sourcetype in ("trackme:state", "trackme:flip") and object_state in alerting_states:
            # Get current event's anomaly_reason from context (already normalized)
            current_anomaly_reason = context.get("anomaly_reason", [])
            if not isinstance(current_anomaly_reason, list):
                current_anomaly_reason = normalize_anomaly_reason(current_anomaly_reason)
            
            # Get stored anomaly_reason from stateful record (merge opened and updated)
            stored_opened_anomaly_reason = normalize_anomaly_reason(stateful_record.get("opened_anomaly_reason", []))
            stored_updated_anomaly_reason = normalize_anomaly_reason(stateful_record.get("updated_anomaly_reason", []))
            # Merge stored anomaly reasons (same logic as in helper)
            stored_anomaly_reason = list(set(stored_opened_anomaly_reason + stored_updated_anomaly_reason))
            
            # Compare anomaly_reason lists (order doesn't matter, so compare as sets)
            if isinstance(current_anomaly_reason, list) and isinstance(stored_anomaly_reason, list):
                if set(current_anomaly_reason) == set(stored_anomaly_reason):
                    # Anomaly reason hasn't changed, skip the update
                    return (
                        False,
                        f"anomaly_reason unchanged for trackme:state/trackme:flip event, skipping update: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}, sourcetype={sourcetype}, anomaly_reason={current_anomaly_reason}",
                    )
        
        # Get the object_state from the stateful record for comparison
        stateful_record_object_state = stateful_record.get("object_state")
        
        # Check if the state has changed - if it has, we should process even with active Ack
        state_changed = stateful_record_object_state != object_state
        
        # if we have a stateful record with mtime, and the event time is not newer than the mtime, we can skip the processing
        # UNLESS the state has changed (in which case we need to process to update/close the incident)
        if mtime is not None and event_time <= mtime and not state_changed:
            return (
                False,
                f'event is not newer than stateful record last update: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}, event_time={time.strftime("%c", time.localtime(event_time))}, mtime={time.strftime("%c", time.localtime(mtime))}',
            )

        # Early exit checks: If state hasn't changed and we're going to skip due to maintenance/bank holidays,
        # skip without validation to avoid unnecessary REST calls
        if not state_changed:
            if maintenance_active and object_state in alerting_states:
                return (
                    False,
                    f"maintenance active, skipping incident update: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}",
                )
            if bank_holidays_active and object_state in alerting_states:
                return (
                    False,
                    f"bank holidays active, skipping incident update: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}",
                )

        # Safety check: Validate object_state via REST call before accepting entity for alert update
        # This ensures the entity is actually in an alerting state according to the decision maker
        # Only validate if:
        # 1. Object is in alerting state AND
        # 2. We're actually going to process it (state changed OR not in maintenance/bank holidays)
        if object_state in alerting_states:
            # Use cache if available (with short TTL since state can change)
            cache_key = (object_id, tuple(sorted(alerting_states)))
            cache_ttl = 5  # Cache validation results for 5 seconds
            current_time = time.time()
            
            if validation_cache is not None and cache_key in validation_cache:
                cached_result, cached_time = validation_cache[cache_key]
                if current_time - cached_time < cache_ttl:
                    is_valid, actual_object_state, error_message = cached_result
                else:
                    # Cache expired, refresh
                    is_valid, actual_object_state, error_message = validate_object_state(
                        helper=helper,
                        server_uri=server_uri,
                        splunkd_port=splunkd_port,
                        header=header,
                        tenant_id=tenant_id,
                        component=component,
                        object_id=object_id,
                        alerting_states=alerting_states,
                        engine_cache=validation_engine_cache,
                    )
                    validation_cache[cache_key] = ((is_valid, actual_object_state, error_message), current_time)
            else:
                is_valid, actual_object_state, error_message = validate_object_state(
                    helper=helper,
                    server_uri=server_uri,
                    splunkd_port=splunkd_port,
                    header=header,
                    tenant_id=tenant_id,
                    component=component,
                    object_id=object_id,
                    alerting_states=alerting_states,
                    engine_cache=validation_engine_cache,
                )
                if validation_cache is not None:
                    validation_cache[cache_key] = ((is_valid, actual_object_state, error_message), current_time)

            if not is_valid:
                # Skip this event - the actual object_state from the decision maker is not in alerting_states
                return (
                    False,
                    f"Object state validation failed: actual_object_state={actual_object_state}, expected_states={alerting_states}: tenant_id={tenant_id}, object={object}, object_id={object_id}, object_state={object_state}",
                )
        
        # IMPORTANT: If state has changed, process the event even if Ack is active
        # This ensures incidents are properly opened/updated/closed when state changes occur
        if state_changed:
            # Debug-level: this fires per pre-dedup event for every yielded
            # candidate. With the new selective search arm, that's roughly
            # one line per state transition processed — duplicative against
            # the durable audit trail (stateful_alerting KV updates +
            # ingested trackme:stateful_alerts events). The summary
            # activity=completion event still reports events_yielded.
            log_debug(
                f"activity=filtering, tenant_id={tenant_id}, object={object}, object_id={object_id}, "
                f"object_state={object_state}, decision=process, reason=state_changed, "
                f"previous_state={stateful_record_object_state}, new_state={object_state}, ack_active={ack_active}"
            )
            # Continue processing - don't skip due to Ack

    # Event passed all filtering criteria
    return (True, None)


@Configuration(distributed=False)
class TrackMeStateful(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get configurable splunkd timeout
        splunkd_timeout = get_splunkd_timeout(reqinfo=reqinfo)

        # Get earliest and latest times
        earliest = self._metadata.searchinfo.earliest_time
        latest = self._metadata.searchinfo.latest_time

        # Get service
        server_uri = self._metadata.searchinfo.splunkd_uri
        session_key = self._metadata.searchinfo.session_key
        splunkd_port = reqinfo["server_rest_port"]
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=session_key,
            timeout=600,
        )

        # Build header for REST calls
        header = {
            "Authorization": f"Splunk {session_key}",
            "Content-Type": "application/json",
        }

        # Retrieve stateful alert configuration to determine alerting states
        # This includes the "orange_as_alerting_state" setting
        alert_config = get_stateful_alert_config(service, self.tenant_id)
        alerting_states = alert_config["alerting_states"]
        orange_as_alerting_state = alert_config["orange_as_alerting_state"]
        
        log.info(
            f"activity=initialization, tenant_id={self.tenant_id}, decision=configured, "
            f"reason=alerting_states_configured, alerting_states={alerting_states}, "
            f"orange_as_alerting_state={orange_as_alerting_state}"
        )

        # Load ack collection once for efficient lookup (instead of REST calls per event)
        # Use composite keys (object::object_category) to avoid collisions when same object exists in multiple categories
        ack_collection_keys = None
        ack_collection_dict = None
        try:
            ack_collection_name = f"kv_trackme_common_alerts_ack_tenant_{self.tenant_id}"
            (
                ack_records,
                _,
                _,
                last_page,
            ) = search_kv_collection_sdkmode(
                log, service, ack_collection_name, page=1, page_count=0, orderby="keyid"
            )
            # Build composite key dictionary to avoid collisions
            ack_collection_dict = {}
            ack_collection_keys = set()
            for record in ack_records:
                obj = record.get("object")
                obj_cat = record.get("object_category")
                if obj and obj_cat:
                    composite_key = f"{obj}::{obj_cat}"
                    ack_collection_dict[composite_key] = record
                    ack_collection_keys.add(composite_key)
            log.info(
                f"activity=initialization, tenant_id={self.tenant_id}, decision=loaded, "
                f"reason=ack_collection_loaded_for_efficient_lookup, ack_records_count={len(ack_records)}, "
                f"unique_composite_keys={len(ack_collection_keys)}"
            )
        except Exception as e:
            log.warning(
                f"activity=initialization, tenant_id={self.tenant_id}, decision=fallback, "
                f"reason=ack_collection_load_failed_will_use_rest_calls, exception={str(e)}"
            )
            # Will fall back to REST calls per event if collection load fails
            ack_collection_keys = None
            ack_collection_dict = None

        # Get maintenance status
        try:
            endpoint = f"{server_uri}/services/trackme/v2/maintenance/check_global_maintenance_status"
            resp = requests.get(endpoint, headers=header, verify=False, timeout=splunkd_timeout)
            resp.raise_for_status()
            maintenance_info = resp.json()
            # Normalize tenants_scope
            if isinstance(maintenance_info.get("tenants_scope"), str):
                ts = maintenance_info.get("tenants_scope", "*").strip()
                if ts == "" or ts == "*":
                    maintenance_info["tenants_scope"] = ["*"]
                else:
                    maintenance_info["tenants_scope"] = [
                        s.strip() for s in ts.split(",") if s.strip()
                    ]
            elif not isinstance(maintenance_info.get("tenants_scope"), list):
                maintenance_info["tenants_scope"] = ["*"]
        except Exception as e:
            log.error(
                f"activity=maintenance_check, tenant_id={self.tenant_id}, decision=error, "
                f"reason=maintenance_check_failed, exception={str(e)}"
            )
            maintenance_info = None

        # Get bank holidays status
        bank_holidays_info = None
        try:
            endpoint = f"{server_uri}/services/trackme/v2/bank_holidays/check_active"
            resp = requests.get(endpoint, headers=header, verify=False, timeout=splunkd_timeout)
            resp.raise_for_status()
            bank_holidays_info = resp.json()
            log.info(
                f"activity=bank_holidays_check, tenant_id={self.tenant_id}, decision=retrieved, "
                f"reason=bank_holidays_status_retrieved, is_active={bank_holidays_info.get('payload', {}).get('is_active', False)}"
            )
        except Exception as e:
            log.error(
                f"activity=bank_holidays_check, tenant_id={self.tenant_id}, decision=error, "
                f"reason=bank_holidays_check_failed, exception={str(e)}"
            )
            bank_holidays_info = None

        # Resolve tenant-specific indexes to avoid subsearch macro overhead
        tenant_indexes = trackme_idx_for_tenant(session_key, server_uri, self.tenant_id)
        tenant_trackme_summary_idx = tenant_indexes.get("trackme_summary_idx", "trackme_summary")
        tenant_trackme_notable_idx = tenant_indexes.get("trackme_notable_idx", "trackme_notable")

        log.info(
            f"activity=initialization, tenant_id={self.tenant_id}, decision=resolved, "
            f"reason=tenant_indexes_resolved, trackme_summary_idx={tenant_trackme_summary_idx}, "
            f"trackme_notable_idx={tenant_trackme_notable_idx}"
        )

        # Build the alerting-states predicate used by the trackme:state arm
        # of the search below. This dynamically reflects the alert's actual
        # `orange_as_alerting_state` configuration — when orange is not
        # configured as alerting, the predicate is kept as tight as possible
        # (red only).
        if len(alerting_states) == 1:
            alerting_states_spl = f'object_state="{alerting_states[0]}"'
        else:
            alerting_states_spl = (
                "(" + " OR ".join(f'object_state="{s}"' for s in alerting_states) + ")"
            )

        # Pre-load the set of active stateful records (alert_status in
        # opened/updated) solely to build the literal `key="..."`
        # predicate for the trackme:state arm of the search below.
        #
        # We deliberately do NOT pre-populate `stateful_record_cache`
        # from these records: the per-event call to
        # get_stateful_records_for_object_id() applies mtime-based
        # selection when multiple non-closed records exist for the same
        # object_id, and also closes duplicate non-closed records as a
        # data-integrity side effect. A naive cache pre-population that
        # stored "whichever record came last" from this query would
        # silently bypass both behaviours for the active-record cohort.
        # The cache stays lazy as before.
        #
        # No Splunk subsearch is dispatched, the default subsearch row
        # limit does not apply, and there is no double-evaluation of the
        # same predicate in multiple places of the query.
        #
        # `alert_status` of "closed" is deliberately excluded — a closed
        # incident has a terminal lifecycle; any new transition for that
        # entity will be surfaced by the trackme:flip arm of the search.
        #
        # A KVstore read failure here is treated as a hard error (no
        # defensive try/except): if KVstore is unavailable, the command
        # cannot function correctly anyway, and the per-event KV reads
        # downstream would fail as well.
        stateful_collection_name = f"kv_trackme_stateful_alerting_tenant_{self.tenant_id}"
        stateful_collection = service.kvstore[stateful_collection_name]
        active_stateful_records = stateful_collection.data.query(
            query=json.dumps({
                "$or": [
                    {"alert_status": "opened"},
                    {"alert_status": "updated"},
                ]
            })
        )

        # Build the de-duplicated active-incident object_id list. The
        # KV query may return multiple records for the same object_id
        # when duplicate non-closed records exist (a defensive state
        # the alert action handles via mtime-selection + cleanup); for
        # our purposes — building the search filter — we only need the
        # unique set of object_ids.
        seen_object_ids = set()
        active_object_ids = []
        for record in active_stateful_records:
            oid = record.get("object_id")
            if oid and oid not in seen_object_ids:
                seen_object_ids.add(oid)
                active_object_ids.append(oid)

        log.info(
            f"activity=initialization, tenant_id={self.tenant_id}, "
            f"reason=active_stateful_records_loaded, "
            f"active_records_count={len(active_object_ids)}"
        )

        # Build the trackme:state arm inner filter, with a defensive cap
        # on the size of the literal key predicate.
        #
        # Each `key="<sha256>"` clause is ~74 characters. Splunk's
        # `max_search_query_length` default is around 100K characters,
        # so a few thousand active incidents would push the resolved
        # SPL past the limit and cause the search to fail outright —
        # exactly the wrong moment, since a high active-incident count
        # implies a mass-outage scenario where alerting matters most.
        #
        # Above the cap we fall back to the non-selective state-arm
        # form: the trackme:state arm carries no inner filter and
        # matches every monitored heartbeat event for the tenant
        # (the original pre-PR behaviour). This preserves
        # closure-detection correctness fully at the cost of search
        # performance, and is much safer than silently truncating the
        # key list. A WARNING-level log line surfaces the situation.
        MAX_KEY_PREDICATE_ACTIVE_RECORDS = 1000
        if len(active_object_ids) > MAX_KEY_PREDICATE_ACTIVE_RECORDS:
            log.warning(
                f"activity=initialization, tenant_id={self.tenant_id}, "
                f"reason=active_records_above_cap, "
                f"active_records_count={len(active_object_ids)}, "
                f"cap={MAX_KEY_PREDICATE_ACTIVE_RECORDS}, "
                f"fallback=non_selective_state_arm, "
                f"impact=search_will_return_all_state_heartbeats_for_this_tenant_until_active_record_count_drops_below_cap"
            )
            # Empty inner predicate → state arm matches every state event
            # passing the outer filter (non-selective fallback).
            state_arm_inner = ""
        elif active_object_ids:
            open_incidents_predicate = (
                "(" + " OR ".join(f'key="{oid}"' for oid in active_object_ids) + ")"
            )
            state_arm_inner = (
                f"({open_incidents_predicate} OR {alerting_states_spl})"
            )
        else:
            # No active incidents — only new alerting candidates matter.
            state_arm_inner = alerting_states_spl

        # Build the stateful alert search query.
        #
        # The trackme:state arm is SELECTIVE — it returns only events that
        # are structurally relevant to the stateful pipeline, rather than
        # the full per-entity heartbeat volume. Across multiple production
        # deployments we have consistently observed ~99.9% of the
        # non-selective arm's events being pre-filtered and discarded by
        # the Python stage, with `search_run_time_seconds` dominating the
        # total command runtime under load (worst observed: avg >200s,
        # p95 >700s, max >8000s). This change pushes the filtering into
        # Splunk itself, with the active-incident key list pre-resolved in
        # Python (above) rather than via a Splunk subsearch.
        #
        # The state arm is the union of two clauses:
        #   - events for entities currently bound to an active stateful
        #     record (closure / update path), and
        #   - events for entities currently in an alerting state
        #     (bootstrap / discovery path; covers entities not yet in an
        #     active record). When an entity has both an active record
        #     AND is currently alerting, both sub-clauses match the same
        #     event — Splunk's OR returns each event exactly once
        #     regardless of how many sub-clauses match, so this is
        #     harmless.
        #
        # The trackme:flip, trackme:sla_breaches and trackme_notable arms
        # remain naturally sparse. The notable arm specifies
        # `sourcetype=trackme:notable` explicitly: without it, some
        # Splunk environments apply eventtype-driven query expansion when
        # an index is searched without a sourcetype constraint, pulling
        # in large lists of unrelated sourcetypes and predicates that
        # significantly bloat the resolved search.
        search_query = remove_leading_spaces(f"""\
            search (index="{tenant_trackme_summary_idx}" (sourcetype=trackme:state) tenant_id="{self.tenant_id}" object_category="*" monitored_state="enabled"
                {state_arm_inner}
            )
            OR (index="{tenant_trackme_summary_idx}" (sourcetype=trackme:flip) tenant_id="{self.tenant_id}" object_category="*" object_previous_state!="discovered")
            OR (index="{tenant_trackme_summary_idx}" (sourcetype=trackme:sla_breaches) tenant_id="{self.tenant_id}" object_category="*")
            OR (index="{tenant_trackme_notable_idx}" sourcetype=trackme:notable tenant_id="{self.tenant_id}" object_category=*)
            """)

        # Log the fully-resolved SPL at INFO level for observability.
        # This makes it possible to inspect the exact query that will be
        # dispatched without needing the Splunk job inspector — useful for
        # troubleshooting, performance analysis, and verifying that the
        # active-records pre-load produced the expected key list.
        log.info(
            f"activity=initialization, tenant_id={self.tenant_id}, "
            f"reason=search_query_built, search_query={search_query}"
        )

        # Search parameters
        search_kwargs = {
            "earliest_time": earliest,
            "latest_time": latest,
            "count": 0,
            "output_mode": "json",
        }

        log.info(
            f"activity=initialization, tenant_id={self.tenant_id}, decision=start, reason=trackmestateful_command_started"
        )

        # Create a minimal helper-like object for filtering functions
        class MinimalHelper:
            def log_info(self, msg):
                log.info(msg)

            def log_debug(self, msg):
                log.debug(msg)

            def log_error(self, msg):
                log.error(msg)

            def log_warn(self, msg):
                log.warning(msg)

        minimal_helper = MinimalHelper()

        # Initialize caches for performance optimization
        # These caches avoid redundant KVstore queries and REST calls for the same object across multiple events
        object_id_cache = {}  # (object, object_category) -> object_id
        object_state_cache = {}  # object_id -> (object_state, anomaly_reason, status_message_json, monitored_state)
        stateful_record_cache = {}  # object_id -> stateful_record
        validation_cache = {}  # (object_id, alerting_states_tuple) -> ((is_valid, actual_object_state, error_message), timestamp)
        score_cache = {}  # object_id -> (score, score_definition, tags)
        # Cache one DecisionMakerEngine per component encountered in this run.
        # The engine amortizes the heavy KV/scoring loads across all events for
        # the same component; per-event evaluation is then a single KV record
        # lookup + the in-process per-record orchestration. Replaces the per-
        # event load_component_data HTTP roundtrip that previously dominated
        # this loop's runtime in busy environments.
        # Value is the engine instance, or None if construction/load failed
        # (cached so we don't retry per-event).
        engines_by_component = {}

        # Engine cache shared across every validate_object_state call within
        # this trackmestateful run, keyed by (tenant_id, component) →
        # DecisionMakerEngine. Same purpose as engines_by_component but
        # consumed by the helper-shared validate_object_state function in
        # modalert_trackme_stateful_alert_helper, which constructs its own
        # engine (no pre-built service) — kept as a separate dict to avoid
        # surprising aliasing between the two construction paths.
        validation_engine_cache = {}

        def _get_engine(component):
            if component not in engines_by_component:
                try:
                    engine = DecisionMakerEngine(
                        session_key=session_key,
                        splunkd_uri=server_uri,
                        tenant_id=self.tenant_id,
                        component=component,
                        # Pass splunkd_port so the engine can lazily build
                        # its system-level service connection during load()
                        # (used for conf reads via system_authtoken). The
                        # passed-in `service` covers the user-level KV
                        # reads only — service_system is constructed by
                        # the engine itself and needs the port.
                        splunkd_port=splunkd_port,
                        service=service,
                        logger=log,
                    )
                    engine.load()
                    engines_by_component[component] = engine
                    log.info(
                        f"activity=load_entity_data, tenant_id={self.tenant_id}, component={component}, "
                        f"decision=engine_loaded, reason=DecisionMakerEngine_initialized_for_component"
                    )
                except Exception as engine_load_exc:
                    log.warning(
                        f"activity=load_entity_data, tenant_id={self.tenant_id}, component={component}, "
                        f"decision=error, reason=engine_construction_failed, "
                        f"exception={str(engine_load_exc)}"
                    )
                    engines_by_component[component] = None
            return engines_by_component[component]

        log.info(
            f"activity=initialization, tenant_id={self.tenant_id}, decision=caches_initialized, "
            f"reason=performance_optimization_caches_created"
        )

        # Execute the search
        try:
            search_start_time = time.time()
            reader = run_splunk_search(
                service, search_query, search_kwargs, 24, 5
            )

            events_processed = 0
            events_yielded = 0
            events_filtered = 0
            events_passed_filters = 0  # Track events that passed all filters (before deduplication)

            # Deduplication: Track latest event per (object_id, sourcetype) combination
            # This prevents race conditions where multiple events for the same object
            # in a single execution cause multiple updates (opened -> updated)
            events_by_key = {}  # key: (object_id, sourcetype) -> (yield_event, _time, context)

            for item in reader:
                if isinstance(item, dict):
                    events_processed += 1

                    # Get filtering context for this event
                    try:
                        event = item.get("_raw")
                        if not isinstance(event, dict):
                            if event is None:
                                raise ValueError("Event _raw field is None")
                            event = json.loads(event)

                        # get original Splunk metadata: index, sourcetype, host, source
                        index = item.get("index")
                        sourcetype = item.get("sourcetype")
                        host = item.get("host")
                        source = item.get("source")

                        yield_event = {
                            "_time": event.get("_time", time.time()),
                            "index": index,
                            "sourcetype": sourcetype,
                            "host": host,
                            "source": source,
                            "_raw": event,
                        }
                        for key, value in event.items():
                            yield_event[key] = value
                        context = get_event_filtering_context(
                            helper=minimal_helper,
                            service=service,
                            server_uri=server_uri,
                            header=header,
                            event=event,
                            maintenance_info=maintenance_info,
                            alerting_states=alerting_states,
                            ack_collection_keys=ack_collection_keys,
                            ack_collection_dict=ack_collection_dict,
                            bank_holidays_info=bank_holidays_info,
                            object_id_cache=object_id_cache,
                            object_state_cache=object_state_cache,
                            stateful_record_cache=stateful_record_cache,
                        )

                        # If context gathering failed, skip this event
                        if context is None:
                            events_filtered += 1
                            log.warning(
                                f"activity=context_gathering, tenant_id={event.get('tenant_id')}, object={event.get('object')}, "
                                f"decision=skip, reason=context_gathering_failed"
                            )
                            continue

                        # Pre-filter: Check if event meets basic conditions for stateful backend
                        should_prefilter_yield, prefilter_reason = should_prefilter_yield_event(
                            event=event,
                            context=context,
                            alerting_states=alerting_states,
                            sourcetype=sourcetype,
                        )

                        if not should_prefilter_yield:
                            events_filtered += 1
                            log.debug(
                                f"activity=pre_filter, tenant_id={context.get('tenant_id')}, object={context.get('object')}, "
                                f"object_id={context.get('object_id')}, object_state={context.get('object_state')}, "
                                f"decision=skip, reason={prefilter_reason if prefilter_reason else 'unknown_reason'}"
                            )
                            continue

                        # Event passed pre-filter, now apply full filtering logic
                        # (ack checks, maintenance checks, validation, etc.)
                        should_process, skip_reason = filter_stateful_alert_event(
                            helper=minimal_helper,
                            server_uri=server_uri,
                            splunkd_port=splunkd_port,
                            header=header,
                            event=event,
                            context=context,
                            alerting_states=alerting_states,
                            validation_engine_cache=validation_engine_cache,
                            validation_cache=validation_cache,
                            sourcetype=sourcetype,
                        )

                        if should_process:
                            # Event passed all filters - add to deduplication dict
                            events_passed_filters += 1
                            
                            # Use (object_id, sourcetype) as key to deduplicate within this execution
                            object_id = context.get('object_id')
                            dedup_key = (object_id, sourcetype)
                            # Convert _time to float for consistent comparison (handles string epoch timestamps)
                            event_time = float(yield_event.get("_time", time.time()))
                            
                            # Keep only the latest event per (object_id, sourcetype) combination
                            if dedup_key not in events_by_key:
                                events_by_key[dedup_key] = (yield_event, event_time, context, prefilter_reason)
                                log.debug(
                                    f"activity=deduplication, tenant_id={context.get('tenant_id')}, object={context.get('object')}, "
                                    f"object_id={object_id}, sourcetype={sourcetype}, decision=added, "
                                    f"reason=first_event_for_object_sourcetype_combination, event_time={event_time}"
                                )
                            else:
                                existing_event, existing_time, existing_context, existing_reason = events_by_key[dedup_key]
                                # Ensure existing_time is also float for safe comparison
                                if not isinstance(existing_time, (int, float)):
                                    existing_time = float(existing_time)
                                if event_time > existing_time:
                                    # This event is newer, replace the existing one
                                    events_by_key[dedup_key] = (yield_event, event_time, context, prefilter_reason)
                                    log.debug(
                                        f"activity=deduplication, tenant_id={context.get('tenant_id')}, object={context.get('object')}, "
                                        f"object_id={object_id}, sourcetype={sourcetype}, decision=replaced, "
                                        f"reason=newer_event_found, old_time={existing_time}, new_time={event_time}"
                                    )
                                else:
                                    log.debug(
                                        f"activity=deduplication, tenant_id={context.get('tenant_id')}, object={context.get('object')}, "
                                        f"object_id={object_id}, sourcetype={sourcetype}, decision=skipped, "
                                        f"reason=older_event_ignored, existing_time={existing_time}, event_time={event_time}"
                                    )
                            
                            log.debug(
                                f"activity=filtering, tenant_id={context.get('tenant_id')}, object={context.get('object')}, "
                                f"object_id={context.get('object_id')}, object_state={context.get('object_state')}, "
                                f"decision=yield, reason=passed_pre_filter_and_full_filter, prefilter_reason={prefilter_reason}"
                            )
                        else:
                            events_filtered += 1
                            log.debug(
                                f"activity=filtering, tenant_id={context.get('tenant_id')}, object={context.get('object')}, "
                                f"object_id={context.get('object_id')}, object_state={context.get('object_state')}, "
                                f"decision=skip, reason={skip_reason if skip_reason else 'unknown_reason'}"
                            )

                    except Exception as e:
                        events_filtered += 1
                        # Safely extract event info for logging (event might not be a dict if JSON parsing failed)
                        tenant_id_info = "unknown"
                        object_info = "unknown"
                        try:
                            if isinstance(event, dict):
                                tenant_id_info = event.get('tenant_id', 'unknown')
                                object_info = event.get('object', 'unknown')
                        except Exception:
                            pass
                        log.error(
                            f"activity=event_processing, tenant_id={tenant_id_info}, object={object_info}, "
                            f"decision=error, reason=exception_during_event_processing, exception={str(e)}"
                        )
                        # On error, we skip the event (fail-safe behavior)
                        continue

            # Deduplication: Extract only the latest event per (object_id, sourcetype) combination
            # This prevents race conditions where multiple events for the same object in a single execution
            # would cause multiple updates (opened -> updated) in the backend
            events_yielded_records = []
            events_yielded = len(events_by_key)  # Count deduplicated events
            
            for dedup_key, (yield_event, event_time, context, prefilter_reason) in events_by_key.items():
                object_id, sourcetype = dedup_key
                
                # Load score and score_definition from component data via REST call
                tenant_id = context.get('tenant_id')
                component = context.get('component')
                
                # Check cache first to avoid redundant REST calls
                score = None
                score_definition = None
                tags = ""
                labels = ""
                if object_id in score_cache:
                    score, score_definition, tags, labels = score_cache[object_id]
                    log.debug(
                        f"activity=load_entity_data, tenant_id={tenant_id}, object_id={object_id}, "
                        f"decision=cache_hit, score={score}, tags={tags}, labels={labels}"
                    )
                elif tenant_id and component and object_id:
                    # Use the in-process DecisionMakerEngine instead of an HTTP
                    # roundtrip to /trackme/v2/component/load_component_data.
                    # The engine is constructed once per (tenant, component) at
                    # the top of stream() and amortized across every event for
                    # the same component — see _get_engine() above.
                    engine = _get_engine(component)
                    if engine is None:
                        # Engine load failed earlier — already logged.
                        # Cache None values to avoid redundant per-event work.
                        score_cache[object_id] = (None, None, "", "")
                    else:
                        try:
                            evaluated = engine.evaluate_object_full(object_id)

                            if evaluated is None:
                                # Record not found, or filtered out by the
                                # blocklist (engine surfaces both as None).
                                #
                                # Behavioural parity with the previous REST
                                # path: the load_component_data handler
                                # gates `processed_records.append(record)`
                                # behind the per-component append_record
                                # flag (trackme_rest_handler_component_user.py
                                # line 3278), so the response data array was
                                # empty for blocklisted keys too — and the
                                # previous code path here also fell into
                                # `score_cache[object_id] = (None, None, "", "")`
                                # in that case. No enrichment regression.
                                score_cache[object_id] = (None, None, "", "")
                                log.debug(
                                    f"activity=load_entity_data, tenant_id={tenant_id}, object_id={object_id}, "
                                    f"decision=cached_empty, reason=engine_returned_no_record, path=engine"
                                )
                            else:
                                # Extract score and score_definition
                                score_raw = evaluated.get("score")
                                score_definition = evaluated.get("score_definition")

                                # Convert score to integer (score is always an integer)
                                score = None
                                if score_raw is not None:
                                    try:
                                        score = int(float(score_raw))  # Convert to float first to handle string "100.0", then to int
                                    except (ValueError, TypeError):
                                        log.warning(
                                            f"activity=load_entity_data, tenant_id={tenant_id}, object_id={object_id}, "
                                            f"decision=error, reason=failed_to_convert_score_to_int, score_raw={score_raw}"
                                        )
                                        score = None

                                # Extract tags as a CSV string.
                                # Tags are stored as CSV in KVStore (e.g. "firewall,net").
                                # We keep the CSV string format here rather than converting
                                # to a Python list, because Splunk's GeneratingCommand serializes
                                # Python lists as multivalue fields (newline-separated), which
                                # breaks downstream comma-based parsing in the alert action.
                                tags_raw = evaluated.get("tags", "")
                                if isinstance(tags_raw, list):
                                    tags = ",".join(str(t) for t in tags_raw)
                                elif isinstance(tags_raw, str):
                                    tags = tags_raw
                                else:
                                    tags = ""

                                # Extract labels as a CSV string (same pattern as tags).
                                # Labels are resolved by dynamic_labels_lookup() as a sorted
                                # list of label name strings. Convert to CSV for the same
                                # reason as tags above.
                                labels_raw = evaluated.get("labels", "")
                                if isinstance(labels_raw, list):
                                    labels = ",".join(str(l) for l in labels_raw)
                                elif isinstance(labels_raw, str):
                                    labels = labels_raw
                                else:
                                    labels = ""

                                # Cache the results
                                score_cache[object_id] = (score, score_definition, tags, labels)

                                log.debug(
                                    f"activity=load_entity_data, tenant_id={tenant_id}, object_id={object_id}, "
                                    f"score={score}, tags={tags}, labels={labels}, decision=cached, path=engine"
                                )
                        except Exception as e:
                            log.warning(
                                f"activity=load_entity_data, tenant_id={tenant_id}, component={component}, object_id={object_id}, "
                                f"decision=error, reason=exception_during_engine_evaluation, exception={str(e)}"
                            )
                            # Cache None values to avoid repeated failed calls
                            score_cache[object_id] = (None, None, "", "")
                
                # Enrich yield_event with entity data from KVStore
                if score is not None:
                    yield_event["score"] = score
                if score_definition is not None:
                    yield_event["score_definition"] = score_definition
                if tags:
                    yield_event["tags"] = tags
                if labels:
                    yield_event["labels"] = labels
                
                events_yielded_records.append(yield_event)
                
                log.debug(
                    f"activity=deduplication, tenant_id={context.get('tenant_id')}, object={context.get('object')}, "
                    f"object_id={object_id}, sourcetype={sourcetype}, decision=final_yield, "
                    f"reason=latest_event_selected_for_object_sourcetype_combination, event_time={event_time}"
                )
            
            # Log deduplication summary if duplicates were found
            if len(events_by_key) < events_passed_filters:
                duplicates_removed = events_passed_filters - len(events_by_key)
                log.info(
                    f"activity=deduplication, tenant_id={self.tenant_id}, decision=completed, "
                    f"reason=duplicate_events_deduplicated, events_passed_filters={events_passed_filters}, "
                    f"events_after_dedup={len(events_by_key)}, duplicates_removed={duplicates_removed}"
                )

            # yield events (now deduplicated)
            for yield_record in generate_fields(events_yielded_records):
                yield yield_record

            search_run_time = round(time.time() - search_start_time, 3)
            log.info(
                f"activity=completion, tenant_id={self.tenant_id}, decision=terminated, "
                f"reason=trackmestateful_command_completed, run_time_seconds={round(time.time() - start, 3)}, "
                f"search_run_time_seconds={search_run_time}, "
                f"events_processed={events_processed}, events_yielded={events_yielded}, events_filtered={events_filtered}, "
                f"cache_stats=object_id_cache_size={len(object_id_cache)}, object_state_cache_size={len(object_state_cache)}, "
                f"stateful_record_cache_size={len(stateful_record_cache)}, validation_cache_size={len(validation_cache)}, "
                f"score_cache_size={len(score_cache)}"
            )

        except Exception as e:
            log.error(
                f"activity=execution, tenant_id={self.tenant_id}, decision=error, "
                f"reason=trackmestateful_command_failed, exception={str(e)}"
            )
            # Raise exception for main search failures - don't yield error events
            # Error events with missing required fields (object, object_category) would crash the downstream backend
            raise Exception(
                f"trackmestateful command failed for tenant_id={self.tenant_id}: {str(e)}"
            ) from e


dispatch(TrackMeStateful, sys.argv, sys.stdin, sys.stdout, __name__)
