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
import os
import sys
import time
import logging
import ast
import json
import re
import fnmatch
import operator

# Networking and URL handling imports
from urllib.parse import urlencode
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import trackme libs
from trackme_libs import run_splunk_search

# Import trackme libs logicalgroup
from trackme_libs_logicalgroup import (
    logical_group_update_green_red_members,
    normalize_logical_group_members,
)

# Import trackme libs utils
from trackme_libs_utils import strict_interpret_boolean, remove_leading_spaces

# Import trackme libs disruption queue
from trackme_libs_disruption_queue import (
    disruption_queue_lookup,
    disruption_queue_update,
    disruption_queue_get_duration,
)

# Import trackme libs splk flx
from trackme_libs_splk_flx import normalize_flx_tracker_name

# Import collections data for default values
from collections_data import vtenant_account_default

# Import score cache functions
from trackme_libs_scoring import read_score_cache

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def get_anomaly_reason_from_component_type(component_type):
    """
    Map score_definition component type to anomaly_reason value.
    
    Args:
        component_type: The type from score_definition.components (e.g., "future_tolerance_breach")
    
    Returns:
        The corresponding anomaly_reason value (e.g., "future_over_tolerance")
    """
    mapping = {
        "future_tolerance_breach": "future_over_tolerance",
        "data_sampling_anomaly": "data_sampling_anomaly",
        "delay_threshold_breach": "delay_threshold_breached",
        "variable_delay_threshold_breach": "variable_delay_threshold_breached",
        "lag_threshold_breach": "lag_threshold_breached",
        "latency_threshold_breach": "lag_threshold_breached",
        "min_hosts_dcount_breach": "min_hosts_dcount",
        "metric_alert": "metric_alert",
        "inactive": "inactive",
        "status_not_met": "status_not_met",
        "skipping_searches": "skipping_searches",
        "execution_errors": "execution_errors",
        "orphan_search": "orphan_search",
        "execution_delayed": "execution_delayed",
        "out_of_monitoring_times": "out_of_monitoring_times",
        "ml_outliers_detection": "ml_outliers_detection",
        "manual_score": "score_breached",
        "score_breached": "score_breached",
    }
    return mapping.get(component_type, component_type)


def apply_manual_score_without_anomaly_fallback(
    record,
    score_definition,
    total_score,
    score,
    status_message,
    anomaly_reason,
    object_state,
):
    """
    Populate status_message / anomaly_reason when a manual score influence pushes
    total_score > 0 without any actual anomaly being detected.

    Without this fallback, the entity ends up in a non-green state (orange / red)
    purely because of the manual score increase, yet status_message and
    anomaly_reason remain empty lists — which leaves the UI (and downstream
    consumers like stateful alerts) with no explanation for the state.

    This mutates status_message, anomaly_reason and score_definition in place and
    is a no-op when:
      - object_state is green (nothing to explain), or
      - the score_source does not contain "manual_score", or
      - total_score is not a positive value, or
      - anomaly_reason already carries at least one real reason (i.e. something
        other than "none").
    """
    if object_state == "green":
        return

    score_source = record.get("score_source", []) if isinstance(record, dict) else []
    if isinstance(score_source, list):
        score_source_list = score_source
    elif score_source:
        score_source_list = [score_source]
    else:
        score_source_list = []

    if "manual_score" not in score_source_list:
        return

    try:
        total_score_value = float(total_score) if total_score is not None else 0.0
    except (TypeError, ValueError):
        total_score_value = 0.0
    if total_score_value <= 0:
        return

    # Bail if the regular anomaly pipeline already produced a real reason
    if isinstance(anomaly_reason, list):
        real_reasons = [r for r in anomaly_reason if r and r != "none"]
        if real_reasons:
            return
        # Drop "none" so the fallback reason reads cleanly
        while "none" in anomaly_reason:
            try:
                anomaly_reason.remove("none")
            except ValueError:
                break

        if "score_breached" not in anomaly_reason:
            anomaly_reason.append("score_breached")

    try:
        base_score_value = float(score) if score is not None else 0.0
    except (TypeError, ValueError):
        base_score_value = 0.0

    if isinstance(status_message, list):
        status_message.append(
            f"Entity has an impact score of {total_score_value:.1f} "
            f"(base score: {base_score_value:.1f}) driven by a manual score influence "
            f"without any related anomaly detected. The current {object_state} state "
            f"reflects this manual override — review the score influence settings if "
            f"the state should be reconsidered."
        )

    # Ensure score_definition carries a manual_score component so the UI
    # drilldown remains consistent across all components (DSM already does this;
    # DHM / MHM / FLX / FQM / WLK historically did not).
    if isinstance(score_definition, dict):
        components = score_definition.get("components")
        if not isinstance(components, list):
            components = []
            score_definition["components"] = components
        already_present = any(
            isinstance(c, dict) and c.get("type") == "manual_score"
            for c in components
        )
        if not already_present:
            components.append({
                "type": "manual_score",
                "score": 0,
                "description": "Manual score influence applied without related anomaly",
            })


def get_impact_score(vtenant_account, field_name, default_value):
    """
    Helper function to get impact score from vtenant_account with fallback to default.
    
    Args:
        vtenant_account: Dictionary containing virtual tenant account configuration
        field_name: Name of the impact score field to retrieve
        default_value: Default value to use if field is not found
    
    Returns:
        Integer impact score value
    """
    if vtenant_account and isinstance(vtenant_account, dict):
        value = vtenant_account.get(field_name)
        if value is not None:
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
    # Fallback to vtenant_account_default if available
    default = vtenant_account_default.get(field_name, default_value)
    try:
        return int(default)
    except (ValueError, TypeError):
        return default_value


def get_entity_impact_score(record, component, score_type, vtenant_account, default_value):
    """
    Helper function to get impact score with entity-level override support.
    Checks entity-level impact_score_weights first, then falls back to tenant-level configuration.
    
    Args:
        record: Dictionary containing entity record data (may contain impact_score_weights)
        component: Component type ('dsm' or 'dhm')
        score_type: Score type ('delay' or 'latency')
        vtenant_account: Dictionary containing virtual tenant account configuration
        default_value: Default value to use if no override is found
    
    Returns:
        Integer impact score value
    """
    # First, check for entity-level custom impact score weights
    if record and isinstance(record, dict):
        impact_score_weights = record.get("impact_score_weights")
        if impact_score_weights:
            try:
                # Parse JSON if it's a string
                if isinstance(impact_score_weights, str):
                    weights_dict = json.loads(impact_score_weights)
                elif isinstance(impact_score_weights, dict):
                    weights_dict = impact_score_weights
                else:
                    weights_dict = None
                
                # Check if we have a custom weight for this score type
                if weights_dict and isinstance(weights_dict, dict):
                    custom_weight = weights_dict.get(score_type)
                    if custom_weight is not None:
                        try:
                            return int(custom_weight)
                        except (ValueError, TypeError):
                            pass
            except (json.JSONDecodeError, AttributeError, TypeError):
                # If parsing fails, fall through to tenant-level
                pass
    
    # Fall back to tenant-level configuration
    field_name = f"impact_score_{component}_{score_type}_threshold_breach"
    return get_impact_score(vtenant_account, field_name, default_value)


def parse_filters(query_parameters):
    filters = []
    for key, value in query_parameters.items():
        if "filter[" in key:
            parts = key.split("[")
            index = int(parts[1].split("]")[0])
            prop = parts[2].split("]")[0]

            # Initialize filter dict if it doesn't exist
            while len(filters) <= index:
                filters.append({})

            if "value" in key and len(parts) > 3:
                # Handle list values
                if "value" not in filters[index]:
                    filters[index]["value"] = []
                # Convert list index (e.g., filter[0][value][0]) to int and insert value
                list_index = int(parts[3].split("]")[0])
                # Ensure the list is long enough to hold this index
                while len(filters[index]["value"]) <= list_index:
                    filters[index]["value"].append(None)
                filters[index]["value"][list_index] = (
                    value.lower() if isinstance(value, str) else value
                )
            else:
                # Handle non-list values or the property itself
                filters[index][prop] = (
                    value.lower() if isinstance(value, str) else value
                )
    return filters


def record_matches_filter(record, filter):
    field = filter.get("field")
    filter_type = filter.get("type")
    value = filter.get("value")

    # Immediately return True if the filter value is empty
    if value == "":
        return True

    # Try to interpret the value as a JSON list if it looks like one
    if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass  # If decoding fails, proceed with the original value string

    # Prepare the record value for comparison
    record_value = record.get(field, "")
    if (
        isinstance(record_value, str)
        and "|" in record_value
        and field not in ["alias", "object"]
    ):
        # Treat as a pseudo list if record_value contains pipes
        record_value = [item.strip().lower() for item in record_value.split("|")]
    elif isinstance(record_value, str):
        record_value = record_value.strip().lower()

    if isinstance(value, str):
        value = value.strip().lower()

    # Handling for different filter types when record_value is a list
    if isinstance(record_value, list):
        if filter_type == "like":
            if isinstance(value, list):
                return any(v.lower() in item for item in record_value for v in value)
            else:
                return any(value in item for item in record_value)
        elif filter_type == "=":
            if isinstance(value, list):
                return any(item == v.lower() for item in record_value for v in value)
            else:
                return value in record_value
        # we can accept != as a filter
        elif filter_type == "!=":
            if isinstance(value, list):
                return any(item != v.lower() for item in record_value for v in value)
            else:
                return value not in record_value
        elif filter_type in ("<", "<=", ">", ">="):
            # Numerical comparisons for lists are more complex and context-dependent
            # You might want to reconsider how these should behave with list record_values
            return False
        elif filter_type == "in":
            if isinstance(value, list):
                return any(item in [v.lower() for v in value] for item in record_value)
            else:
                return value in record_value
        elif filter_type == "starts":
            return any(item.startswith(value) for item in record_value)
        elif filter_type == "ends":
            return any(item.endswith(value) for item in record_value)
        elif filter_type == "regex":
            return any(re.search(value, item) is not None for item in record_value)
    else:
        # Handling for different filter types when record_value is a string
        if filter_type == "like":
            return value in record_value
        elif filter_type == "=":
            return record_value == value
        # numerical comparison (except for != which is handled as a string comparison)
        elif filter_type in ("<", "<=", ">", ">=", "!="):
            # Handle numerical comparisons including "!="
            if filter_type == "!=":
                try:
                    # Attempt numerical comparison first
                    is_not_equal = float(record_value) != float(value)
                except ValueError:
                    # Fallback to string comparison
                    is_not_equal = record_value != value
                return is_not_equal
            else:
                try:
                    record_value = float(record_value)
                    value = float(value)
                except ValueError:
                    return False  # Skip filter if conversion fails
                # Directly evaluate the comparison expression
                return eval(f"record_value {filter_type} value")
        elif filter_type == "in":
            if isinstance(value, list):
                return record_value in [v.lower() for v in value]
            else:
                return record_value == value
        elif filter_type == "starts":
            return record_value.startswith(value)
        elif filter_type == "ends":
            return record_value.endswith(value)
        elif filter_type == "regex":
            return re.search(value, record_value) is not None

    return False


def pre_filter_records(data_records, query_parameters):
    """
    Pre-filters records based on a subset of filter fields: 'alias', 'object', 'monitored_state'.
    If other fields are present in the filters, returns all records without filtering.
    """
    filters = parse_filters(query_parameters)
    prefilter_fields = {"alias", "object", "monitored_state"}

    # Check if any filter exists outside the pre-defined fields for pre-filtering
    if any(f.get("field") not in prefilter_fields for f in filters):
        # If there are filters on fields outside the pre-filter scope, return all records
        return data_records

    # Proceed with pre-filtering if all filters fall within the pre-filter scope
    prefiltered_records = [
        record
        for record in data_records
        if all(record_matches_filter(record, f) for f in filters)
    ]

    return prefiltered_records


def filter_records(data_records, query_parameters):
    """
    Filters data records based on structured filters parsed from query parameters.
    """
    filters = parse_filters(query_parameters)

    if len(filters) > 0:
        get_effective_logger().debug(f'filters="{filters}"')

    # Apply filters to records, requiring all conditions to be met ('AND' logic)
    filtered_records = [
        record
        for record in data_records
        if all(record_matches_filter(record, f) for f in filters)
    ]

    return filtered_records


def convert_seconds_to_duration(seconds):
    """
    Define the function convert_seconds_to_duration
    behaviour: converts seconds to duration, duration is a string from as [D+]HH:MM:SS
    The first segment represents the number of days, the second the number of hours, third the number of minutes, and the fourth the number of seconds.
    """

    try:
        original_seconds = int(seconds)
    except ValueError:
        return 0

    # Check if the original seconds were negative
    is_negative = original_seconds < 0
    seconds = abs(original_seconds)

    # Calculate days, hours, minutes, and seconds
    days = seconds // (24 * 3600)
    seconds = seconds % (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    # Format the duration string
    if days > 0:
        duration = f"{days}+{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Add "-" if the original seconds were negative
    if is_negative:
        duration = "-" + duration

    return duration


def convert_epoch_to_datetime(epoch):
    """
    Define the function convert_epoch_to_datetime
    """

    # convert epoch to float
    try:
        epoch = float(epoch)
        # convert epoch to datetime
        datetime = time.strftime("%d %b %Y %H:%M", time.localtime(epoch))
        return datetime
    except Exception as e:
        epoch = 0
        return epoch


def get_monitoring_time_status(monitoring_time_policy, monitoring_time_rules):
    """
    Determine if an entity is currently under monitoring based on monitoring_time_policy and monitoring_time_rules.
    
    Arguments:
    - monitoring_time_policy: predefined policy name (string/list) or dictionary format
    - monitoring_time_rules: dictionary with week day keys (0-6) and hour lists as values
    
    Returns:
    - (isUnderMonitoring, anomaly_reason, status_message) tuple
      - isUnderMonitoring: True if entity is currently under monitoring, False otherwise
      - anomaly_reason: "out_of_monitoring_times" if not under monitoring, None otherwise
      - status_message: Human-readable message describing the monitoring status
    """
    
    try:
        import json
        
        # Helper function to convert day number to day name
        def get_day_name(day_no):
            day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            return day_names[day_no] if 0 <= day_no <= 6 else f"Day {day_no}"
        
        # Helper function to format time in human-readable format
        def format_time(hour_decimal):
            hour_int = int(hour_decimal)
            minutes = int((hour_decimal - hour_int) * 60)
            if minutes == 0:
                return f"{hour_int:02d}:00"
            else:
                return f"{hour_int:02d}:{minutes:02d}"
        
        # get current wday (0=Sunday, 6=Saturday)
        current_wday_no = int(time.strftime("%w"))
        current_day_name = get_day_name(current_wday_no)
        
        # get current hour and minute for precise checking
        current_hour = int(time.strftime("%H"))
        current_minute = int(time.strftime("%M"))
        current_hour_decimal = current_hour + (current_minute / 60.0)
        current_time_str = format_time(current_hour_decimal)
        
        # Priority: monitoring_time_rules > monitoring_time_policy > all_time
        
        # Check monitoring_time_rules first (takes precedence)
        if monitoring_time_rules is not None and monitoring_time_rules != "":
            try:
                # Parse if it's a string
                if isinstance(monitoring_time_rules, str):
                    rules_dict = json.loads(monitoring_time_rules)
                else:
                    rules_dict = monitoring_time_rules
                
                if isinstance(rules_dict, dict) and len(rules_dict) > 0:
                    # Check if current day is in the rules
                    day_key = str(current_wday_no)
                    if day_key in rules_dict:
                        hours_list = rules_dict[day_key]
                        if isinstance(hours_list, list) and len(hours_list) > 0:
                            # Check if current hour is in the list
                            for hour_val in hours_list:
                                try:
                                    hour_float = float(hour_val)
                                    # Check if current hour matches (within the hour range)
                                    if hour_float <= current_hour_decimal < hour_float + 1:
                                        return (
                                            True,
                                            None,
                                            f"This entity is currently under monitoring (custom rules: {current_day_name} {current_time_str})"
                                        )
                                except (ValueError, TypeError):
                                    continue
                    
                    # Current day/hour not in rules
                    return (
                        False,
                        "out_of_monitoring_times",
                        f"This entity is not currently under monitoring (custom rules: {current_day_name} {current_time_str} is not within the configured monitoring schedule)"
                    )
            except Exception as e:
                get_effective_logger().warning(f"Failed to parse monitoring_time_rules: {str(e)}, falling back to policy")
        
        # Check monitoring_time_policy
        if monitoring_time_policy is not None and monitoring_time_policy != "":
            try:
                # Parse if it's a string
                if isinstance(monitoring_time_policy, str):
                    # Try to parse as JSON first (might be dictionary)
                    try:
                        policy_dict = json.loads(monitoring_time_policy)
                    except (json.JSONDecodeError, ValueError):
                        # Not JSON, treat as predefined policy name
                        policy_dict = None
                        policy_name = monitoring_time_policy
                elif isinstance(monitoring_time_policy, list):
                    # List of policy names - use first one
                    policy_name = monitoring_time_policy[0] if len(monitoring_time_policy) > 0 else None
                    policy_dict = None
                elif isinstance(monitoring_time_policy, dict):
                    policy_dict = monitoring_time_policy
                    policy_name = None
                else:
                    policy_dict = None
                    policy_name = None
                
                # If dictionary format, use it like monitoring_time_rules
                if policy_dict is not None and isinstance(policy_dict, dict) and len(policy_dict) > 0:
                    day_key = str(current_wday_no)
                    if day_key in policy_dict:
                        hours_list = policy_dict[day_key]
                        if isinstance(hours_list, list) and len(hours_list) > 0:
                            for hour_val in hours_list:
                                try:
                                    hour_float = float(hour_val)
                                    if hour_float <= current_hour_decimal < hour_float + 1:
                                        return (
                                            True,
                                            None,
                                            f"This entity is currently under monitoring (custom policy: {current_day_name} {current_time_str})"
                                        )
                                except (ValueError, TypeError):
                                    continue
                    return (
                        False,
                        "out_of_monitoring_times",
                        f"This entity is not currently under monitoring (custom policy: {current_day_name} {current_time_str} is not within the configured monitoring schedule)"
                    )
                
                # Map predefined policy names to day+hour rules
                if policy_name:
                    if policy_name == "all_time":
                        return (True, None, "This entity is currently under monitoring (all_time policy)")
                    
                    elif policy_name == "business_days_all_hours":
                        # Monday-Friday (1-5), all hours
                        if current_wday_no in [1, 2, 3, 4, 5]:
                            return (True, None, f"This entity is currently under monitoring (business_days_all_hours policy: {current_day_name})")
                        else:
                            return (
                                False,
                                "out_of_monitoring_times",
                                f"This entity is not currently under monitoring (business_days_all_hours policy: {current_day_name} is not a business day)"
                            )
                    
                    elif policy_name == "monday_saturday_all_hours":
                        # Monday-Saturday (1-6), all hours
                        if current_wday_no in [1, 2, 3, 4, 5, 6]:
                            return (True, None, f"This entity is currently under monitoring (monday_saturday_all_hours policy: {current_day_name})")
                        else:
                            return (
                                False,
                                "out_of_monitoring_times",
                                f"This entity is not currently under monitoring (monday_saturday_all_hours policy: {current_day_name} is not within Monday-Saturday)"
                            )
                    
                    elif policy_name == "business_days_08h_20h":
                        # Monday-Friday (1-5), 8:00-20:00
                        if current_wday_no in [1, 2, 3, 4, 5]:
                            if 8 <= current_hour < 20:
                                return (True, None, f"This entity is currently under monitoring (business_days_08h_20h policy: {current_day_name} {current_time_str})")
                            else:
                                return (
                                    False,
                                    "out_of_monitoring_times",
                                    f"This entity is not currently under monitoring (business_days_08h_20h policy: {current_day_name} {current_time_str} is outside 08:00-20:00 range)"
                                )
                        else:
                            return (
                                False,
                                "out_of_monitoring_times",
                                f"This entity is not currently under monitoring (business_days_08h_20h policy: {current_day_name} is not a business day)"
                            )
                    
                    elif policy_name == "monday_saturday_08h_20h":
                        # Monday-Saturday (1-6), 8:00-20:00
                        if current_wday_no in [1, 2, 3, 4, 5, 6]:
                            if 8 <= current_hour < 20:
                                return (True, None, f"This entity is currently under monitoring (monday_saturday_08h_20h policy: {current_day_name} {current_time_str})")
                            else:
                                return (
                                    False,
                                    "out_of_monitoring_times",
                                    f"This entity is not currently under monitoring (monday_saturday_08h_20h policy: {current_day_name} {current_time_str} is outside 08:00-20:00 range)"
                                )
                        else:
                            return (
                                False,
                                "out_of_monitoring_times",
                                f"This entity is not currently under monitoring (monday_saturday_08h_20h policy: {current_day_name} is not within Monday-Saturday)"
                            )
            except Exception as e:
                get_effective_logger().warning(f"Failed to parse monitoring_time_policy: {str(e)}, falling back to all_time")
        
        # Final fallback: all_time (monitor always)
        return (True, None, "This entity is currently under monitoring (all_time policy)")
    
    except Exception as e:
        get_effective_logger().error(f"get_monitoring_time_status function has failed, exception={str(e)}")
        # Fallback to all_time on error
        return (True, None, f"Monitoring time status check failed: {str(e)}, defaulting to all_time monitoring")


def get_outliers_status(isOutlier, OutliersDisabled, tenant_outliers_set_state=None, score_outliers=None):
    """
    Create a function called get_outliers_status:
    - arguments: isOutlier, OutliersDisabled, tenant_outliers_set_state (deprecated, kept for backward compatibility), score_outliers
    - tenant_outliers_set_state: Deprecated - no longer used with score-based approach. Kept for backward compatibility.
    - score_outliers: The score_outliers value from calculate_score (optional, for hybrid scoring)
    - behaviour: alter isOutlier, 0=not outlier, 1=outlier (can turn red), 2=outlier but disabled/score too low
    - With score-based approach, score_outliers controls whether outliers can turn entities red (score >= 100)
    """

    if OutliersDisabled == 1:
        isOutlier = 0
    else:
        if isOutlier == 1:
            # Score-based approach: if score_outliers is provided and < 100, don't allow outlier to turn red
            if score_outliers is not None:
                if score_outliers >= 100:
                    isOutlier = 1  # Allow outlier status to turn entity red
                else:
                    isOutlier = 2  # Report outlier but don't allow it to turn entity red
            else:
                isOutlier = 1  # Legacy behavior: allow outlier status if score not available
        else:
            isOutlier = 0

    return isOutlier


def get_data_sampling_status(
    data_sample_status_colour, data_sample_feature, tenant_data_sampling_set_state=None
):
    """
    Create a function called get_data_sampling_status:
    - arguments: data_sample_status_colour, data_sample_feature, tenant_data_sampling_set_state (deprecated, kept for backward compatibility)
    - tenant_data_sampling_set_state: Deprecated - no longer used with score-based approach. Kept for backward compatibility.
    - behaviour: alter isAnomaly, 0=not anomaly, 1=anomaly, 2=anomaly but disabled at tenant level
    - With score-based approach, the impact score controls whether sampling anomalies affect entity status
    """

    # if disabled at entity level, them isAnomaly is 0
    if data_sample_feature == "disabled":
        isAnomaly = 0

    if data_sample_status_colour == "green":
        isAnomaly = 0
    elif data_sample_status_colour == "red":
        # With score-based approach, score controls the impact, so always allow anomaly
        # The score will determine if entity turns red (score >= 100)
        isAnomaly = 1
    else:
        isAnomaly = 0

    return isAnomaly


def get_future_status(
    future_tolerance,
    system_future_tolerance,
    data_last_lag_seen,
    data_last_ingestion_lag_seen,
    data_last_time_seen,
    data_last_ingest,
):
    """
    Create a function called get_future_status:
    - arguments: future_tolerance (expressed in seconds), system_future_tolerance (expressed in seconds), data_last_lag_seen (expressed in seconds)
    - behaviour: returns a boolean, True if data_last_lag_seen is lower than future_tolerance, False otherwise. If future_tolerance is 0, rely on system_future_tolerance
    """

    isFuture = False
    isFutureMsg = ""
    if future_tolerance == 0:
        future_tolerance = system_future_tolerance

    # convert all to int
    try:
        future_tolerance = int(round(float(future_tolerance), 0))
        data_last_lag_seen = int(round(float(data_last_lag_seen), 0))
        data_last_ingestion_lag_seen = int(
            round(float(data_last_ingestion_lag_seen), 0)
        )
    except:
        pass

    get_effective_logger().debug(
        f"data_last_lag_seen={data_last_lag_seen}, system_future_tolerance={system_future_tolerance}, future_tolerance={future_tolerance}"
    )

    if float(data_last_lag_seen) < float(future_tolerance) or float(
        data_last_ingestion_lag_seen
    ) < float(future_tolerance):
        isFuture = True

        # convert data_last_lag_seen to duration
        data_last_lag_seen_duration = convert_seconds_to_duration(data_last_lag_seen)

        # convert data_last_ingestion_lag_seen to duration
        data_last_ingestion_lag_seen_duration = convert_seconds_to_duration(
            data_last_ingestion_lag_seen
        )

        # convert data_last_time_seen to %c
        data_last_time_seen_datetime = convert_epoch_to_datetime(data_last_time_seen)

        # convert data_last_ingest to %c
        data_last_ingest_datetime = convert_epoch_to_datetime(data_last_ingest)

        isFutureMsg = f"""detected data indexed in the future which is most likely due to timestamping misconfiguration, timezone or time synchronization issue. Event delay is {data_last_lag_seen} seconds (duration: {data_last_lag_seen_duration}), Event latency is {data_last_ingestion_lag_seen} seconds (duration: {data_last_ingestion_lag_seen_duration}), this is beyond current tolerance threshold of {future_tolerance} seconds, latest event available (_time) for this entity: {data_last_time_seen_datetime}, latest event ingested for this entity: {data_last_ingest_datetime}. Review and fix the root cause, or adapt the future tolerance at the system level or for this entity especially."""

    else:
        isFuture = False

    return isFuture, isFutureMsg, future_tolerance


def get_future_metrics_status(
    system_future_tolerance,
    metric_last_time_seen,
):
    """
    Create a function called get_future_metrics_status:
    - arguments: future_tolerance (expressed in seconds), system_future_tolerance (expressed in seconds), data_last_lag_seen (expressed in seconds)
    - behaviour: returns a boolean, True if metric_last_time_seen is lower than system_future_tolerance, False otherwise.
    """

    isFuture = False
    isFutureMsg = ""

    get_effective_logger().debug(
        f"metric_last_time_seen={metric_last_time_seen}, system_future_tolerance={system_future_tolerance}"
    )

    if float(metric_last_time_seen) < float(system_future_tolerance):
        isFuture = True
        # convert data_last_lag_seen to duration
        metric_last_time_seen_duration = convert_seconds_to_duration(
            metric_last_time_seen
        )
        # convert data_last_time_seen to %c
        metric_last_time_seen_datetime = convert_epoch_to_datetime(
            metric_last_time_seen
        )

        isFutureMsg = f"""detected metrics indexed in the future which is most likely due to timestamping misconfiguration, timezone or time synchronization issue. Metric delay is {metric_last_time_seen} seconds (duration: {metric_last_time_seen_duration}) which is beyond tolerance threshold of {system_future_tolerance}, latest event available (_time) for this entity: {metric_last_time_seen_datetime}. Review and fix the root cause, or adapt the future tolerance at the system level or for this entity especially"""
    else:
        isFuture = False

    return isFuture, isFutureMsg


def get_is_under_dcount_host(min_dcount_host, min_dcount_threshold, min_dcount_field):
    """
    Create a function call get_is_under_dcount_host:
    - arguments: min_dcount_host, min_dcount_threshold
    - returns: isUnderDcountHost (boolean), isUnderDcountHostMsg (string)
    - behaviour: returns a boolean, True if min_dcount_threshold is a numerical and is lower than min_dcount_host, False otherwise
    """

    if isinstance(min_dcount_host, float) and min_dcount_threshold < min_dcount_host:
        isUnderDcountHost = True
        isUnderDcountHostMsg = f"""Monitoring conditions are not met due to low number of hosts. Number of hosts is {int(min_dcount_threshold)} based on the metric {min_dcount_field} which is lower than the minimum required number of hosts of {int(min_dcount_host)}"""
    else:
        isUnderDcountHost = False
        isUnderDcountHostMsg = ""

    return isUnderDcountHost, isUnderDcountHostMsg


def get_logical_groups_collection_records(collection):
    """
    Queries and processes records from a collection based on specific criteria.

    :param collection: The collection object to query.
    :return: Tuple containing collection records and a dictionary of records.
    """

    collection_records = []
    collection_records_dict = {}
    count_to_process_list = []
    collection_members_list = []
    collection_members_dict = {}

    end = False
    skip_tracker = 0
    while not end:
        process_collection_records = collection.data.query(skip=skip_tracker)
        if process_collection_records:
            for item in process_collection_records:
                collection_records.append(item)
                object_group_members = normalize_logical_group_members(
                    item.get("object_group_members", [])
                )
                object_group_members_green = normalize_logical_group_members(
                    item.get("object_group_members_green", [])
                )
                object_group_members_red = normalize_logical_group_members(
                    item.get("object_group_members_red", [])
                )
                collection_records_dict[item.get("_key")] = {
                    "object_group_name": item.get("object_group_name"),
                    "object_group_mtime": item.get("object_group_mtime"),
                    "object_group_members": object_group_members,
                    "object_group_members_green": object_group_members_green,
                    "object_group_members_red": object_group_members_red,
                    "object_group_min_green_percent": item.get(
                        "object_group_min_green_percent", 0
                    ),
                }

                try:

                    logicalgroup_members = object_group_members
                    # add members in collection_members_list, also create a dict per member
                    for member in logicalgroup_members:
                        if member not in collection_members_list:
                            collection_members_list.append(member)
                            collection_members_dict[member] = {
                                "object_group_key": item.get("_key"),
                                "object_group_name": item.get("object_group_name"),
                                "object_group_members": object_group_members,
                                "object_group_members_green": object_group_members_green,
                                "object_group_members_red": object_group_members_red,
                                "object_group_min_green_percent": item.get(
                                    "object_group_min_green_percent", 0
                                ),
                            }

                except Exception as e:
                    get_effective_logger().error(
                        f"function get_logical_groups_collection_records, error while processing logical group members, exception={str(e)}"
                    )

                count_to_process_list.append(item.get("_key"))
            skip_tracker += len(process_collection_records)
        else:
            end = True

    return (
        collection_records,
        collection_records_dict,
        collection_members_list,
        collection_members_dict,
        count_to_process_list,
    )


def get_and_manage_logical_group_status(
    splunkd_uri,
    session_key,
    tenant_id,
    object_name,
    object_state,
    object_group_key,
    object_logical_group_dict,
):
    """
    Create a function called get_and_manage_logical_group_status:
    - arguments: object_name, object_state, object_group_key, object_logical_group_dict
    - returns: isUnderLogicalGroup (boolean), LogicalGroupStateInAlert (boolean), LogicalGroupMsg (string)
    - behaviour:
        isUnderLogicalGroup: True if object_group_key is not empty and object_group_members_count is higher than 1
        LogicalGroupStateInAlert: True if object_group_green_percent is lower than object_group_min_green_percent
        LogicalGroupMsg: string containing the status of the logical group
    """

    # object_group_members_count
    object_group_members_count = 0

    # get logical group name
    object_group_name = object_logical_group_dict.get("object_group_name", "")

    try:

        # enter if the group is not empty
        if object_group_name != "":
            object_group_min_green_percent = object_logical_group_dict.get(
                "object_group_min_green_percent", 0
            )

            object_group_members = normalize_logical_group_members(
                object_logical_group_dict.get("object_group_members", [])
            )
            object_group_members_green = normalize_logical_group_members(
                object_logical_group_dict.get("object_group_members_green", [])
            )
            object_group_members_red = normalize_logical_group_members(
                object_logical_group_dict.get("object_group_members_red", [])
            )

            object_group_members_count = len(object_group_members)

            # if object_state is green, object_name must be in object_group_members_green but not in object_group_members_red
            # if object_state is red or blue, object_name must be in object_group_members_red but not in object_group_members_green
            # any change required to object_group_members_green and object_group_members_red implies an update to the KVstore record is required, set the boolean uppdate_kvstore_record to True if required

            update_kvstore_record = False

            if object_state == "green":
                if object_name not in object_group_members_green:
                    object_group_members_green.append(object_name)
                    update_kvstore_record = True
                if object_name in object_group_members_red:
                    object_group_members_red.remove(object_name)
                    update_kvstore_record = True
            else:
                if object_name not in object_group_members_red:
                    object_group_members_red.append(object_name)
                    update_kvstore_record = True
                if object_name in object_group_members_green:
                    object_group_members_green.remove(object_name)
                    update_kvstore_record = True

            # if update_kvstore_record is True, call the API endpoint accordingly
            if update_kvstore_record:
                # proceed
                try:
                    response = logical_group_update_green_red_members(
                        splunkd_uri,
                        session_key,
                        tenant_id,
                        object_name,
                        object_group_key,
                        object_group_members_green,
                        object_group_members_red,
                    )
                    get_effective_logger().info(
                        f'tenant="{tenant_id}", object="{object_name}", logical group green/red members update API was successful, response="{response}"'
                    )

                except Exception as e:
                    get_effective_logger().error(
                        f'tenant="{tenant_id}", object="{object_name}", logical group green/red members update API call has failed, exception="{str(e)}"'
                    )

            # ensure object_group_min_green_percent is float
            try:
                object_group_min_green_percent = float(object_group_min_green_percent)
            except:
                object_group_min_green_percent = 0

            # calculate object_group_green_percent, if logical group is empty, then object_group_green_percent is 100
            try:
                if object_group_members_count > 0:
                    object_group_green_percent = (
                        len(object_group_members_green) / object_group_members_count
                    ) * 100
                else:
                    object_group_green_percent = 100
            except:
                object_group_green_percent = 0

        # define status and return

        if object_group_key != "" and object_group_members_count > 1:
            isUnderLogicalGroup = True
            if object_group_green_percent < object_group_min_green_percent:
                LogicalGroupStateInAlert = True
                LogicalGroupMsg = f"""Logical Group {object_group_name} with key="{object_group_key}" is in alert state. The current green percentage of the group is {round(object_group_green_percent, 2)}% which is lower than the minimum green percentage of {round(object_group_min_green_percent, 2)}%, object_group_members_count={object_group_members_count}, object_group_members_red={object_group_members_red}"""

            else:
                LogicalGroupStateInAlert = False
                LogicalGroupMsg = f"""Logical Group {object_group_name} with key="{object_group_key}" is in normal state. The current green percentage of the group is {round(object_group_green_percent, 2)}% which is higher or equal to the minimal green percentage of {round(object_group_min_green_percent, 2)}%, object_group_members_count={object_group_members_count}, object_group_members_red={object_group_members_red}"""

        else:
            isUnderLogicalGroup = False
            LogicalGroupStateInAlert = False
            LogicalGroupMsg = ""

        return isUnderLogicalGroup, LogicalGroupStateInAlert, LogicalGroupMsg

    except Exception as e:
        get_effective_logger().error(
            f'function get_and_manage_logical_group_status has failed, exception="{str(e)}", object_name="{object_name}", object_group_key="{object_group_key}", object_logical_group_dict="{object_logical_group_dict}"'
        )
        return (
            False,
            False,
            f'function get_and_manage_logical_group_status has failed, exception="{str(e)}", object_name="{object_name}", object_group_key="{object_group_key}"',
        )


def get_dsm_latency_status(
    data_last_ingestion_lag_seen,
    data_max_lag_allowed,
    data_last_ingest,
    data_last_time_seen,
):
    """
    Create a function called get_dsm_latency_status:
    - arguments: data_last_ingestion_lag_seen, data_max_lag_allowed, data_last_ingest, data_last_time_seen
    - returns: isUnderLatencyAlert (boolean), isUnderLatencyMessage (string)
    - behaviour:
        isUnderLatencyAlert: If data_last_ingestion_lag_seen is higher than data_max_lag_allowed, then isUnderLatencyAlert is True
        isUnderLatencyMessage: If isUnderLatencyAlert is True:
        "Monitoring conditions are not met due to latency issues. Ingestion latency is $data_last_ingestion_lag_seen$ seconds (duration: <conversion of data_last_ingestion_lag_seen to duration), which is higher than the maximum allowed latency of $data_max_lag_allowed$ seconds (duration: <conversion of data_max_lag_allowed to duration>), latest event available for this entity: <conversion of epoch data_last_time_seen to %c>, latest event ingested for this entity: <conversion of epoch data_last_ingest to %c>"
        isUnderLatencyMessage: If isUnderLatencyAlert is False:
        "Monitoring conditions are not met for ingest latency are met. Ingestion latency is $data_last_ingestion_lag_seen$ seconds (duration: <conversion of data_last_ingestion_lag_seen to duration), which is lower than the maximum allowed latency of $data_max_lag_allowed$ seconds (duration: <conversion of data_max_lag_allowed to duration>), latest event available for this entity: <conversion of epoch data_last_time_seen to %c>, latest event ingested for this entity: <conversion of epoch data_last_ingest to %c>"
    """

    # convert data_last_ingestion_lag_seen to float
    try:
        data_last_ingestion_lag_seen = float(data_last_ingestion_lag_seen)
    except:
        data_last_ingestion_lag_seen = 0

    # convert data_max_lag_allowed to float
    try:
        data_max_lag_allowed = float(data_max_lag_allowed)
    except:
        data_max_lag_allowed = 0

    # convert data_last_ingest to float
    try:
        data_last_ingest = float(data_last_ingest)
    except:
        data_last_ingest = 0

    # convert data_last_time_seen to float
    try:
        data_last_time_seen = float(data_last_time_seen)
    except:
        data_last_time_seen = 0

    # convert data_last_ingestion_lag_seen to duration
    data_last_ingestion_lag_seen_duration = convert_seconds_to_duration(
        data_last_ingestion_lag_seen
    )

    # convert data_max_lag_allowed to duration
    data_max_lag_allowed_duration = convert_seconds_to_duration(data_max_lag_allowed)

    # convert data_last_ingest to %c
    data_last_ingest_datetime = convert_epoch_to_datetime(data_last_ingest)

    # calculate the time since last ingestion in seconds
    time_since_last_ingestion = time.time() - data_last_ingest

    # convert data_last_time_seen to %c
    data_last_time_seen_datetime = convert_epoch_to_datetime(data_last_time_seen)

    # calculate the time since last event in seconds
    time_since_last_event = time.time() - data_last_time_seen

    # define isUnderLatencyAlert
    if float(data_last_ingestion_lag_seen) > float(data_max_lag_allowed):
        isUnderLatencyAlert = True
    else:
        isUnderLatencyAlert = False

    # define isUnderLatencyMessage
    if isUnderLatencyAlert:

        # if the time since last ingestion and the time since last event are less than data_max_lag_allowed, then indicate that might be receiving a mix of delayed and non-delayed events
        if (
            time_since_last_ingestion < data_max_lag_allowed
            and time_since_last_event < data_max_lag_allowed
        ):
            isUnderLatencyMessage = f"""Monitoring conditions are not met due to latency issues. Ingestion latency is approximately {round(float(data_last_ingestion_lag_seen), 3)} seconds (duration: {data_last_ingestion_lag_seen_duration}), which is higher than the maximum allowed latency of {int(data_max_lag_allowed)} seconds (duration: {data_max_lag_allowed_duration}), latest event available (_time) for this entity: {data_last_time_seen_datetime}, latest event indexed (_indextime) for this entity: {data_last_ingest_datetime}, this indicates that the source might be receiving a mix of delayed and non-delayed events"""
        else:
            isUnderLatencyMessage = f"""Monitoring conditions are not met due to latency issues. Ingestion latency is approximately {round(float(data_last_ingestion_lag_seen), 3)} seconds (duration: {data_last_ingestion_lag_seen_duration}), which is higher than the maximum allowed latency of {int(data_max_lag_allowed)} seconds (duration: {data_max_lag_allowed_duration}), latest event available (_time) for this entity: {data_last_time_seen_datetime}, latest event indexed (_indextime) for this entity: {data_last_ingest_datetime}, this indicates that the source is receiving delayed events only"""

    else:
        isUnderLatencyMessage = f"""monitoring conditions for ingest latency are met. Ingestion latency is approximately {round(float(data_last_ingestion_lag_seen), 3)} seconds (duration: {data_last_ingestion_lag_seen_duration}), which is lower than the maximum allowed latency of {int(data_max_lag_allowed)} seconds (duration: {data_max_lag_allowed_duration}), latest event indexed (_indextime) for this entity: {data_last_ingest_datetime}"""

    # return
    return isUnderLatencyAlert, isUnderLatencyMessage


def resolve_variable_delay_threshold(entity_record, variable_delay_record, current_time=None):
    """
    Resolve the effective delay threshold for an entity based on variable delay policy.

    Arguments:
        entity_record: dict - The entity record from the main KVstore collection
        variable_delay_record: dict or None - The variable delay record from the variable delay collection
        current_time: datetime or None - Override for current time (for testing). Defaults to now().

    Returns:
        tuple: (effective_threshold: float, slot_name: str or None, is_variable: bool)
            - effective_threshold: the delay threshold to use (in seconds)
            - slot_name: the name of the active slot, or None if static
            - is_variable: True if variable delay is active, False otherwise
    """

    from datetime import datetime as dt

    # If variable delay is not enabled, return the static threshold
    variable_delay_policy = entity_record.get("variable_delay_policy", "static")
    if variable_delay_policy != "variable" or variable_delay_record is None:
        return (float(entity_record.get("data_max_delay_allowed", 3600)), None, False)

    # Check if variable delay is enabled in the record
    variable_delay_enabled = variable_delay_record.get("variable_delay_enabled", "false")
    if variable_delay_enabled != "true":
        return (float(entity_record.get("data_max_delay_allowed", 3600)), None, False)

    # Get current time
    if current_time is None:
        current_time = dt.now()

    current_day = current_time.weekday()  # 0=Monday, 6=Sunday
    current_hour = current_time.hour

    # Parse slots
    try:
        slots_config = json.loads(variable_delay_record.get("variable_delay_slots", "{}"))
        slots = slots_config.get("slots", [])
    except (json.JSONDecodeError, TypeError):
        # Fallback to static threshold on parse error
        get_effective_logger().warning(
            f'resolve_variable_delay_threshold: failed to parse variable_delay_slots for entity="{entity_record.get("object", "unknown")}", falling back to static threshold'
        )
        return (float(entity_record.get("data_max_delay_allowed", 3600)), None, False)

    # Evaluate slots in order - first match wins
    for slot in slots:
        days = slot.get("days", [])
        hours = slot.get("hours", [])
        if current_day in days and current_hour in hours:
            threshold = float(slot.get("max_delay_allowed", 3600))
            slot_name = slot.get("slot_name", "unnamed")
            return (threshold, slot_name, True)

    # No slot matched - use the default fallback
    default_threshold = float(
        variable_delay_record.get(
            "variable_delay_default",
            entity_record.get("data_max_delay_allowed", 3600),
        )
    )
    return (default_threshold, "_default", True)


# Lagging class matching constants
_MATCH_MODE_RANK = {"exact": 0, "wildcard": 1, "regex": 2}


def match_lagging_class_pattern(entity_value, pattern, match_mode):
    """
    Match an entity value against a lagging class pattern using the specified mode.

    Arguments:
        entity_value: str - The entity value to match (e.g., index name, sourcetype, priority)
        pattern: str - The pattern from the lagging class definition
        match_mode: str - "exact", "wildcard", or "regex"

    Returns:
        bool - True if the entity value matches the pattern
    """
    if not entity_value or not pattern:
        return False

    if match_mode == "exact":
        return entity_value == pattern
    elif match_mode == "wildcard":
        return fnmatch.fnmatch(entity_value, pattern)
    elif match_mode == "regex":
        try:
            return bool(re.fullmatch(pattern, entity_value))
        except re.error:
            return False
    return False


def resolve_lagging_class_threshold(entity_record, lagging_classes_records, current_time=None):
    """
    Resolve lagging class threshold for an entity by matching against lagging class policies.

    Matching follows this priority:
    1. If data_override_lagging_class == "true", skip (entity overrides lagging classes)
    2. Match by level in order: index > sourcetype > priority (first level with a match wins)
    3. Within a level, specificity ordering: exact > wildcard > regex, then by ctime (oldest first)
    4. For multi-value fields (comma-separated), match if ANY individual value matches

    Arguments:
        entity_record: dict - The entity record from the main KVstore collection
        lagging_classes_records: list - All lagging class records for this component
        current_time: datetime or None - Override for current time (for variable delay slot resolution)

    Returns:
        tuple: (matched, override_lag, override_delay, delay_mode, resolved_delay_threshold, active_slot_name, matched_class_info)
            - matched: bool - whether a lagging class matched this entity
            - override_lag: float or None - latency threshold override (None = don't override)
            - override_delay: float or None - static delay threshold (when delay_mode="static")
            - delay_mode: str or None - "static" or "variable"
            - resolved_delay_threshold: float or None - effective delay threshold (resolves variable slots at current time)
            - active_slot_name: str or None - variable delay slot name if applicable
            - matched_class_info: dict or None - info about the matched class for logging/debugging
    """

    from datetime import datetime as dt

    # Check if entity overrides lagging classes
    if entity_record.get("data_override_lagging_class") == "true":
        return (False, None, None, None, None, None, None)

    # If no lagging classes defined, return immediately
    if not lagging_classes_records:
        return (False, None, None, None, None, None, None)

    # Extract entity matchable values
    data_index = entity_record.get("data_index", "")
    data_sourcetype = entity_record.get("data_sourcetype", "")
    priority = entity_record.get("priority", "")

    # Define the level-to-value mapping
    level_value_map = [
        ("index", data_index),
        ("sourcetype", data_sourcetype),
        ("priority", priority),
    ]

    # Try matching in level order: index > sourcetype > priority
    for level, entity_value_raw in level_value_map:

        if not entity_value_raw:
            continue

        # Handle multi-value fields (comma-separated, common in DHM)
        if isinstance(entity_value_raw, str) and "," in entity_value_raw:
            entity_values = [v.strip() for v in entity_value_raw.split(",") if v.strip()]
        else:
            entity_values = [str(entity_value_raw).strip()] if entity_value_raw else []

        if not entity_values:
            continue

        # Find all classes at this level that match any entity value
        matches = []
        for cls in lagging_classes_records:
            if cls.get("level") != level:
                continue

            cls_name = cls.get("name", "")
            cls_match_mode = cls.get("match_mode", "exact")

            # Check if any entity value matches
            for ev in entity_values:
                if match_lagging_class_pattern(ev, cls_name, cls_match_mode):
                    matches.append(cls)
                    break  # one match is enough for this class

        if not matches:
            continue

        # Sort by specificity: exact > wildcard > regex, then by ctime (oldest first)
        matches.sort(
            key=lambda c: (
                _MATCH_MODE_RANK.get(c.get("match_mode", "exact"), 99),
                float(c.get("ctime") or 0),
            )
        )
        best_match = matches[0]

        # Resolve thresholds from the best match

        # Optional latency threshold
        value_lag_raw = best_match.get("value_lag", "")
        override_lag = None
        if value_lag_raw and str(value_lag_raw).strip():
            try:
                override_lag = float(value_lag_raw)
            except (ValueError, TypeError):
                override_lag = None

        # Delay configuration
        delay_mode = best_match.get("delay_mode", "static")

        matched_class_info = {
            "name": best_match.get("name"),
            "level": level,
            "_key": best_match.get("_key"),
            "match_mode": best_match.get("match_mode", "exact"),
            "delay_mode": delay_mode,
        }

        if delay_mode == "variable":
            # Resolve variable delay from the class's slots
            if current_time is None:
                current_time = dt.now()

            current_day = current_time.weekday()  # 0=Monday, 6=Sunday
            current_hour = current_time.hour

            # Parse slots
            try:
                slots_raw = best_match.get("variable_delay_slots", "{}")
                slots_config = json.loads(slots_raw) if isinstance(slots_raw, str) else slots_raw
                slots = slots_config.get("slots", []) if isinstance(slots_config, dict) else []
            except (json.JSONDecodeError, TypeError):
                get_effective_logger().warning(
                    f'resolve_lagging_class_threshold: failed to parse variable_delay_slots for class="{best_match.get("name", "unknown")}", falling back to variable_delay_default'
                )
                slots = []

            # Evaluate slots in order - first match wins
            for slot in slots:
                days = slot.get("days", [])
                hours = slot.get("hours", [])
                if current_day in days and current_hour in hours:
                    try:
                        threshold = float(slot.get("max_delay_allowed", 3600))
                    except (ValueError, TypeError):
                        threshold = 3600
                    slot_name = slot.get("slot_name", "unnamed")
                    return (True, override_lag, None, "variable", threshold, slot_name, matched_class_info)

            # No slot matched - use variable_delay_default
            try:
                default_delay = float(best_match.get("variable_delay_default", 3600))
            except (ValueError, TypeError):
                default_delay = 3600
            return (True, override_lag, None, "variable", default_delay, "_default", matched_class_info)

        else:
            # Static delay
            try:
                override_delay = float(best_match.get("value_delay", 0))
            except (ValueError, TypeError):
                override_delay = None
            return (True, override_lag, override_delay, "static", override_delay, None, matched_class_info)

    # No match found at any level
    return (False, None, None, None, None, None, None)


def resolve_variable_threshold_value(threshold_record, current_time=None):
    """
    Resolve the effective threshold value based on variable threshold configuration.

    For FLX thresholds, each threshold rule can optionally have time-based variable values
    that change based on day-of-week and hour-of-day.

    Arguments:
        threshold_record: dict - A single threshold record from the thresholds collection
        current_time: datetime or None - Override for current time (for testing). Defaults to now().

    Returns:
        tuple: (effective_value, slot_name: str or None, is_variable: bool)
            - effective_value: the threshold value to use (numeric, as stored in the slot or static value)
            - slot_name: the name of the active slot, or None if static
            - is_variable: True if variable threshold is active, False otherwise
    """

    from datetime import datetime as dt

    # If variable threshold is not enabled, return the static value
    variable_threshold_enabled = str(threshold_record.get("variable_threshold_enabled", "false")).lower()
    if variable_threshold_enabled != "true":
        return (threshold_record.get("value"), None, False)

    # Get current time
    if current_time is None:
        current_time = dt.now()

    current_day = current_time.weekday()  # 0=Monday, 6=Sunday
    current_hour = current_time.hour

    # Parse slots — handle None/missing slots gracefully by using default fallback
    raw_slots = threshold_record.get("variable_threshold_slots")
    if raw_slots is None:
        # No slots configured — skip to default fallback (don't treat as error)
        slots = []
    else:
        try:
            slots_config = json.loads(raw_slots)
            # slots_config must be a dict with a "slots" key; if it's a list or other type, fall back
            if not isinstance(slots_config, dict):
                get_effective_logger().warning(
                    f'resolve_variable_threshold_value: variable_threshold_slots is not a dict for threshold_key="{threshold_record.get("_key", "unknown")}", falling back to default value'
                )
                slots = []
            else:
                slots = slots_config.get("slots", [])
        except (json.JSONDecodeError, TypeError):
            # Fallback to default value on parse error
            get_effective_logger().warning(
                f'resolve_variable_threshold_value: failed to parse variable_threshold_slots for threshold_key="{threshold_record.get("_key", "unknown")}", falling back to default value'
            )
            slots = []

    # Evaluate slots in order - first match wins
    for slot in slots:
        days = slot.get("days", [])
        hours = slot.get("hours", [])
        if current_day in days and current_hour in hours:
            slot_value = slot.get("value", threshold_record.get("value"))
            slot_name = slot.get("slot_name", "unnamed")
            return (slot_value, slot_name, True)

    # No slot matched - use the default fallback
    # Use explicit None check (not .get default) to handle both missing key
    # and explicit None/null stored in KV (e.g. from bulk update clearing)
    default_value = threshold_record.get("variable_threshold_default")
    if default_value is None:
        default_value = threshold_record.get("value")
    return (default_value, "_default", True)


def validate_variable_threshold_slots(slots_config):
    """
    Validate variable threshold slots configuration.

    Arguments:
        slots_config: dict - The parsed JSON configuration containing a "slots" list

    Returns:
        list: List of error messages (empty list means valid)
    """

    errors = []

    if not isinstance(slots_config, dict):
        return ["variable_threshold_slots must be a JSON object"]

    slots = slots_config.get("slots", [])
    if not isinstance(slots, list):
        return ["variable_threshold_slots.slots must be a JSON array"]

    if len(slots) == 0:
        return ["variable_threshold_slots.slots must contain at least one slot"]

    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            errors.append(f"Slot at index {i}: each slot must be a JSON object")
            continue

        slot_name = slot.get("slot_name", f"slot_{i}")

        # validate days
        days = slot.get("days", [])
        if not isinstance(days, list) or len(days) == 0 or not all(
            isinstance(d, int) and 0 <= d <= 6 for d in days
        ):
            errors.append(
                f"Slot '{slot_name}': days must be a non-empty list of integers 0-6 (0=Monday, 6=Sunday)"
            )

        # validate hours
        hours = slot.get("hours", [])
        if not isinstance(hours, list) or len(hours) == 0 or not all(
            isinstance(h, int) and 0 <= h <= 23 for h in hours
        ):
            errors.append(
                f"Slot '{slot_name}': hours must be a non-empty list of integers 0-23"
            )

        # validate value (numeric)
        value = slot.get("value")
        if value is None:
            errors.append(f"Slot '{slot_name}': value is required")
        else:
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"Slot '{slot_name}': value must be numeric")

    return errors


def get_dsm_delay_status(
    data_last_lag_seen,
    data_max_delay_allowed,
    data_last_ingest,
    data_last_time_seen,
    resolved_max_delay_allowed=None,
    variable_delay_slot_name=None,
):
    """
    Create a function called get_dsm_delay_status:
    - arguments: data_last_lag_seen, data_max_delay_allowed, data_last_ingest, data_last_time_seen
    - returns: isUnderDelayAlert (boolean), isUnderDelayMessage (string)
    - behaviour:
        isUnderDelayAlert: If data_last_lag_seen is higher than data_max_delay_allowed, then isUnderDelayAlert is True
        isUnderDelayMessage: If isUnderDelayAlert is True:
            "Monitoring conditions are not met due to delay issues. Event delay is $data_last_lag_seen$ seconds (duration: <conversion of data_last_lag_seen to duration), which is higher than the maximum allowed delay of $data_max_delay_allowed$ seconds (duration: <conversion of data_max_delay_allowed to duration>), latest event available (_time) for this entity: <conversion of epoch data_last_time_seen to %c>, latest event ingested for this entity: <conversion of epoch data_last_ingest to %c>"
        isUnderDelayMessage: If isUnderDelayAlert is False:
            "monitoring conditions for event delay are met. Event delay is $data_last_lag_seen$ seconds (duration: <conversion of data_last_lag_seen to duration), which is lower than the maximum allowed delay of $data_max_delay_allowed$ seconds (duration: <conversion of data_max_delay_allowed to duration>), latest event available for this entity: <conversion of epoch data_last_time_seen to %c>, latest event ingested for this entity: <conversion of epoch data_last_ingest to %c>"
    """

    # convert data_last_lag_seen to float
    try:
        data_last_lag_seen = float(data_last_lag_seen)
    except:
        data_last_lag_seen = 0

    # convert data_max_delay_allowed to float
    try:
        data_max_delay_allowed = float(data_max_delay_allowed)
    except:
        data_max_delay_allowed = 0

    # determine effective threshold (variable delay takes precedence if provided)
    if resolved_max_delay_allowed is not None:
        try:
            effective_threshold = float(resolved_max_delay_allowed)
        except:
            effective_threshold = data_max_delay_allowed
    else:
        effective_threshold = data_max_delay_allowed

    # convert data_last_ingest to float
    try:
        data_last_ingest = float(data_last_ingest)
    except:
        data_last_ingest = 0

    # convert data_last_time_seen to float
    try:
        data_last_time_seen = float(data_last_time_seen)
    except:
        data_last_time_seen = 0

    # convert data_last_lag_seen to duration
    data_last_lag_seen_duration = convert_seconds_to_duration(data_last_lag_seen)

    # convert effective threshold to duration
    effective_threshold_duration = convert_seconds_to_duration(effective_threshold)

    # convert data_last_ingest to %c
    data_last_ingest_datetime = convert_epoch_to_datetime(data_last_ingest)

    # convert data_last_time_seen to %c
    data_last_time_seen_datetime = convert_epoch_to_datetime(data_last_time_seen)

    # define isUnderDelayAlert
    if float(data_last_lag_seen) > float(effective_threshold):
        isUnderDelayAlert = True
    else:
        isUnderDelayAlert = False

    # build threshold type label for status messages
    if variable_delay_slot_name:
        threshold_label = f"variable delay threshold (active slot: '{variable_delay_slot_name}')"
    else:
        threshold_label = "static delay threshold"

    # define isUnderDelayMessage
    if isUnderDelayAlert:
        isUnderDelayMessage = f"""Monitoring conditions are not met due to delay issues. Event delay is {round(float(data_last_lag_seen), 3)} seconds (duration: {data_last_lag_seen_duration}), which is higher than the maximum allowed {threshold_label} of {int(round(float(effective_threshold), 0))} seconds (duration: {effective_threshold_duration}), latest event available (_time) for this entity: {data_last_time_seen_datetime}, latest event ingested (_indextime) for this entity: {data_last_ingest_datetime}. This indicates that the source is receiving events with timestamps older than the threshold defined for this entity."""
    else:
        isUnderDelayMessage = f"""monitoring conditions for event delay are met. Event delay is {round(float(data_last_lag_seen), 3)} seconds (duration: {data_last_lag_seen_duration}), which is lower than the maximum allowed {threshold_label} of {int(round(float(effective_threshold), 0))} seconds (duration: {effective_threshold_duration}), latest event available (_time) for this entity: {data_last_time_seen_datetime}"""

    # return
    return isUnderDelayAlert, isUnderDelayMessage


def build_outlier_reason_status_message(record, score_outliers):
    """
    Resolve the human-readable outlier reason string to append to status_message.

    Reads ``record["isOutlierReason"]`` first (the latest snapshot from the most
    recent ML monitor cycle). If that field is empty AND ``score_outliers`` is
    positive (meaning the 24h cumulative scoring window still contains outlier
    events), falls back to ``record["lastIsOutlierReason"]`` — the cache of the
    last active outlier reason, written asymmetrically by the outliers tracker
    (refreshed when outliers are detected, preserved when the cycle clears).

    Returns ``(message_or_None, used_cached_bool)``. When ``used_cached`` is
    True the message is annotated to make it clear the reported breach is no
    longer active in the most recent cycle but still drives the impact score.

    The fallback is bounded to ~24h to stay aligned with the ``mstats``
    lookback in ``calculate_score`` — beyond that the cache and the score are
    both irrelevant.
    """
    outlier_reasons = record.get("isOutlierReason") or []

    if outlier_reasons:
        if isinstance(outlier_reasons, list):
            return (" | ".join(str(r) for r in outlier_reasons), False)
        return (str(outlier_reasons), False)

    if score_outliers is None or score_outliers <= 0:
        return (None, False)

    cached = record.get("lastIsOutlierReason") or []
    cached_mtime = record.get("lastIsOutlierReason_mtime")
    if not cached or not cached_mtime:
        return (None, False)

    try:
        age_hours = (time.time() - float(cached_mtime)) / 3600.0
    except (TypeError, ValueError):
        return (None, False)

    if age_hours < 0 or age_hours > 24:
        return (None, False)

    if isinstance(cached, list):
        cached_str = " | ".join(str(r) for r in cached)
    else:
        cached_str = str(cached)

    annotated = (
        f"Last detected outlier (no longer active in the most recent ML monitor cycle, "
        f"~{age_hours:.1f}h ago, still scoring in the 24h impact-score window): {cached_str}"
    )
    return (annotated, True)


def set_dsm_status(
    logger,
    splunkd_uri,
    session_key,
    tenant_id,
    record,
    isOutlier,
    isAnomaly,
    isFuture,
    isFutureMsg,
    isUnderMonitoring,
    isUnderMonitoringMsg,
    isUnderDcountHost,
    isUnderDcountHostMsg,
    object_logical_group_dict,
    isUnderLatencyAlert,
    isUnderLatencyMessage,
    isUnderDelayAlert,
    isUnderDelayMessage,
    disruption_queue_collection,
    disruption_queue_record,
    source_handler=None,
    monitoring_anomaly_reason=None,
    score=None,
    score_outliers=None,
    vtenant_account=None,
    delay_is_variable=False,
):
    """
    Create a function called set_dsm_status:
    - arguments: record, isOutlier, isAnomaly, isFuture, isUnderMonitoring, isUnderMonitoringMsg, isUnderDcountHost, isUnderLogicalGroup, LogicalGroupStateInAlert, isUnderLatencyAlert, isUnderLatencyMessage, isUnderDelayAlert, isUnderDelayMessage
    - returns:
        object_state (string): blue, orange, green, red
        anomaly_reason (list): list of short code reasons why the object is in anomaly
        status_message (list): list of long description reasons why the object is in anomaly
    - behaviour:
        object_state:
            green if:
                isOutlier is 1
                isAnomaly is 1
                isFuture is False
                isUnderMonitoring is True
                isUnderDcountHost is False
                if isUnderLogicalGroup is True, then LogicalGroupStateInAlert must be False
                isUnderLatencyAlert is False
                isUnderDelayAlert is False
            blue if:
                Any of the condition above is not met, but isUnderLogicalGroup is True and LogicalGroupStateInAlert is True
            orange if:
                All green conditions are met except for isFuture which would be True
            red if:
                Any of the green conditions are not met, and blue conditions and orange conditions are not met
        anomaly_reason:
            if object_state is green, anomnaly_reason is None
            Otherwise, anomaly_reason is a list containing the reasons why the object is in anomaly
    """

    # init status_message and anomaly_reason
    status_message = []
    anomaly_reason = []

    # init status_message_json
    status_message_json = {}

    # init original_object_state
    original_object_state = record.get("object_state", "green")

    # define object_state
    # Check outliers: if isOutlier == 1 but score_outliers <= 0, treat as no outlier (suppressed)
    isOutlierEffective = isOutlier == 1
    if score_outliers is not None and score_outliers <= 0:
        # Outliers are suppressed (false positive), don't treat as outlier
        isOutlierEffective = False
    
    if (
        (isOutlierEffective == False or isOutlier == 2)
        and (isAnomaly == 0 or isAnomaly == 2)
        and isUnderDcountHost is False
        and isUnderLatencyAlert is False
        and isUnderDelayAlert is False
    ):
        object_state = "green"
    else:
        object_state = "red"

    #
    # Logical group management
    #

    logical_group_input_state = object_state
    (
        isUnderLogicalGroup,
        LogicalGroupStateInAlert,
        LogicalGroupMsg,
    ) = get_and_manage_logical_group_status(
        splunkd_uri,
        session_key,
        tenant_id,
        record.get("object"),
        object_state,
        record.get("object_group_key"),
        object_logical_group_dict,
    )

    # log debug
    get_effective_logger().debug(
        f'function get_and_manage_logical_group_status: object="{record.get("object")}", object_state="{object_state}", object_group_key="{record.get("object_group_key")}", isUnderLogicalGroup="{isUnderLogicalGroup}", LogicalGroupStateInAlert="{LogicalGroupStateInAlert}", LogicalGroupMsg="{LogicalGroupMsg}"'
    )

    # Update object_logical_group_dict to reflect the current state after KVstore update
    # This ensures re-evaluation uses fresh data instead of stale dict
    if isUnderLogicalGroup and object_logical_group_dict:
        object_name = record.get("object")
        # Normalize the lists to ensure consistency
        members_green = normalize_logical_group_members(
            object_logical_group_dict.get("object_group_members_green", [])
        )
        members_red = normalize_logical_group_members(
            object_logical_group_dict.get("object_group_members_red", [])
        )
        
        # Update based on current state (matching the logic in get_and_manage_logical_group_status)
        if object_state == "green":
            if object_name not in members_green:
                members_green.append(object_name)
            if object_name in members_red:
                members_red.remove(object_name)
        else:  # red or blue
            if object_name not in members_red:
                members_red.append(object_name)
            if object_name in members_green:
                members_green.remove(object_name)
        
        # Update the dict with normalized lists
        object_logical_group_dict["object_group_members_green"] = members_green
        object_logical_group_dict["object_group_members_red"] = members_red

    # if object_state is red but isUnderLogicalGroup is True and LogicalGroupStateInAlert is False, then object_state is blue
    if object_state == "red" and isUnderLogicalGroup is True:
        if LogicalGroupStateInAlert is False:
            object_state = "blue"

    # if object_state is not red or blue but isFuture is True, then object_state is orange
    if object_state not in ["red", "blue"]:
        if isFuture is True:
            object_state = "orange"

    # if object_state is red but isUnderMonitoring is False, then object_state is orange
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    #
    # Hybrid scoring: Apply score-based logic
    # Outliers are handled separately via score_outliers in get_outliers_status
    #
    total_score = None
    score_definition = {}
    if score is not None:
        # Calculate total score with static increments for anomalies
        base_score = float(score) if score is not None else 0.0
        total_score = base_score
        
        # Build score definition to track where the score comes from
        # Convert base_score to integer if it's a whole number, otherwise keep as float
        if base_score == int(base_score):
            score_definition["base_score"] = int(base_score)
        else:
            score_definition["base_score"] = base_score
        score_definition["components"] = []
        
        # Add static increments for each anomaly type (using VT-specific impact scores)
        if isAnomaly == 1:
            increment = get_impact_score(vtenant_account, "impact_score_dsm_data_sampling_anomaly", 36)
            total_score += increment
            score_definition["components"].append({
                "type": "data_sampling_anomaly",
                "score": increment,
                "description": "Data sampling anomaly detected"
            })
        
        if isUnderDelayAlert is True:
            increment = get_entity_impact_score(record, "dsm", "delay", vtenant_account, 100)
            total_score += increment
            delay_type = "variable_delay_threshold_breach" if delay_is_variable else "delay_threshold_breach"
            delay_desc = "Variable delay threshold breached" if delay_is_variable else "Delay threshold breached"
            score_definition["components"].append({
                "type": delay_type,
                "score": increment,
                "description": delay_desc
            })

        if isUnderLatencyAlert is True:
            increment = get_entity_impact_score(record, "dsm", "latency", vtenant_account, 48)
            total_score += increment
            score_definition["components"].append({
                "type": "latency_threshold_breach",
                "score": increment,
                "description": "Latency threshold breached"
            })
        
        if isUnderDcountHost is True:
            increment = get_impact_score(vtenant_account, "impact_score_dsm_min_hosts_dcount_breach", 100)
            total_score += increment
            score_definition["components"].append({
                "type": "min_hosts_dcount_breach",
                "score": increment,
                "description": "Minimum hosts dcount threshold breached"
            })
        
        if isFuture is True:
            increment = get_impact_score(vtenant_account, "impact_score_dsm_future_tolerance_breach", 36)
            total_score += increment
            score_definition["components"].append({
                "type": "future_tolerance_breach",
                "score": increment,
                "description": "Future tolerance breached"
            })
        
        # Add outlier score if present
        if score_outliers is not None and score_outliers > 0:
            score_definition["score_outliers"] = float(score_outliers)
        
        # Add score sources if available
        score_source = record.get("score_source", [])
        if score_source:
            score_definition["score_source"] = score_source if isinstance(score_source, list) else [score_source]
            
            # Check for manual_score increases (positive scores from manual_score source)
            # If manual_score increases the score without a related anomaly, add score_breached component
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            if "manual_score" in score_source_list and total_score and total_score > 0:
                # Check if there are no other anomaly components
                has_other_anomalies = (
                    isAnomaly == 1
                    or isUnderDelayAlert is True
                    or isUnderLatencyAlert is True
                    or isUnderDcountHost is True
                    or isFuture is True
                    or (score_outliers is not None and score_outliers > 0)
                )
                if not has_other_anomalies:
                    # Manual score increase without other anomalies - add score_breached component
                    score_definition["components"].append({
                        "type": "manual_score",
                        "score": 0,  # Score is already included in base_score calculation
                        "description": "Manual score influence applied without related anomaly"
                    })
        
        # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score
        
        # Apply score-based logic:
        # - If total_score >= 100: entity should be red (if not already red due to other reasons, keep current state)
        # - If total_score > 0 and < 100: entity should be orange (even if currently green)
        # - If total_score == 0: keep current state
        
        if total_score >= 100:
            # If score >= 100, ensure entity is red (unless it's blue due to logical group)
            if object_state not in ["red", "blue"]:
                object_state = "red"
                get_effective_logger().debug(
                    f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red (score >= 100)'
                )
            else:
                get_effective_logger().debug(
                    f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (score >= 100)'
                )
        elif total_score > 0 and total_score < 100:
            # If score > 0 and < 100, entity should be orange (even if currently green)
            if object_state == "green":
                object_state = "orange"
                # Add status message about score
                score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                # Add outlier context if outliers are present
                if score_outliers is not None and score_outliers > 0:
                    score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                status_message.append(score_msg)
                get_effective_logger().debug(
                    f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting green to orange (0 < score < 100)'
                )
            elif object_state == "red":
                # Downgrade red to orange if score < 100
                # Only apply score-based downgrade if the red state is NOT due to outliers
                # (outliers with score_outliers >= 100 should still be red)
                if isOutlier != 1:
                    object_state = "orange"
                    # Add status message about score when downgrading
                    score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                    if score_outliers is not None and score_outliers > 0:
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                    status_message.append(score_msg)
                    get_effective_logger().debug(
                        f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", downgrading red to orange (non-outlier anomalies only)'
                    )
                else:
                    # If outlier is present but score_outliers < 100, it was already set to isOutlier=2
                    # in get_outliers_status, so we can still apply score-based logic
                    if score_outliers is not None and score_outliers < 100:
                        object_state = "orange"
                        # Add status message about score when downgrading due to low outlier score
                        score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                        score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                        status_message.append(score_msg)
                        get_effective_logger().debug(
                            f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'downgrading red to orange (outlier score too low)'
                        )
                    else:
                        get_effective_logger().debug(
                            f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", keeping red state (outlier score >= 100)'
                        )
            else:
                get_effective_logger().debug(
                    f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (0 < score < 100)'
                )
        else:
            # total_score == 0 or total_score <= 0
            # Check if score is 0 due to false_positive (global false positive, not just outliers)
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            has_false_positive = "false_positive" in score_source_list
            
            if has_false_positive:
                # Score is 0 due to false_positive, set to green (anomaly_reason will remain visible for audit)
                object_state = "green"
                get_effective_logger().debug(
                    f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", score_source="{score_source}", '
                    f'setting state to green (false positive set, score cancelled)'
                )
            else:
                # Check if total_score is 0 because all impact score weights are 0
                # If all components have score 0, then the entity should be green (unless outliers present)
                all_components_zero = True
                if score_definition and "components" in score_definition:
                    components = score_definition.get("components", [])
                    if components:
                        for component in components:
                            component_score = component.get("score", 0)
                            if component_score != 0:
                                all_components_zero = False
                                break
                    # If no components exist but total_score is 0, also consider it as all zero
                    elif not components and total_score == 0:
                        all_components_zero = True
                
                # If all components have score 0 and no outliers (or outliers suppressed), set to green
                if all_components_zero and (score_outliers is None or score_outliers <= 0):
                    object_state = "green"
                    get_effective_logger().debug(
                        f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'setting state to green (all impact score weights are 0, no outliers)'
                    )
                else:
                    get_effective_logger().debug(
                        f'set_dsm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'keeping current state (score == 0)'
                    )

    # If score-based logic changed the state, re-evaluate logical group status
    if (
        logical_group_input_state != object_state
        and object_state in ["green", "red"]
        and record.get("object_group_key")
    ):
        (
            isUnderLogicalGroup,
            LogicalGroupStateInAlert,
            LogicalGroupMsg,
        ) = get_and_manage_logical_group_status(
            splunkd_uri,
            session_key,
            tenant_id,
            record.get("object"),
            object_state,
            record.get("object_group_key"),
            object_logical_group_dict,
        )

        if object_state == "red" and isUnderLogicalGroup is True:
            if LogicalGroupStateInAlert is False:
                object_state = "blue"

    #
    # Out of monitoring days and hours management (post-scoring)
    # Monitoring time policy takes precedence over scoring — entities outside
    # their monitoring window must never be promoted to red by scoring logic
    #
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    # define anomaly_reason
    if object_state == "green":
        status_message.append(isUnderDelayMessage)
        status_message.append(isUnderLatencyMessage)

        # Check if false positive is set - if so, preserve anomaly reasons from score_definition
        score_source = record.get("score_source", [])
        score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
        has_false_positive = "false_positive" in score_source_list

        if has_false_positive and score_definition and "components" in score_definition:
            # Extract anomaly reasons from score_definition components
            for component in score_definition.get("components", []):
                component_type = component.get("type")
                if component_type:
                    mapped_reason = get_anomaly_reason_from_component_type(component_type)
                    if mapped_reason and mapped_reason not in anomaly_reason:
                        anomaly_reason.append(mapped_reason)
            # If no components found, still add "none"
            if not anomaly_reason:
                anomaly_reason.append("none")
        else:
            anomaly_reason.append("none")

        # if in a logical group, add the logical group message
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)

    else:
        # Check for outliers: either isOutlier == 1 (traditional) or score_outliers > 0 (hybrid scoring)
        if isOutlier == 1 or (score_outliers is not None and score_outliers > 0):
            # Always add outlier reasons when outliers are present (either traditional or hybrid scoring).
            # When the latest ML monitor cycle has cleared isOutlierReason but score_outliers (24h cumulative)
            # still indicates past outliers, fall back to the cached lastIsOutlierReason — see helper docstring.
            outlier_msg, _outlier_used_cached = build_outlier_reason_status_message(
                record, score_outliers
            )
            if outlier_msg:
                status_message.append(outlier_msg)
            # Add ml_outliers_detection to anomaly_reason for all outlier cases
            if "ml_outliers_detection" not in anomaly_reason:
                anomaly_reason.append("ml_outliers_detection")

            # Add score context message for red state with high outlier score (>= 100)
            # Note: orange state score messages are already added during score-based state transitions above
            if score_outliers is not None and score_outliers >= 100:
                base_score = float(score) if score is not None else 0.0
                total = float(total_score) if total_score is not None else score_outliers
                status_message.append(
                    f"Entity has an impact score of {total:.1f} (base score: {base_score:.1f}), which is 100 or above. "
                    f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    f"This indicates critical anomalies warranting an alert status."
                )

        if isAnomaly == 1:
            status_message.append(
                "anomalies detected in the data sampling and format recognition, review the data sampling screen to investigate. This alert means that trackMe detected an issue in the format of the events compared to the format that was previously identified for this source"
            )
            anomaly_reason.append("data_sampling_anomaly")

        if isFuture is True:
            status_message.append(isFutureMsg)
            anomaly_reason.append("future_over_tolerance")

        # Monitoring time policy, add the message first then the anomaly reason
        if isUnderMonitoring is False:
            status_message.append(isUnderMonitoringMsg)
            
            # Use new monitoring anomaly reason if provided, otherwise use legacy separate reasons
            if monitoring_anomaly_reason:
                anomaly_reason.append(monitoring_anomaly_reason)

        if isUnderDcountHost is True:
            status_message.append(isUnderDcountHostMsg)
            anomaly_reason.append("min_hosts_dcount")

        if isUnderLatencyAlert is True:
            status_message.append(isUnderLatencyMessage)
            anomaly_reason.append("lag_threshold_breached")

        if isUnderDelayAlert is True:
            status_message.append(isUnderDelayMessage)
            if delay_is_variable:
                anomaly_reason.append("variable_delay_threshold_breached")
            else:
                anomaly_reason.append("delay_threshold_breached")

        # logical group
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)
            anomaly_reason.append("in_logical_group")

    # Fallback: manual score influence raised total_score > 0 but no actual
    # anomaly was detected — populate status_message / anomaly_reason so the
    # UI can explain the non-green state.
    apply_manual_score_without_anomaly_fallback(
        record,
        score_definition,
        total_score,
        score,
        status_message,
        anomaly_reason,
        object_state,
    )

    # form status_message_json
    status_message_json["status_message"] = status_message
    status_message_json["anomaly_reason"] = anomaly_reason

    # Add score information to status_message_json for UI display (sorted alphabetically)
    # Use total_score if calculated (hybrid scoring), otherwise use base score
    if total_score is not None:
        status_message_json["score"] = float(total_score)
        # Update record score to reflect the calculated total_score for UI consistency
        record["score"] = float(total_score)
        # Add score definition for drilldown modal
        if score_definition:
            status_message_json["score_definition"] = score_definition
            record["score_definition"] = json.dumps(score_definition) if isinstance(score_definition, dict) else score_definition
    elif score is not None:
        status_message_json["score"] = float(score)
    if score_outliers is not None:
        status_message_json["score_outliers"] = float(score_outliers)
    if total_score is not None:
        status_message_json["total_score"] = float(total_score)

    # get disruption_duration
    if not disruption_queue_record:
        record["disruption_min_time_sec"] = 0

    else:

        logger.debug(
            f'disruption_queue_record="{disruption_queue_record}", getting disruption_duration'
        )

        disruption_object_state = disruption_queue_record.get("object_state", "green")
        try:
            disruption_min_time_sec = int(
                disruption_queue_record.get("disruption_min_time_sec", 0)
            )
        except:
            disruption_min_time_sec = 0
        # add to the record
        record["disruption_min_time_sec"] = disruption_min_time_sec

        try:
            disruption_start_epoch = float(
                disruption_queue_record.get("disruption_start_epoch", 0)
            )
        except:
            disruption_start_epoch = 0

        # Case 1: Entity is no longer in alert state (not red)
        if object_state != "red":
            # Only update if we were previously tracking a disruption
            if disruption_object_state == "red":
                disruption_queue_record["object_state"] = object_state
                disruption_queue_record["disruption_start_epoch"] = 0
                disruption_queue_record["mtime"] = time.time()

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")
            return object_state, status_message, status_message_json, anomaly_reason

        # Case 2: Entity is in alert state (red)
        if object_state == "red":
            current_time = time.time()

            # If this is a new disruption, start tracking it
            if disruption_object_state != "red":
                disruption_queue_record["object_state"] = "red"
                disruption_queue_record["disruption_start_epoch"] = current_time
                disruption_queue_record["mtime"] = current_time

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")

                # For new disruptions, if min time is set, show as blue with message
                if disruption_min_time_sec > 0:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is 0 which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message
                return object_state, status_message, status_message_json, anomaly_reason

            # If we're already tracking a disruption, check duration
            if disruption_min_time_sec > 0:
                try:
                    disruption_duration = current_time - disruption_start_epoch
                except Exception as e:
                    logger.error(f"error calculating disruption_duration: {e}")
                    disruption_duration = 0

                # If duration hasn't breached threshold, show as blue with message
                if disruption_duration < disruption_min_time_sec:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is {convert_seconds_to_duration(disruption_duration)} which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message

    # anomaly_reason sanitify check, if the list has more than 1 item, and contains "none", remove it
    if isinstance(anomaly_reason, list):
        if len(anomaly_reason) > 1 and "none" in anomaly_reason:
            anomaly_reason.remove("none")

    # return
    get_effective_logger().debug(
        f'set_dsm_status, object="{record.get("object")}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
    )

    return (
        object_state,
        status_message,
        status_message_json,
        anomaly_reason,
    )


def set_dhm_status(
    logger,
    splunkd_uri,
    session_key,
    tenant_id,
    record,
    isOutlier,
    isFuture,
    isFutureMsg,
    isUnderMonitoring,
    isUnderMonitoringMsg,
    object_logical_group_dict,
    isUnderLatencyAlert,
    isUnderLatencyMessage,
    isUnderDelayAlert,
    isUnderDelayMessage,
    default_splk_dhm_alerting_policy,
    disruption_queue_collection,
    disruption_queue_record,
    source_handler=None,
    monitoring_anomaly_reason=None,
    score=None,
    score_outliers=None,
    vtenant_account=None,
    delay_is_variable=False,
):
    """
    Create a function called set_dhm_status:
    - arguments: record, isOutlier, isFuture, isFutureMsg, isUnderMonitoring, isUnderMonitoringMsg, object_logical_group_dict, isUnderLatencyAlert, isUnderLatencyMessage, isUnderDelayAlert, isUnderDelayMessage, default_splk_dhm_alerting_policy
    - returns:
        object_state (string): blue, orange, green, red
        anomaly_reason (list): list of short code reasons why the object is in anomaly
        status_message (list): list of long description reasons why the object is in anomaly
    - behaviour:
        object_state:
            green if:
                isOutlier is 1
                isFuture is False
                isUnderMonitoring is True
                if isUnderLogicalGroup is True, then LogicalGroupStateInAlert must be False
                isUnderLatencyAlert is False
                isUnderDelayAlert is False
            blue if:
                Any of the condition above is not met, but isUnderLogicalGroup is True and LogicalGroupStateInAlert is True
            orange if:
                All green conditions are met except for isFuture which would be True
            red if:
                Any of the green conditions are not met, and blue conditions and orange conditions are not met
        anomaly_reason:
            if object_state is green, anomnaly_reason is None
            Otherwise, anomaly_reason is a list containing the reasons why the object is in anomaly
    """

    # init status_message and anomaly_reason
    status_message = []
    anomaly_reason = []

    # init status_message_json
    status_message_json = {}

    # define object_state
    # Check outliers: if isOutlier == 1 but score_outliers <= 0, treat as no outlier (suppressed)
    isOutlierEffective = isOutlier == 1
    if score_outliers is not None and score_outliers <= 0:
        # Outliers are suppressed (false positive), don't treat as outlier
        isOutlierEffective = False
    
    if (
        (isOutlierEffective == False or isOutlier == 2)
        and isUnderLatencyAlert is False
        and isUnderDelayAlert is False
    ):
        object_state = "green"
    else:
        object_state = "red"

    #
    # Logical group management
    #

    (
        isUnderLogicalGroup,
        LogicalGroupStateInAlert,
        LogicalGroupMsg,
    ) = get_and_manage_logical_group_status(
        splunkd_uri,
        session_key,
        tenant_id,
        record.get("object"),
        object_state,
        record.get("object_group_key"),
        object_logical_group_dict,
    )

    # log debug
    get_effective_logger().debug(
        f'function get_and_manage_logical_group_status: object="{record.get("object")}", object_state="{object_state}", object_group_key="{record.get("object_group_key")}", isUnderLogicalGroup="{isUnderLogicalGroup}", LogicalGroupStateInAlert="{LogicalGroupStateInAlert}", LogicalGroupMsg="{LogicalGroupMsg}"'
    )

    # Update object_logical_group_dict to reflect the current state after KVstore update
    # This ensures re-evaluation uses fresh data instead of stale dict
    if isUnderLogicalGroup and object_logical_group_dict:
        object_name = record.get("object")
        # Normalize the lists to ensure consistency
        members_green = normalize_logical_group_members(
            object_logical_group_dict.get("object_group_members_green", [])
        )
        members_red = normalize_logical_group_members(
            object_logical_group_dict.get("object_group_members_red", [])
        )
        
        # Update based on current state (matching the logic in get_and_manage_logical_group_status)
        if object_state == "green":
            if object_name not in members_green:
                members_green.append(object_name)
            if object_name in members_red:
                members_red.remove(object_name)
        else:  # red or blue
            if object_name not in members_red:
                members_red.append(object_name)
            if object_name in members_green:
                members_green.remove(object_name)
        
        # Update the dict with normalized lists
        object_logical_group_dict["object_group_members_green"] = members_green
        object_logical_group_dict["object_group_members_red"] = members_red

    splk_dhm_alerting_policy = record.get("splk_dhm_alerting_policy", "global_policy")
    if not len(splk_dhm_alerting_policy) > 0:
        splk_dhm_alerting_policy = "global_policy"
    splk_dhm_st_summary = record.get("splk_dhm_st_summary")

    # get the entity global max delay allowed
    global_max_delay_allowed = int(
        round(float(record.get("data_max_delay_allowed", 0)), 0)
    )

    # get the entity global max lag allowed
    global_max_lag_allowed = int(round(float(record.get("data_max_lag_allowed", 0)), 0))

    # get the entity global last delay seen (data_last_lag_seen)
    global_last_event_lag = int(round(float(record.get("data_last_lag_seen", 0)), 0))

    # get the entity global last lag seen (data_last_ingestion_lag_seen)
    global_last_ingest_lag = int(
        round(float(record.get("data_last_ingestion_lag_seen", 0)), 0)
    )

    # Convert splk_dhm_st_summary to a list if it is a string
    if isinstance(splk_dhm_st_summary, str):
        splk_dhm_st_summary = [splk_dhm_st_summary]

    # counters
    count_red = 0
    count_green = 0
    sourcetypes_red_list = []

    # retrieve host_idx_blocklists, host_st_blocklists
    host_idx_blocklists = record.get("host_idx_blocklists", [])
    host_st_blocklists = record.get("host_st_blocklists", [])

    # if string, then turn into list from comma separated string
    if isinstance(host_idx_blocklists, str):
        host_idx_blocklists = host_idx_blocklists.split(",")
    if isinstance(host_st_blocklists, str):
        host_st_blocklists = host_st_blocklists.split(",")

    # splk_dhm_st_summary can actually be a list
    if isinstance(splk_dhm_st_summary, list):

        for item_str in splk_dhm_st_summary:
            dict_loaded = False
            dict_loading_error = []

            # Try JSON first (new format, ~10-100x faster than ast.literal_eval)
            try:
                new_dict = json.loads(item_str)
                dict_loaded = True
            except Exception as e:
                dict_loaded = False
                dict_loading_error.append(str(e))

            # Fall back to ast.literal_eval for legacy Python dict format
            if not dict_loaded:
                try:
                    dict_str = "{" + item_str + "}"
                    new_dict = ast.literal_eval(dict_str)
                    dict_loaded = True
                except Exception as e:
                    dict_loaded = False
                    dict_loading_error.append(str(e))

            if dict_loaded:

                # handle blocklists
                new_dict = {
                    key: val
                    for key, val in new_dict.items()
                    if val["idx"] not in host_idx_blocklists
                    and val["st"] not in host_st_blocklists
                }

                # Iterate through the inner dictionaries
                for inner_dict in new_dict.values():

                    if inner_dict.get("state") == "red":
                        count_red += 1

                        max_lag_allowed = float(inner_dict.get("max_lag_allowed"))
                        max_delay_allowed = float(inner_dict.get("max_delay_allowed"))
                        last_ingest_lag = float(inner_dict.get("last_ingest_lag"))
                        last_event_lag = float(inner_dict.get("last_event_lag"))

                        # Extras-aware trackers (breakby_extra_fields) extend the
                        # combo grain beyond (index, sourcetype). When present,
                        # the per-combo summary carries an `extras` dict mapping
                        # field name to value (e.g. {"source": "/var/log/..."}).
                        # Surface it in human-readable form so operators
                        # inspecting alert noise can attribute the breach to the
                        # exact offending combo. Falls back to a flat string for
                        # records still in flight from a pre-encoding-change
                        # cycle (defensive — mid-upgrade only).
                        _extras = inner_dict.get("extras")
                        if isinstance(_extras, dict) and _extras:
                            _extras_str = ", ".join(
                                f"{k}: {v}" for k, v in _extras.items()
                            )
                            _combo_label = (
                                f'(idx: {inner_dict.get("idx")}, '
                                f'st: {inner_dict.get("st")}, {_extras_str}'
                            )
                        elif _extras:
                            _combo_label = (
                                f'(idx: {inner_dict.get("idx")}, '
                                f'st: {inner_dict.get("st")}, extras: {_extras}'
                            )
                        else:
                            _combo_label = (
                                f'(idx: {inner_dict.get("idx")}, '
                                f'st: {inner_dict.get("st")}'
                            )

                        if (
                            last_ingest_lag > max_lag_allowed
                            and "lag_threshold_breached" not in anomaly_reason
                        ):
                            anomaly_reason.append("lag_threshold_breached")
                            sourcetypes_red_list.append(
                                f'{_combo_label}, anomaly_reason: lag_threshold_breached)'
                            )
                        if (
                            last_event_lag > max_delay_allowed
                            and "delay_threshold_breached" not in anomaly_reason
                        ):
                            anomaly_reason.append("delay_threshold_breached")
                            sourcetypes_red_list.append(
                                f'{_combo_label}, anomaly_reason: delay_threshold_breached)'
                            )

                    elif inner_dict.get("state") == "green":
                        count_green += 1

            else:
                get_effective_logger().error(
                    f"Error in processing item_str: {item_str}. Error: {dict_loading_error}"
                )

        get_effective_logger().debug(
            f'object="{record.get("object")}", count_red={count_red}, count_green={count_green}'
        )

        # turn sourcetypes_red_list into a pipe separated string
        sourcetypes_red_list = "|".join(sourcetypes_red_list)

        # Decision making based on the counts of red and green states
        if splk_dhm_alerting_policy == "global_policy":
            if default_splk_dhm_alerting_policy == "track_per_host":
                # Use object_state as it is
                pass
            elif default_splk_dhm_alerting_policy == "track_per_sourcetype":
                if count_red > 0:
                    object_state = "red"
                    status_message.append(
                        f"One or more sourcetypes are in alert for this entity, and policy is set to track_per_sourcetype, sourcetypes in alert: {sourcetypes_red_list}"
                    )
                else:
                    # Use object_state as it is
                    pass
        elif splk_dhm_alerting_policy == "track_per_host":
            # Use object_state as it is
            pass
        elif splk_dhm_alerting_policy == "track_per_sourcetype":
            if count_red > 0:
                object_state = "red"
                status_message.append(
                    f"One or more sourcetypes are in alert for this entity, and policy is set to track_per_sourcetype, sourcetypes in alert: {sourcetypes_red_list}"
                )
            else:
                # Use object_state as it is
                pass
        else:
            # Use object_state as it is
            pass

    # if all sourcetypes are in alert, object_state is red or orange depending on the global max delay entity values
    if (
        count_green == 0
        and (global_last_event_lag >= global_max_delay_allowed)
        and (global_last_ingest_lag >= global_max_lag_allowed)
    ):
        object_state = "red"
        status_message.append(
            f"all sourcetypes are in alert for this entity, global entity max delay allowed is breached (max_delay_allowed: {global_max_delay_allowed} seconds, duration: {convert_seconds_to_duration(global_max_delay_allowed)}, last_event_lag: {global_last_event_lag} seconds, duration: {convert_seconds_to_duration(global_last_event_lag)}), global entity max lag allowed is breached (max_delay_allowed: {global_max_lag_allowed} seconds, duration: {convert_seconds_to_duration(global_max_lag_allowed)}), last_event_lag: {global_last_ingest_lag} seconds, duration: {convert_seconds_to_duration(global_last_ingest_lag)})"
        )

    elif (
        count_green == 0
        and (global_last_event_lag < global_max_delay_allowed)
        and (global_last_ingest_lag >= global_max_lag_allowed)
    ):
        object_state = "red"
        status_message.append(
            f"all sourcetypes are in alert for this entity, global entity max delay allowed is not breached but max lag allowed is breached (max_delay_allowed: {global_max_delay_allowed} seconds, duration: {convert_seconds_to_duration(global_max_delay_allowed)}, last_event_lag: {global_last_event_lag} seconds, duration: {convert_seconds_to_duration(global_last_event_lag)})"
        )

    elif (
        count_green == 0
        and (global_last_event_lag >= global_max_delay_allowed)
        and (global_last_ingest_lag < global_max_lag_allowed)
    ):
        object_state = "red"
        status_message.append(
            f"all sourcetypes are in alert for this entity, global entity max delay allowed is breached but max lag allowed is not breached (max_delay_allowed: {global_max_delay_allowed} seconds, duration: {convert_seconds_to_duration(global_max_delay_allowed)}, last_event_lag: {global_last_event_lag} seconds, duration: {convert_seconds_to_duration(global_last_event_lag)})"
        )

    elif (
        count_green == 0
        and (global_last_event_lag < global_max_delay_allowed)
        and (global_last_ingest_lag < global_max_lag_allowed)
    ):
        object_state = "green"
        status_message.append(
            f"all sourcetypes are in alert for this entity, however global entity max delay allowed and max lag allowed are not breached (max_delay_allowed: {global_max_delay_allowed} seconds, duration: {convert_seconds_to_duration(global_max_delay_allowed)}, last_event_lag: {global_last_event_lag} seconds, duration: {convert_seconds_to_duration(global_last_event_lag)})"
        )

    elif count_green == 0:
        object_state = "red"
        status_message.append(
            f"all sourcetypes are in alert for this entity, however global entity level max delay allowed and max lag allowed could not be determined, verify TrackMe logs for more information (max_delay_allowed: {global_max_delay_allowed} seconds, duration: {convert_seconds_to_duration(global_max_delay_allowed)}, last_event_lag: {global_last_event_lag} seconds, duration: {convert_seconds_to_duration(global_last_event_lag)})"
        )

    # if object_state is red but isUnderLogicalGroup is True and LogicalGroupStateInAlert is False, then object_state is blue
    if object_state == "red" and isUnderLogicalGroup is True:
        if LogicalGroupStateInAlert is False:
            object_state = "blue"

    # if object_state is not red or blue but isFuture is True, then object_state is orange
    if object_state not in ["red", "blue"]:
        if isFuture is True:
            object_state = "orange"

    # if object_state is red but if isUnderMonitoring is False, then object_state is orange
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    # Capture state after all DHM-specific logic but before scoring
    # This ensures we can detect if scoring changes the state and re-evaluate logical groups
    logical_group_input_state = object_state

    #
    # Hybrid scoring: Apply score-based logic
    # Outliers are handled separately via score_outliers in get_outliers_status
    #
    total_score = None
    score_definition = {}
    if score is not None:
        # Calculate total score with static increments for anomalies
        base_score = float(score) if score is not None else 0.0
        total_score = base_score
        
        # Build score definition to track where the score comes from
        # Convert base_score to integer if it's a whole number, otherwise keep as float
        if base_score == int(base_score):
            score_definition["base_score"] = int(base_score)
        else:
            score_definition["base_score"] = base_score
        score_definition["components"] = []
        
        # Add static increments for each anomaly type (using VT-specific impact scores)
        if isUnderDelayAlert is True:
            increment = get_entity_impact_score(record, "dhm", "delay", vtenant_account, 100)
            total_score += increment
            delay_type = "variable_delay_threshold_breach" if delay_is_variable else "delay_threshold_breach"
            delay_desc = "Variable delay threshold breached" if delay_is_variable else "Delay threshold breached"
            score_definition["components"].append({
                "type": delay_type,
                "score": increment,
                "description": delay_desc
            })
        
        if isUnderLatencyAlert is True:
            increment = get_entity_impact_score(record, "dhm", "latency", vtenant_account, 48)
            total_score += increment
            score_definition["components"].append({
                "type": "latency_threshold_breach",
                "score": increment,
                "description": "Latency threshold breached"
            })
        
        if isFuture is True:
            increment = get_impact_score(vtenant_account, "impact_score_dhm_future_tolerance_breach", 36)
            total_score += increment
            score_definition["components"].append({
                "type": "future_tolerance_breach",
                "score": increment,
                "description": "Future tolerance breached"
            })
        
        # Add outlier score if present
        if score_outliers is not None and score_outliers > 0:
            score_definition["score_outliers"] = float(score_outliers)
        
        # Add score sources if available
        score_source = record.get("score_source", [])
        if score_source:
            score_definition["score_source"] = score_source if isinstance(score_source, list) else [score_source]
        
        # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score
        
        # Apply score-based logic:
        # - If total_score >= 100: entity should be red (if not already red due to other reasons, keep current state)
        # - If total_score > 0 and < 100: entity should be orange (even if currently green)
        # - If total_score == 0: keep current state
        
        if total_score >= 100:
            # If score >= 100, ensure entity is red (unless it's blue due to logical group)
            if object_state not in ["red", "blue"]:
                object_state = "red"
                get_effective_logger().debug(
                    f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red (score >= 100)'
                )
            else:
                get_effective_logger().debug(
                    f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (score >= 100)'
                )
        elif total_score > 0 and total_score < 100:
            # If score > 0 and < 100, entity should be orange (even if currently green)
            if object_state == "green":
                object_state = "orange"
                # Add status message about score
                score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                # Add outlier context if outliers are present
                if score_outliers is not None and score_outliers > 0:
                    score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                status_message.append(score_msg)
                get_effective_logger().debug(
                    f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting green to orange (0 < score < 100)'
                )
            elif object_state == "red":
                # Downgrade red to orange if score < 100
                # Only apply score-based downgrade if the red state is NOT due to outliers
                # (outliers with score_outliers >= 100 should still be red)
                if isOutlier != 1:
                    object_state = "orange"
                    # Add status message about score when downgrading
                    score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                    if score_outliers is not None and score_outliers > 0:
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                    status_message.append(score_msg)
                    get_effective_logger().debug(
                        f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", downgrading red to orange (non-outlier anomalies only)'
                    )
                else:
                    # If outlier is present but score_outliers < 100, it was already set to isOutlier=2
                    # in get_outliers_status, so we can still apply score-based logic
                    if score_outliers is not None and score_outliers < 100:
                        object_state = "orange"
                        # Add status message about score when downgrading due to low outlier score
                        score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                        score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                        status_message.append(score_msg)
                        get_effective_logger().debug(
                            f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'downgrading red to orange (outlier score too low)'
                        )
                    else:
                        get_effective_logger().debug(
                            f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", keeping red state (outlier score >= 100)'
                        )
            else:
                get_effective_logger().debug(
                    f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (0 < score < 100)'
                )
        else:
            # total_score == 0 or total_score <= 0
            # Check if score is 0 due to false_positive (global false positive, not just outliers)
            score_source = record.get("score_source", [])
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            has_false_positive = "false_positive" in score_source_list
            
            if has_false_positive:
                # Score is 0 due to false_positive, set to green (anomaly_reason will remain visible for audit)
                object_state = "green"
                get_effective_logger().debug(
                    f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", score_source="{score_source}", '
                    f'setting state to green (false positive set, score cancelled)'
                )
            else:
                # Check if total_score is 0 because all impact score weights are 0
                # If all components have score 0, then the entity should be green (unless outliers present)
                all_components_zero = True
                if score_definition and "components" in score_definition:
                    components = score_definition.get("components", [])
                    if components:
                        for component in components:
                            component_score = component.get("score", 0)
                            if component_score != 0:
                                all_components_zero = False
                                break
                    # If no components exist but total_score is 0, also consider it as all zero
                    elif not components and total_score == 0:
                        all_components_zero = True
                
                # If all components have score 0 and no outliers (or outliers suppressed), set to green
                if all_components_zero and (score_outliers is None or score_outliers <= 0):
                    object_state = "green"
                    get_effective_logger().debug(
                        f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'setting state to green (all impact score weights are 0, no outliers)'
                    )
                else:
                    get_effective_logger().debug(
                        f'set_dhm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'keeping current state (score == 0)'
                    )

    # If score-based logic changed the state, re-evaluate logical group status
    if (
        logical_group_input_state != object_state
        and object_state in ["green", "red"]
        and record.get("object_group_key")
    ):
        (
            isUnderLogicalGroup,
            LogicalGroupStateInAlert,
            LogicalGroupMsg,
        ) = get_and_manage_logical_group_status(
            splunkd_uri,
            session_key,
            tenant_id,
            record.get("object"),
            object_state,
            record.get("object_group_key"),
            object_logical_group_dict,
        )

        if object_state == "red" and isUnderLogicalGroup is True:
            if LogicalGroupStateInAlert is False:
                object_state = "blue"

    #
    # Out of monitoring days and hours management (post-scoring)
    # Monitoring time policy takes precedence over scoring — entities outside
    # their monitoring window must never be promoted to red by scoring logic
    #
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    # define anomaly_reason
    if object_state == "green":
        status_message.append(isUnderDelayMessage)
        status_message.append(isUnderLatencyMessage)

        # Check if false positive is set - if so, preserve anomaly reasons from score_definition
        score_source = record.get("score_source", [])
        score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
        has_false_positive = "false_positive" in score_source_list

        if has_false_positive and score_definition and "components" in score_definition:
            # Extract anomaly reasons from score_definition components
            for component in score_definition.get("components", []):
                component_type = component.get("type")
                if component_type:
                    mapped_reason = get_anomaly_reason_from_component_type(component_type)
                    if mapped_reason and mapped_reason not in anomaly_reason:
                        anomaly_reason.append(mapped_reason)
            # If no components found, still add "none"
            if not anomaly_reason:
                anomaly_reason.append("none")
        else:
            anomaly_reason.append("none")

        # if in a logical group, add the logical group message
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)

    else:
        # Check for outliers: either isOutlier == 1 (traditional) or score_outliers > 0 (hybrid scoring)
        if isOutlier == 1 or (score_outliers is not None and score_outliers > 0):
            # Always add outlier reasons when outliers are present (either traditional or hybrid scoring).
            # When the latest ML monitor cycle has cleared isOutlierReason but score_outliers (24h cumulative)
            # still indicates past outliers, fall back to the cached lastIsOutlierReason — see helper docstring.
            outlier_msg, _outlier_used_cached = build_outlier_reason_status_message(
                record, score_outliers
            )
            if outlier_msg:
                status_message.append(outlier_msg)
            # Add ml_outliers_detection to anomaly_reason for all outlier cases
            if "ml_outliers_detection" not in anomaly_reason:
                anomaly_reason.append("ml_outliers_detection")
            
            # Add score context message for red state with high outlier score (>= 100)
            # Note: orange state score messages are already added during score-based state transitions above
            if score_outliers is not None and score_outliers >= 100:
                base_score = float(score) if score is not None else 0.0
                total = float(total_score) if total_score is not None else score_outliers
                status_message.append(
                    f"Entity has an impact score of {total:.1f} (base score: {base_score:.1f}), which is 100 or above. "
                    f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    f"This indicates critical anomalies warranting an alert status."
                )

        if isFuture is True:
            status_message.append(isFutureMsg)
            anomaly_reason.append("future_over_tolerance")

        # Monitoring time policy, add the message first then the anomaly reason
        if isUnderMonitoring is False:
            status_message.append(isUnderMonitoringMsg)
            # Use new monitoring anomaly reason if provided
            if monitoring_anomaly_reason:
                anomaly_reason.append(monitoring_anomaly_reason)

        if isUnderLatencyAlert is True:
            status_message.append(isUnderLatencyMessage)
            anomaly_reason.append("lag_threshold_breached")

        if isUnderDelayAlert is True:
            status_message.append(isUnderDelayMessage)
            if delay_is_variable:
                anomaly_reason.append("variable_delay_threshold_breached")
            else:
                anomaly_reason.append("delay_threshold_breached")

        # logical group
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)
            anomaly_reason.append("in_logical_group")

    # Fallback: manual score influence raised total_score > 0 but no actual
    # anomaly was detected — populate status_message / anomaly_reason so the
    # UI can explain the non-green state.
    apply_manual_score_without_anomaly_fallback(
        record,
        score_definition,
        total_score,
        score,
        status_message,
        anomaly_reason,
        object_state,
    )

    # form status_message_json
    status_message_json["status_message"] = status_message
    # deduplicate anomaly_reason
    anomaly_reason = list(set(anomaly_reason))
    status_message_json["anomaly_reason"] = anomaly_reason
    
    # Add score information to status_message_json for UI display (sorted alphabetically)
    # Use total_score if calculated (hybrid scoring), otherwise use base score
    if total_score is not None:
        status_message_json["score"] = float(total_score)
        # Update record score to reflect the calculated total_score for UI consistency
        record["score"] = float(total_score)
        # Add score definition for drilldown modal
        if score_definition:
            status_message_json["score_definition"] = score_definition
            record["score_definition"] = json.dumps(score_definition) if isinstance(score_definition, dict) else score_definition
    elif score is not None:
        status_message_json["score"] = float(score)
    if score_outliers is not None:
        status_message_json["score_outliers"] = float(score_outliers)
    if total_score is not None:
        status_message_json["total_score"] = float(total_score)

    # get disruption_duration
    if not disruption_queue_record:
        record["disruption_min_time_sec"] = 0

    else:
        logger.debug(
            f'disruption_queue_record="{disruption_queue_record}", getting disruption_duration'
        )

        disruption_object_state = disruption_queue_record.get("object_state", "green")
        try:
            disruption_min_time_sec = int(
                disruption_queue_record.get("disruption_min_time_sec", 0)
            )
        except:
            disruption_min_time_sec = 0
        # add to the record
        record["disruption_min_time_sec"] = disruption_min_time_sec

        try:
            disruption_start_epoch = float(
                disruption_queue_record.get("disruption_start_epoch", 0)
            )
        except:
            disruption_start_epoch = 0

        # Case 1: Entity is no longer in alert state (not red)
        if object_state != "red":
            # Only update if we were previously tracking a disruption
            if disruption_object_state == "red":
                disruption_queue_record["object_state"] = object_state
                disruption_queue_record["disruption_start_epoch"] = 0
                disruption_queue_record["mtime"] = time.time()

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")
            return (
                object_state,
                status_message,
                status_message_json,
                anomaly_reason,
                splk_dhm_alerting_policy,
            )

        # Case 2: Entity is in alert state (red)
        if object_state == "red":
            current_time = time.time()

            # If this is a new disruption, start tracking it
            if disruption_object_state != "red":
                disruption_queue_record["object_state"] = "red"
                disruption_queue_record["disruption_start_epoch"] = current_time
                disruption_queue_record["mtime"] = current_time

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")

                # For new disruptions, if min time is set, show as blue with message
                if disruption_min_time_sec > 0:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is 0 which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message
                return (
                    object_state,
                    status_message,
                    status_message_json,
                    anomaly_reason,
                    splk_dhm_alerting_policy,
                )

            # If we're already tracking a disruption, check duration
            if disruption_min_time_sec > 0:
                try:
                    disruption_duration = current_time - disruption_start_epoch
                except Exception as e:
                    logger.error(f"error calculating disruption_duration: {e}")
                    disruption_duration = 0

                # If duration hasn't breached threshold, show as blue with message
                if disruption_duration < disruption_min_time_sec:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is {convert_seconds_to_duration(disruption_duration)} which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message

    # anomaly_reason sanitify check, if the list has more than 1 item, and contains "none", remove it
    if isinstance(anomaly_reason, list):
        if len(anomaly_reason) > 1 and "none" in anomaly_reason:
            anomaly_reason.remove("none")

    # return
    get_effective_logger().debug(
        f'set_dhm_status, object="{record.get("object")}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
    )

    return (
        object_state,
        status_message,
        status_message_json,
        anomaly_reason,
        splk_dhm_alerting_policy,
    )


def set_mhm_status(
    logger,
    splunkd_uri,
    session_key,
    tenant_id,
    record,
    metric_details,
    isFuture,
    isFutureMsg,
    isUnderMonitoring,
    isUnderMonitoringMsg,
    object_logical_group_dict,
    disruption_queue_collection,
    disruption_queue_record,
    source_handler=None,
    monitoring_anomaly_reason=None,
    score=None,
    score_outliers=None,
    vtenant_account=None,
):
    """
    Create a function called set_mhm_status:
    - arguments: record, isFuture, isFutureMsg, isUnderLogicalGroup, LogicalGroupStateInAlert
    - returns:
        object_state (string): blue, orange, green, red
        anomaly_reason (list): list of short code reasons why the object is in anomaly
        status_message (list): list of long description reasons why the object is in anomaly
    - behaviour:
        object_state:
            green if:
                all metric caterogies are green
            blue if:
                Any of the condition above is not met, but isUnderLogicalGroup is True and LogicalGroupStateInAlert is True
            orange if:
                All green conditions are met except for isFuture which would be True
            red if:
                Any of the green conditions are not met, and blue conditions and orange conditions are not met
        anomaly_reason:
            if object_state is green, anomnaly_reason is None
            Otherwise, anomaly_reason is a list containing the reasons why the object is in anomaly
    """

    # init status_message and anomaly_reason
    status_message = []
    anomaly_reason = []

    # init status_message_json
    status_message_json = {}

    # define object_state
    object_state = "green"

    #
    # Logical group management
    #

    (
        isUnderLogicalGroup,
        LogicalGroupStateInAlert,
        LogicalGroupMsg,
    ) = get_and_manage_logical_group_status(
        splunkd_uri,
        session_key,
        tenant_id,
        record.get("object"),
        object_state,
        record.get("object_group_key"),
        object_logical_group_dict,
    )

    # log debug
    get_effective_logger().debug(
        f'function get_and_manage_logical_group_status: object="{record.get("object")}", object_state="{object_state}", object_group_key="{record.get("object_group_key")}", isUnderLogicalGroup="{isUnderLogicalGroup}", LogicalGroupStateInAlert="{LogicalGroupStateInAlert}", LogicalGroupMsg="{LogicalGroupMsg}"'
    )

    # Update object_logical_group_dict to reflect the current state after KVstore update
    # This ensures re-evaluation uses fresh data instead of stale dict
    if isUnderLogicalGroup and object_logical_group_dict:
        object_name = record.get("object")
        # Normalize the lists to ensure consistency
        members_green = normalize_logical_group_members(
            object_logical_group_dict.get("object_group_members_green", [])
        )
        members_red = normalize_logical_group_members(
            object_logical_group_dict.get("object_group_members_red", [])
        )
        
        # Update based on current state (matching the logic in get_and_manage_logical_group_status)
        if object_state == "green":
            if object_name not in members_green:
                members_green.append(object_name)
            if object_name in members_red:
                members_red.remove(object_name)
        else:  # red or blue
            if object_name not in members_red:
                members_red.append(object_name)
            if object_name in members_green:
                members_green.remove(object_name)
        
        # Update the dict with normalized lists
        object_logical_group_dict["object_group_members_green"] = members_green
        object_logical_group_dict["object_group_members_red"] = members_red

    # Convert metric_details to a list if it is a string
    if isinstance(metric_details, str):
        metric_details = [metric_details]

    # counters
    count_red = 0
    count_green = 0
    metrics_red_list = []

    # splk_dhm_st_summary can actually be a list
    if isinstance(metric_details, list):
        for item_str in metric_details:
            try:
                new_dict = ast.literal_eval(item_str)

                # Iterate through the inner dictionaries
                for inner_dict in new_dict.values():
                    if inner_dict.get("state") == "red":
                        count_red += 1
                        anomaly_reason.append("delay_threshold_breached")
                        metrics_red_list.append(
                            f'(idx: {inner_dict.get("idx")}, metrics: {inner_dict.get("metric_category")}, anomaly_reason: delay_threshold_breached)'
                        )

                    elif inner_dict.get("state") == "green":
                        count_green += 1

            except Exception as e:
                get_effective_logger().error(
                    f"Error in processing item_str: {item_str}. Error: {str(e)}"
                )

        get_effective_logger().debug(
            f'object="{record.get("object")}", count_red={count_red}, count_green={count_green}'
        )

        # turn metrics_red_list into a pipe separated string
        metrics_red_list = "|".join(metrics_red_list)

        # Decision making based on the counts of red and green states
        if count_red > 0:
            object_state = "red"
            status_message.append(
                f"One or more metric categories are in alert for this entity, metrics in alert: {metrics_red_list}"
            )
        else:
            # Use object_state as it is
            pass

    # if all metrics are in alert, then object_state is red
    if count_green == 0:
        object_state = "red"
        status_message.append("all metric categories are in alert for this entity")

    # if object_state is red but isUnderLogicalGroup is True and LogicalGroupStateInAlert is False, then object_state is blue
    if object_state == "red" and isUnderLogicalGroup is True:
        if LogicalGroupStateInAlert is False:
            object_state = "blue"

    # if object_state is not red or blue but isFuture is True, then object_state is orange
    if object_state not in ["red", "blue"]:
        if isFuture is True:
            object_state = "orange"

    # if object_state is red but isUnderMonitoring is False, then object_state is orange
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    # Capture state after all MHM-specific logic but before scoring
    # This ensures we can detect if scoring changes the state and re-evaluate logical groups
    logical_group_input_state = object_state

    #
    # Hybrid scoring: Apply score-based logic
    # MHM doesn't have outliers, only future tolerance and metric alerts
    #
    total_score = None
    score_definition = {}
    if score is not None:
        # Calculate total score with static increments for anomalies
        base_score = float(score) if score is not None else 0.0
        total_score = base_score
        
        # Build score definition to track where the score comes from
        # Convert base_score to integer if it's a whole number, otherwise keep as float
        if base_score == int(base_score):
            score_definition["base_score"] = int(base_score)
        else:
            score_definition["base_score"] = base_score
        score_definition["components"] = []
        
        # Add static increments for each anomaly type (using VT-specific impact scores)
        if count_red > 0:
            increment = get_impact_score(vtenant_account, "impact_score_mhm_metric_alert", 100)
            total_score += increment
            score_definition["components"].append({
                "type": "metric_alert",
                "score": increment,
                "description": "One or more metric categories in alert"
            })
        
        if isFuture is True:
            increment = get_impact_score(vtenant_account, "impact_score_mhm_future_tolerance_breach", 36)
            total_score += increment
            score_definition["components"].append({
                "type": "future_tolerance_breach",
                "score": increment,
                "description": "Future tolerance breached"
            })
        
        # Add outlier score if present
        if score_outliers is not None and score_outliers > 0:
            score_definition["score_outliers"] = float(score_outliers)
        
        # Add score sources if available
        score_source = record.get("score_source", [])
        if score_source:
            score_definition["score_source"] = score_source if isinstance(score_source, list) else [score_source]
        
        # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score
        
        # Apply score-based logic:
        # - If total_score >= 100: entity should be red (if not already red due to other reasons, keep current state)
        # - If total_score > 0 and < 100: entity should be orange (even if currently green)
        # - If total_score == 0: keep current state
        
        if total_score >= 100:
            # If score >= 100, ensure entity is red (unless it's blue due to logical group)
            if object_state not in ["red", "blue"]:
                object_state = "red"
                get_effective_logger().debug(
                    f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red (score >= 100)'
                )
            else:
                get_effective_logger().debug(
                    f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (score >= 100)'
                )
        elif total_score > 0 and total_score < 100:
            # If score > 0 and < 100, entity should be orange (even if currently green)
            if object_state == "green":
                object_state = "orange"
                # Add status message about score
                score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                # Add outlier context if outliers are present
                if score_outliers is not None and score_outliers > 0:
                    score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                status_message.append(score_msg)
                get_effective_logger().debug(
                    f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting green to orange (0 < score < 100)'
                )
            elif object_state == "red":
                # Downgrade red to orange if score < 100
                # Only apply score-based downgrade if the red state is NOT due to high outlier score
                # (outliers with score_outliers >= 100 should keep the entity red)
                if score_outliers is not None and score_outliers >= 100:
                    get_effective_logger().debug(
                        f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", keeping red state (outlier score >= 100)'
                    )
                else:
                    object_state = "orange"
                    # Add status message about score when downgrading
                    score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                    if score_outliers is not None and score_outliers > 0:
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                    status_message.append(score_msg)
                    get_effective_logger().debug(
                        f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", downgrading red to orange'
                    )
            else:
                get_effective_logger().debug(
                    f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (0 < score < 100)'
                )
        else:
            # total_score == 0 or total_score <= 0
            # Check if score is 0 due to false_positive (global false positive, not just outliers)
            score_source = record.get("score_source", [])
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            has_false_positive = "false_positive" in score_source_list
            
            if has_false_positive:
                # Score is 0 due to false_positive, set to green (anomaly_reason will remain visible for audit)
                object_state = "green"
                get_effective_logger().debug(
                    f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", score_source="{score_source}", '
                    f'setting state to green (false positive set, score cancelled)'
                )
            else:
                # Check if total_score is 0 because all impact score weights are 0
                # If all components have score 0, then the entity should be green (unless outliers present)
                all_components_zero = True
                if score_definition and "components" in score_definition:
                    components = score_definition.get("components", [])
                    if components:
                        for component in components:
                            component_score = component.get("score", 0)
                            if component_score != 0:
                                all_components_zero = False
                                break
                
                # If all components have score 0 and no outliers, set to green
                if all_components_zero and (score_outliers is None or score_outliers <= 0):
                    object_state = "green"
                    get_effective_logger().debug(
                        f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'setting state to green (all impact score weights are 0, no outliers)'
                    )
                else:
                    # total_score == 0, keep current state
                    get_effective_logger().debug(
                        f'set_mhm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", keeping current state (score == 0)'
                    )

    # If score-based logic changed the state, re-evaluate logical group status
    if (
        logical_group_input_state != object_state
        and object_state in ["green", "red"]
        and record.get("object_group_key")
    ):
        (
            isUnderLogicalGroup,
            LogicalGroupStateInAlert,
            LogicalGroupMsg,
        ) = get_and_manage_logical_group_status(
            splunkd_uri,
            session_key,
            tenant_id,
            record.get("object"),
            object_state,
            record.get("object_group_key"),
            object_logical_group_dict,
        )

        if object_state == "red" and isUnderLogicalGroup is True:
            if LogicalGroupStateInAlert is False:
                object_state = "blue"

    #
    # Out of monitoring days and hours management (post-scoring)
    # Monitoring time policy takes precedence over scoring — entities outside
    # their monitoring window must never be promoted to red by scoring logic
    #
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    # define anomaly_reason
    if object_state == "green":
        status_message.append(
            "All metric categories are in normal state for this entity"
        )

        # Check if false positive is set - if so, preserve anomaly reasons from score_definition
        score_source = record.get("score_source", [])
        score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
        has_false_positive = "false_positive" in score_source_list
        
        if has_false_positive and score_definition and "components" in score_definition:
            # Extract anomaly reasons from score_definition components
            for component in score_definition.get("components", []):
                component_type = component.get("type")
                if component_type:
                    mapped_reason = get_anomaly_reason_from_component_type(component_type)
                    if mapped_reason and mapped_reason not in anomaly_reason:
                        anomaly_reason.append(mapped_reason)
            # If no components found, still add "none"
            if not anomaly_reason:
                anomaly_reason.append("none")
        else:
            anomaly_reason.append("none")

        # if in a logical group, add the logical group message
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)

    else:
        # Check for outliers: score_outliers > 0 (hybrid scoring)
        if score_outliers is not None and score_outliers > 0:
            # Add outlier reasons when outliers are present.
            # When the latest ML monitor cycle has cleared isOutlierReason but score_outliers (24h cumulative)
            # still indicates past outliers, fall back to the cached lastIsOutlierReason — see helper docstring.
            outlier_msg, _outlier_used_cached = build_outlier_reason_status_message(
                record, score_outliers
            )
            if outlier_msg:
                status_message.append(outlier_msg)
            # Add ml_outliers_detection to anomaly_reason for all outlier cases
            if "ml_outliers_detection" not in anomaly_reason:
                anomaly_reason.append("ml_outliers_detection")

            # Add score context message for red state with high outlier score (>= 100)
            # Note: orange state score messages are already added during score-based state transitions above
            if score_outliers >= 100:
                base_score = float(score) if score is not None else 0.0
                total = float(total_score) if total_score is not None else score_outliers
                status_message.append(
                    f"Entity has an impact score of {total:.1f} (base score: {base_score:.1f}), which is 100 or above. "
                    f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    f"This indicates critical anomalies warranting an alert status."
                )

        if isFuture is True:
            status_message.append(isFutureMsg)
            anomaly_reason.append("future_over_tolerance")

        # Monitoring time policy, add the message first then the anomaly reason
        if isUnderMonitoring is False:
            status_message.append(isUnderMonitoringMsg)
            # Use new monitoring anomaly reason if provided, otherwise use legacy
            if monitoring_anomaly_reason:
                anomaly_reason.append(monitoring_anomaly_reason)
            else:
                anomaly_reason.append("out_of_monitoring_times")

        # logical group
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)
            anomaly_reason.append("in_logical_group")

    # Fallback: manual score influence raised total_score > 0 but no actual
    # anomaly was detected — populate status_message / anomaly_reason so the
    # UI can explain the non-green state.
    apply_manual_score_without_anomaly_fallback(
        record,
        score_definition,
        total_score,
        score,
        status_message,
        anomaly_reason,
        object_state,
    )

    # Deduplicate anomaly_reason before setting it in status_message_json
    # This prevents duplicates (e.g., delay_threshold_breached added multiple times for multiple metrics)
    if isinstance(anomaly_reason, list):
        if len(anomaly_reason) > 1 and "none" in anomaly_reason:
            anomaly_reason.remove("none")
        # deduplicate anomaly_reason to avoid duplicates
        anomaly_reason = list(set(anomaly_reason))

    # form status_message_json
    status_message_json["status_message"] = status_message
    status_message_json["anomaly_reason"] = anomaly_reason

    # Add score information to status_message_json for UI display (sorted alphabetically)
    # Use total_score if calculated (hybrid scoring), otherwise use base score
    if total_score is not None:
        status_message_json["score"] = float(total_score)
        # Update record score to reflect the calculated total_score for UI consistency
        record["score"] = float(total_score)
        # Add score definition for drilldown modal
        if score_definition:
            status_message_json["score_definition"] = score_definition
            record["score_definition"] = json.dumps(score_definition) if isinstance(score_definition, dict) else score_definition
    elif score is not None:
        status_message_json["score"] = float(score)
    if score_outliers is not None:
        status_message_json["score_outliers"] = float(score_outliers)
    if total_score is not None:
        status_message_json["total_score"] = float(total_score)

    # get disruption_duration
    if not disruption_queue_record:
        record["disruption_min_time_sec"] = 0

    else:

        logger.debug(
            f'disruption_queue_record="{disruption_queue_record}", getting disruption_duration'
        )

        disruption_object_state = disruption_queue_record.get("object_state", "green")
        try:
            disruption_min_time_sec = int(
                disruption_queue_record.get("disruption_min_time_sec", 0)
            )
        except:
            disruption_min_time_sec = 0
        # add to the record
        record["disruption_min_time_sec"] = disruption_min_time_sec

        try:
            disruption_start_epoch = float(
                disruption_queue_record.get("disruption_start_epoch", 0)
            )
        except:
            disruption_start_epoch = 0

        # Case 1: Entity is no longer in alert state (not red)
        if object_state != "red":
            # Only update if we were previously tracking a disruption
            if disruption_object_state == "red":
                disruption_queue_record["object_state"] = object_state
                disruption_queue_record["disruption_start_epoch"] = 0
                disruption_queue_record["mtime"] = time.time()

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")
            return object_state, status_message, status_message_json, anomaly_reason

        # Case 2: Entity is in alert state (red)
        if object_state == "red":
            current_time = time.time()

            # If this is a new disruption, start tracking it
            if disruption_object_state != "red":
                disruption_queue_record["object_state"] = "red"
                disruption_queue_record["disruption_start_epoch"] = current_time
                disruption_queue_record["mtime"] = current_time

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")

                # For new disruptions, if min time is set, show as blue with message
                if disruption_min_time_sec > 0:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is 0 which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message
                return object_state, status_message, status_message_json, anomaly_reason

            # If we're already tracking a disruption, check duration
            if disruption_min_time_sec > 0:
                try:
                    disruption_duration = current_time - disruption_start_epoch
                except Exception as e:
                    logger.error(f"error calculating disruption_duration: {e}")
                    disruption_duration = 0

                # If duration hasn't breached threshold, show as blue with message
                if disruption_duration < disruption_min_time_sec:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is {convert_seconds_to_duration(disruption_duration)} which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message

    # anomaly_reason sanitify check, if the list has more than 1 item, and contains "none", remove it
    # Also ensure status_message_json is updated with deduplicated list (safety check)
    if isinstance(anomaly_reason, list):
        if len(anomaly_reason) > 1 and "none" in anomaly_reason:
            anomaly_reason.remove("none")
        # deduplicate anomaly_reason to avoid duplicates (e.g., delay_threshold_breached added multiple times for multiple metrics)
        anomaly_reason = list(set(anomaly_reason))
        # Update status_message_json to ensure it has the deduplicated list
        status_message_json["anomaly_reason"] = anomaly_reason

    # return
    get_effective_logger().debug(
        f'set_mhm_status, object="{record.get("object")}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
    )

    return object_state, status_message, status_message_json, anomaly_reason


def set_flx_status(
    logger,
    splunkd_uri,
    session_key,
    tenant_id,
    record,
    isOutlier,
    isUnderMonitoring,
    isUnderMonitoringMsg,
    object_logical_group_dict,
    threshold_alert,
    threshold_messages,
    disruption_queue_collection,
    disruption_queue_record,
    source_handler=None,
    monitoring_anomaly_reason=None,
    score=None,
    score_outliers=None,
    threshold_scores=None,
    vtenant_account=None,
):
    """
    Create a function called set_flx_status:
    - arguments: record, isOutlier, isFuture, isUnderMonitoring, isUnderMonitoringMsg, isUnderLogicalGroup, LogicalGroupStateInAlert, isUnderLatencyAlert, isUnderLatencyMessage, isUnderDelayAlert, isUnderDelayMessage
    - returns:
        object_state (string): blue, orange, green, red
        anomaly_reason (list): list of short code reasons why the object is in anomaly
        status_message (list): list of long description reasons why the object is in anomaly
    - behaviour:
        object_state:
            green if:
                isOutlier is 1
                isFuture is False
                isUnderMonitoring is True
                if isUnderLogicalGroup is True, then LogicalGroupStateInAlert must be False
                isUnderLatencyAlert is False
                isUnderDelayAlert is False
            blue if:
                Any of the condition above is not met, but isUnderLogicalGroup is True and LogicalGroupStateInAlert is True
            orange if:
                All green conditions are met except for isFuture which would be True
            red if:
                Any of the green conditions are not met, and blue conditions and orange conditions are not met
        anomaly_reason:
            if object_state is green, anomnaly_reason is None
            Otherwise, anomaly_reason is a list containing the reasons why the object is in anomaly
    """

    # init status_message and anomaly_reason
    status_message = []
    anomaly_reason = []

    # upstream anomaly_reason
    # Note: use `or []` rather than dict.get default — the KV record may have
    # the key present with an explicit None value (e.g. from partial patches
    # performed by label/impact-score updates), and dict.get only falls back
    # to the default when the key is missing, not when the stored value is None.
    # Without this guard, `"x" in upstream_anomaly_reason` raises
    # `argument of type 'NoneType' is not iterable`.
    upstream_anomaly_reason = record.get("anomaly_reason") or []
    if isinstance(upstream_anomaly_reason, str):
        upstream_anomaly_reason = [upstream_anomaly_reason]

    # init status_message_json
    status_message_json = {}

    # status and status_description are used to compose the anomaly_reason
    status_raw = record.get("status", "unknown")
    try:
        status = int(status_raw)
    except (ValueError, TypeError):
        # status remains as its raw value for display purposes but is not a valid integer
        status = status_raw
    status_description = record.get("status_description", "unknown")
    
    # Get upstream_status - the live value from the current search run
    # This is stored by the decision maker before calling set_flx_status
    # See GitHub issue: https://github.com/trackme-limited/trackme-report-issues/issues/1513
    upstream_status = record.get("upstream_status")
    if upstream_status is not None:
        try:
            upstream_status = int(upstream_status)
        except (ValueError, TypeError):
            upstream_status = None
    
    # Parse metrics for use in various checks
    metrics = record.get("metrics", {})
    if isinstance(metrics, str):
        try:
            metrics = json.loads(metrics)
        except Exception:
            metrics = {}
    
    # Determine original_upstream_status for status_not_met logic
    # This is the status we use to decide if status_not_met should be added/removed
    original_upstream_status = None
    
    # STEP 1: Get base value from upstream_status (live from current search) or fallbacks
    if upstream_status is not None:
        original_upstream_status = upstream_status
        logger.debug(
            f'set_flx_status: object="{record.get("object")}", '
            f'using upstream_status={upstream_status} as original_upstream_status (live value from current search)'
        )
    else:
        # Fallback to metrics.status or status field
        if isinstance(metrics, dict) and "status" in metrics:
            try:
                original_upstream_status = int(metrics["status"])
            except (ValueError, TypeError):
                pass
        
        if original_upstream_status is None:
            # Only use the status field if it was successfully converted to an integer
            if isinstance(status, int):
                original_upstream_status = status
            else:
                logger.debug(
                    f'set_flx_status: object="{record.get("object")}", '
                    f'status field is not a valid integer ("{status}"), original_upstream_status remains None'
                )
        
        logger.debug(
            f'set_flx_status: object="{record.get("object")}", '
            f'upstream_status not available, using fallback original_upstream_status={original_upstream_status}'
        )
    
    # STEP 2: Special handling for converging trackers - pct_availability override
    # This applies REGARDLESS of whether we have upstream_status
    # If pct_availability >= 100% but status = 2, override to 1 (100% always means healthy)
    flx_type = record.get("flx_type", "")
    is_converging_tracker = False
    if flx_type == "converging":
        is_converging_tracker = True
    else:
        # Also check extra_attributes structure as a fallback detection method
        conv_extra_attributes = record.get("extra_attributes", {})
        if isinstance(conv_extra_attributes, str):
            try:
                conv_extra_attributes = json.loads(conv_extra_attributes)
            except Exception:
                conv_extra_attributes = {}
        if isinstance(conv_extra_attributes, dict) and "all_entities" in conv_extra_attributes:
            is_converging_tracker = True
    
    if is_converging_tracker:
        try:
            pct_availability = None
            if isinstance(metrics, dict) and "pct_availability" in metrics:
                pct_availability = float(metrics.get("pct_availability", 0))
            
            # Override: If pct_availability >= 100% but original_upstream_status = 2, set to 1
            # (100% availability always means healthy, regardless of stale status)
            if pct_availability is not None and pct_availability >= 100.0 and original_upstream_status == 2:
                logger.debug(
                    f'set_flx_status, converging tracker override: object="{record.get("object")}", '
                    f'pct_availability="{pct_availability}" (>= 100%) but original_upstream_status=2, '
                    f'overriding to original_upstream_status=1'
                )
                original_upstream_status = 1
            else:
                logger.debug(
                    f'set_flx_status, converging tracker: object="{record.get("object")}", '
                    f'pct_availability="{pct_availability}", original_upstream_status="{original_upstream_status}"'
                )
        except (ValueError, TypeError) as e:
            logger.debug(
                f'set_flx_status, converging tracker but failed to parse pct_availability: '
                f'object="{record.get("object")}", error="{str(e)}", keeping original_upstream_status="{original_upstream_status}"'
            )

    # for flx, object_state can be defined upstream based on the status
    object_state = "unknown"
    if status == 1:
        object_state = "green"
    elif status == 2:
        object_state = "red"
    elif status == 3:
        object_state = "orange"
    else:
        pass

    # for flx, attempt to retrieve extra_attributes, if present attempt to load as an object
    extra_attributes = record.get("extra_attributes", {})
    if isinstance(extra_attributes, str):
        if len(extra_attributes) > 0:
            try:
                extra_attributes = json.loads(extra_attributes)
            except Exception as e:
                logger.error(
                    f"Error in processing extra_attributes: {extra_attributes}. Error: {str(e)}"
                )
        else:
            extra_attributes = {}

    # if source_handler is trackmedecisionmaker, check if status_not_met should be added
    # Use original_upstream_status (not status) to be consistent with converging tracker override logic
    # (lines 3143-3144 can override original_upstream_status to 1 when pct_availability >= 100%)
    # Only add status_not_met when original_upstream_status is a valid integer and explicitly not 1
    # If original_upstream_status is None (unknown/invalid), do NOT assume status_not_met
    if source_handler == "trackmedecisionmaker":
        if original_upstream_status is not None and original_upstream_status != 1 and not (
            len(upstream_anomaly_reason) == 1
            and upstream_anomaly_reason[0] == "inactive"
        ):
            if "status_not_met" not in upstream_anomaly_reason:
                upstream_anomaly_reason.append("status_not_met")

    get_effective_logger().debug(
        f'source_handler="{source_handler}", entering set_flx_status, object="{record.get("object")}", object_state="{object_state}", status="{status}", upstream_anomaly_reason="{upstream_anomaly_reason}"'
    )

    #
    # Threshold alert management
    #

    # if threshold_alert is True, then object_state is red
    record["threshold_alert"] = threshold_alert
    record["threshold_messages"] = threshold_messages
    if threshold_alert == 1:
        object_state = "red"
        status = 2
        anomaly_reason.append("threshold_alert")
        for threshold_message in threshold_messages:
            status_message.append(threshold_message)
        # in record, update status_description and status_description_short with a CSV string of the threshold_messages
        record["status_description"] = ",".join(threshold_messages)
        record["status_description_short"] = ",".join(threshold_messages)

    else:

        # remove threshold_alert from upstream_anomaly_reason, if present
        if "threshold_alert" in upstream_anomaly_reason:
            upstream_anomaly_reason.remove("threshold_alert")

        # if the unique anomaly reason was threshold_alert, then object_state is green
        # BUT only if original_upstream_status is 1 (good status)
        # If original_upstream_status != 1 (status_not_met), we should keep the red/orange state
        if len(upstream_anomaly_reason) == 0 and original_upstream_status == 1:
            object_state = "green"
            status = 1

    #
    # Logical group management
    #

    (
        isUnderLogicalGroup,
        LogicalGroupStateInAlert,
        LogicalGroupMsg,
    ) = get_and_manage_logical_group_status(
        splunkd_uri,
        session_key,
        tenant_id,
        record.get("object"),
        object_state,
        record.get("object_group_key"),
        object_logical_group_dict,
    )

    # log debug
    logger.debug(
        f'function get_and_manage_logical_group_status: object="{record.get("object")}", object_state="{object_state}", object_group_key="{record.get("object_group_key")}", isUnderLogicalGroup="{isUnderLogicalGroup}", LogicalGroupStateInAlert="{LogicalGroupStateInAlert}", LogicalGroupMsg="{LogicalGroupMsg}"'
    )

    # get status_description_short and ensures it always has a value
    status_description_short = record.get("status_description_short", None)
    if not status_description_short:
        record["status_description_short"] = status_description
        status_description_short = status_description

    # Verify isOutlier
    # Only set red if isOutlier == 1 AND score_outliers > 0 (or score_outliers is None for legacy)
    # If score_outliers <= 0, outliers are suppressed (false positive) and should not cause red state
    if isOutlier == 1:
        if score_outliers is not None:
            if score_outliers > 0:
                # Outliers present with positive score
                if score_outliers >= 100:
                    object_state = "red"
                    status = 2
                else:
                    # score_outliers > 0 and < 100, set to orange
                    object_state = "orange"
                    status = 3
            # If score_outliers <= 0, don't set state to red/orange (outliers suppressed)
        else:
            # Legacy behavior: if score_outliers is not provided, use isOutlier
            object_state = "red"
            status = 2
    else:
        pass

    # if object_state is red but isUnderMonitoring is False, then object_state is orange
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"
            status = 3

    #
    # Hybrid scoring: Apply score-based logic
    # Outliers are handled separately via score_outliers in get_outliers_status
    #
    total_score = None
    score_definition = {}
    if score is not None:
        # Calculate total score with static increments for anomalies
        base_score = float(score) if score is not None else 0.0
        total_score = base_score
        
        # Build score definition to track where the score comes from
        # Convert base_score to integer if it's a whole number, otherwise keep as float
        if base_score == int(base_score):
            score_definition["base_score"] = int(base_score)
        else:
            score_definition["base_score"] = base_score
        score_definition["components"] = []
        
        # Add static increments for each anomaly type
        if threshold_alert == 1:
            # Use threshold scores if provided, otherwise default to 100
            if threshold_scores and len(threshold_scores) > 0:
                # Sum all threshold scores (multiple thresholds can be breached)
                increment = sum(threshold_scores)
            else:
                # Default to 100 for backward compatibility
                increment = 100
            total_score += increment
            score_definition["components"].append({
                "type": "threshold_breach",
                "score": increment,
                "description": "Threshold alert breached"
            })
        
        # Add outlier score if present
        if score_outliers is not None and score_outliers > 0:
            score_definition["score_outliers"] = float(score_outliers)
        
        # Add score sources if available
        score_source = record.get("score_source", [])
        if score_source:
            score_definition["score_source"] = score_source if isinstance(score_source, list) else [score_source]
        
        # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score
        
        # Apply score-based logic:
        # - If total_score >= 100: entity should be red (if not already red due to other reasons, keep current state)
        # - If total_score > 0 and < 100: entity should be orange (even if currently green)
        # - If total_score == 0: keep current state
        
        if total_score >= 100:
            # If score >= 100, ensure entity is red (unless it's blue due to logical group)
            if object_state not in ["red", "blue"]:
                object_state = "red"
                status = 2
                get_effective_logger().debug(
                    f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red (score >= 100)'
                )
            else:
                get_effective_logger().debug(
                    f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (score >= 100)'
                )
        elif total_score > 0 and total_score < 100:
            # If score > 0 and < 100, entity should be orange (even if currently green)
            if object_state == "green":
                object_state = "orange"
                status = 3
                # Add status message about score
                score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                # Add outlier context if outliers are present
                if score_outliers is not None and score_outliers > 0:
                    score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                status_message.append(score_msg)
                get_effective_logger().debug(
                    f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting green to orange (0 < score < 100)'
                )
            elif object_state == "red":
                # Downgrade red to orange if score < 100
                # Only apply score-based downgrade if the red state is NOT due to outliers
                # (outliers with score_outliers >= 100 should still be red)
                if isOutlier != 1:
                    object_state = "orange"
                    status = 3
                    # Add status message about score when downgrading
                    score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                    if score_outliers is not None and score_outliers > 0:
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                    status_message.append(score_msg)
                    get_effective_logger().debug(
                        f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", downgrading red to orange (non-outlier anomalies only)'
                    )
                else:
                    # If outlier is present but score_outliers < 100, it was already set to isOutlier=2
                    # in get_outliers_status, so we can still apply score-based logic
                    if score_outliers is not None and score_outliers < 100:
                        object_state = "orange"
                        status = 3
                        # Add status message about score when downgrading due to low outlier score
                        score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                        score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                        status_message.append(score_msg)
                        get_effective_logger().debug(
                            f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'downgrading red to orange (outlier score too low)'
                        )
                    else:
                        get_effective_logger().debug(
                            f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", keeping red state (outlier score >= 100)'
                        )
            else:
                get_effective_logger().debug(
                    f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (0 < score < 100)'
                )
        else:
            # total_score == 0 or total_score <= 0
            # Check if score is 0 due to false_positive (global false positive, not just outliers)
            score_source = record.get("score_source", [])
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            has_false_positive = "false_positive" in score_source_list
            
            if has_false_positive:
                # Score is 0 due to false_positive, set to green (anomaly_reason will remain visible for audit)
                object_state = "green"
                status = 1
                get_effective_logger().debug(
                    f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", score_source="{score_source}", '
                    f'setting state to green (false positive set, score cancelled)'
                )
            else:
                # Check if total_score is 0 because all impact score weights are 0
                # If all components have score 0, then the entity should be green (unless outliers present or upstream issues)
                all_components_zero = True
                if score_definition and "components" in score_definition:
                    components = score_definition.get("components", [])
                    if components:
                        for component in components:
                            component_score = component.get("score", 0)
                            if component_score != 0:
                                all_components_zero = False
                                break
                    # If no components exist but total_score is 0, also consider it as all zero
                    elif not components and total_score == 0:
                        all_components_zero = True
                
                # If all components have score 0, no outliers, no threshold alerts, set to green
                # For status_not_met (original_upstream_status == 2), check if its impact score is 0
                # If so, status_not_met should not prevent green state - the impact score is the source of truth
                if (all_components_zero and 
                    (score_outliers is None or score_outliers <= 0) and 
                    threshold_alert != 1):
                    # Check if the only issue is status_not_met with 0 impact score
                    can_be_green = False
                    if original_upstream_status == 1:
                        # Upstream status is good, can be green
                        can_be_green = True
                    elif original_upstream_status == 2:
                        # Upstream status is bad, check if status_not_met impact score is 0
                        status_not_met_score = get_impact_score(vtenant_account, "impact_score_flx_status_not_met", 100)
                        if status_not_met_score == 0:
                            can_be_green = True
                            get_effective_logger().debug(
                                f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                                f'original_upstream_status=2 but status_not_met impact score is 0, allowing green state'
                            )
                    
                    if can_be_green:
                        object_state = "green"
                        status = 1
                        get_effective_logger().debug(
                            f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'threshold_alert="{threshold_alert}", original_upstream_status="{original_upstream_status}", '
                            f'setting state to green (all impact score weights are 0, no outliers)'
                        )
                    else:
                        # Keep current state if status_not_met has a non-zero impact score
                        get_effective_logger().debug(
                            f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'threshold_alert="{threshold_alert}", original_upstream_status="{original_upstream_status}", '
                            f'keeping current state (status_not_met has non-zero impact score)'
                        )
                else:
                    # Keep current state if there are other issues (outliers, thresholds, non-zero components)
                    get_effective_logger().debug(
                        f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'threshold_alert="{threshold_alert}", original_upstream_status="{original_upstream_status}", '
                        f'keeping current state (other issues present)'
                    )
        
        # Safeguard: If original_upstream_status == 2 (status_not_met), ensure state is not green
        # ONLY if the impact score for status_not_met is > 0
        # If the user has set the impact score to 0, they explicitly don't want status_not_met to affect state
        # (false_positive is also an explicit override that should be respected)
        if original_upstream_status == 2 and object_state == "green":
            score_source = record.get("score_source", [])
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            has_false_positive = "false_positive" in score_source_list
            
            # Get the configured impact score for status_not_met directly from tenant settings
            # (not from score_definition which isn't populated yet when object_state is green)
            status_not_met_score = get_impact_score(vtenant_account, "impact_score_flx_status_not_met", 100)
            
            if not has_false_positive and status_not_met_score > 0:
                # Restore red state if upstream status indicates status_not_met AND impact score is configured
                object_state = "red"
                status = 2
                get_effective_logger().debug(
                    f'set_flx_status, safeguard: object="{record.get("object")}", '
                    f'original_upstream_status="{original_upstream_status}", '
                    f'status_not_met_score="{status_not_met_score}", '
                    f'correcting green state back to red (status_not_met detected with non-zero impact score)'
                )
            elif not has_false_positive and status_not_met_score == 0:
                # Safeguard bypassed - add status_not_met to upstream_anomaly_reason for informational purposes
                # This ensures it appears in the final anomaly_reason even though state remains green
                if "status_not_met" not in upstream_anomaly_reason:
                    upstream_anomaly_reason.append("status_not_met")
                get_effective_logger().debug(
                    f'set_flx_status, safeguard bypassed: object="{record.get("object")}", '
                    f'original_upstream_status="{original_upstream_status}", '
                    f'status_not_met_score=0, keeping green state but adding status_not_met to anomaly_reason for visibility'
                )

    # define anomaly_reason
    if object_state == "green":
        status_message_str = f"The entity status is complying with monitoring rules (status: {status}, status_description: {status_description})"
        status_message.append(status_message_str)
        
        # Check if false positive is set - if so, preserve anomaly reasons from score_definition
        score_source = record.get("score_source", [])
        score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
        has_false_positive = "false_positive" in score_source_list
        
        if has_false_positive and score_definition and "components" in score_definition:
            # Extract anomaly reasons from score_definition components
            for component in score_definition.get("components", []):
                component_type = component.get("type")
                if component_type:
                    mapped_reason = get_anomaly_reason_from_component_type(component_type)
                    if mapped_reason and mapped_reason not in anomaly_reason:
                        anomaly_reason.append(mapped_reason)
            # If no components found, still add "none"
            if not anomaly_reason:
                anomaly_reason.append("none")
        elif "status_not_met" in upstream_anomaly_reason and original_upstream_status == 2:
            # Preserve status_not_met for informational purposes when safeguard was bypassed
            # (impact score is 0 but we still want to show the condition exists)
            # Must also verify current status is bad (original_upstream_status == 2) to avoid
            # persisting stale status_not_met after the entity recovers to good status
            anomaly_reason.append("status_not_met")
        else:
            anomaly_reason.append("none")

        # if in a logical group, add the logical group message
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)

    #
    # Inactive entities management
    #

    # get max_sec_inactive
    max_sec_inactive = record.get("max_sec_inactive", 0)
    try:
        max_sec_inactive = int(max_sec_inactive)
    except Exception as e:
        max_sec_inactive = 0

    # get the age in seconds since the latest execution
    sec_since_last_execution = round(
        time.time() - float(record.get("tracker_runtime")), 0
    )
    duration_since_last_execution = convert_seconds_to_duration(
        sec_since_last_execution
    )

    # Check and act
    if float(sec_since_last_execution) > max_sec_inactive and max_sec_inactive > 0:
        status_message_str = f"This entity has been inactive for more than {duration_since_last_execution} (D+HH:MM:SS) and was not actively managed by any tracker, its status was updated automatically by the inactive entities tracker"
        status_message = [status_message_str]
        status_description_short = "entity is red due to inactivity"
        status_description = f"The entity status is red due to inactivity, it was not actively managed by any tracker for more than {duration_since_last_execution} (D+HH:MM:SS)"
        anomaly_reason = ["inactive"]
        object_state = "red"
        status = 2
        # in this case, we need to update the status_description and status_description_short
        record["status_description"] = status_description
        record["status_description_short"] = status_description_short
        record["object_state"] = object_state
        # Add score increment for inactive if scoring is enabled (using VT-specific impact score)
        if score is not None and total_score is not None:
            increment = get_impact_score(vtenant_account, "impact_score_flx_inactive", 100)
            total_score += increment
            score_definition["components"].append({
                "type": "inactive",
                "score": increment,
                "description": "Entity inactive"
            })
            # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score

    #
    # end of inactive entities management
    #

    #
    # Red status due to upstream Flex logic / Orange state
    #

    # Only add status_not_met if the original upstream status from the search indicates a problem
    # (status != 1), not when we're orange/red purely due to score-based logic or outliers
    # status_not_met should only be driven by the hybrid tracker search itself
    # Don't add status_not_met if:
    # 1. Entity is orange/red ONLY due to outliers (regardless of score)
    # 2. Outliers score >= 100 (entity already red due to outliers)
    # 3. Entity is orange/red ONLY due to threshold breaches with score < 100
    # Check if entity is orange/red ONLY due to outliers
    has_outliers_only = (
        isOutlier == 1 
        and score_outliers is not None 
        and not threshold_alert
    )
    
    # Check if outliers score is >= 100 (entity already red due to outliers)
    outliers_score_high = (
        isOutlier == 1 
        and score_outliers is not None 
        and score_outliers >= 100
    )
    
    # Check if entity is orange/red ONLY due to threshold breaches with score < 100
    # Calculate threshold score to check if it's < 100
    threshold_score_sum = 0
    if threshold_alert == 1 and threshold_scores and len(threshold_scores) > 0:
        threshold_score_sum = sum(threshold_scores)
    elif threshold_alert == 1:
        threshold_score_sum = 100  # Default score if threshold_scores not provided
    
    has_threshold_only_low_score = (
        threshold_alert == 1 
        and isOutlier != 1 
        and threshold_score_sum < 100
    )
    
    # Only add status_not_met if:
    # - Original upstream status was bad (status != 1) AND
    # - Entity is in non-green state AND
    # - Entity is NOT orange/red ONLY due to outliers (any score) AND
    # - Outliers score is NOT >= 100 (don't add if outliers already made it red) AND
    # - Entity is NOT orange/red ONLY due to threshold breaches with score < 100
    if ((object_state == "red" and not threshold_alert) or object_state == "orange") and original_upstream_status is not None and original_upstream_status != 1 and not has_outliers_only and not outliers_score_high and not has_threshold_only_low_score:
        status_message_str = f"The entity status is not complying with monitoring rules (status: {status}, status_description: {status_description})"
        status_message.append(status_message_str)
        anomaly_reason.append("status_not_met")
        # Add score increment for status_not_met if scoring is enabled (using VT-specific impact score)
        if score is not None and total_score is not None:
            increment = get_impact_score(vtenant_account, "impact_score_flx_status_not_met", 100)
            total_score += increment
            score_definition["components"].append({
                "type": "status_not_met",
                "score": increment,
                "description": "Status not met"
            })
            # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score

        # Re-check score-based logic after adding status_not_met score
        # If total_score >= 100, ensure entity is red (unless it's blue due to logical group)
        if total_score is not None and total_score >= 100:
            if object_state not in ["red", "blue"]:
                object_state = "red"
                status = 2
                get_effective_logger().debug(
                    f'set_flx_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red after status_not_met (score >= 100)'
                )

    # Other statements
    # Check for outliers: report isOutlier in status_message for both red and orange states
    # Add ml_outliers_detection to anomaly_reason for all outlier cases
    if isOutlier == 1 or (score_outliers is not None and score_outliers > 0):
        # Always add outlier reasons when outliers are present (either traditional or hybrid scoring).
        # When the latest ML monitor cycle has cleared isOutlierReason but score_outliers (24h cumulative)
        # still indicates past outliers, fall back to the cached lastIsOutlierReason — see helper docstring.
        outlier_msg, _outlier_used_cached = build_outlier_reason_status_message(
            record, score_outliers
        )
        if outlier_msg:
            status_message.append(outlier_msg)

        # Add ml_outliers_detection to anomaly_reason for all outlier cases
        if "ml_outliers_detection" not in anomaly_reason:
            anomaly_reason.append("ml_outliers_detection")
        
        # Add score context message for red state with high outlier score (>= 100)
        # Note: orange state score messages are already added during score-based state transitions above
        if score_outliers is not None and score_outliers >= 100:
            base_score = float(score) if score is not None else 0.0
            total = float(total_score) if total_score is not None else score_outliers
            status_message.append(
                f"Entity has an impact score of {total:.1f} (base score: {base_score:.1f}), which is 100 or above. "
                f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                f"This indicates critical anomalies warranting an alert status."
            )

    if object_state == "red":

        # Monitoring time policy, add the message first then the anomaly reason
        if isUnderMonitoring is False:
            status_message.append(isUnderMonitoringMsg)
            # Use new monitoring anomaly reason if provided
            if monitoring_anomaly_reason:
                anomaly_reason.append(monitoring_anomaly_reason)
            else:
                anomaly_reason.append("out_of_monitoring_times")
            # Note: out_of_monitoring_times is not scored as an anomaly - it's a protective mechanism
            # that prevents entities from turning red when outside their monitoring window

        # logical group
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)
            anomaly_reason.append("in_logical_group")
            # Note: in_logical_group is not scored as an anomaly - it's a protective mechanism
            # that prevents entities from turning red when the logical group is compliant

    #
    # Logical group management (object_state is red but in a logical group which is not in alert)
    #

    # if object_state is red but isUnderLogicalGroup is True and LogicalGroupStateInAlert is False, then object_state is blue
    if object_state == "red" and isUnderLogicalGroup is True:
        if LogicalGroupStateInAlert is False:
            object_state = "blue"
            status = 3
    #
    # Out of monitoring days and hours management (post-scoring)
    # Monitoring time policy takes precedence over scoring — entities outside
    # their monitoring window must never be promoted to red by scoring logic
    #
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"
            status = 3

    # Fallback: manual score influence raised total_score > 0 but no actual
    # anomaly was detected — populate status_message / anomaly_reason so the
    # UI can explain the non-green state.
    apply_manual_score_without_anomaly_fallback(
        record,
        score_definition,
        total_score,
        score,
        status_message,
        anomaly_reason,
        object_state,
    )

    # update status, object_state, anomaly_reason and metrics
    record["status"] = status
    record["object_state"] = object_state
    record["anomaly_reason"] = anomaly_reason

    # ensure status metric in metrics is updated
    try:
        metrics_record = record.get("metrics", {})
        if isinstance(metrics_record, str):
            metrics_record = json.loads(metrics_record)
        metrics_record["status"] = status
        record["metrics"] = json.dumps(metrics_record)
    except Exception as e:
        pass
    status_message_json["status_message"] = status_message
    status_message_json["anomaly_reason"] = anomaly_reason
    if extra_attributes:
        status_message_json["extra_attributes"] = extra_attributes
    
    # Add score information to status_message_json for UI display (sorted alphabetically)
    # Use total_score if calculated (hybrid scoring), otherwise use base score
    if total_score is not None:
        status_message_json["score"] = float(total_score)
        # Update record score to reflect the calculated total_score for UI consistency
        record["score"] = float(total_score)
        # Add score definition for drilldown modal
        if score_definition:
            status_message_json["score_definition"] = score_definition
            record["score_definition"] = json.dumps(score_definition) if isinstance(score_definition, dict) else score_definition
    elif score is not None:
        status_message_json["score"] = float(score)
    if score_outliers is not None:
        status_message_json["score_outliers"] = float(score_outliers)
    if total_score is not None:
        status_message_json["total_score"] = float(total_score)

    # get disruption_duration
    if not disruption_queue_record:
        record["disruption_min_time_sec"] = 0

    else:

        logger.debug(
            f'disruption_queue_record="{disruption_queue_record}", getting disruption_duration'
        )

        disruption_object_state = disruption_queue_record.get("object_state", "green")
        try:
            disruption_min_time_sec = int(
                disruption_queue_record.get("disruption_min_time_sec", 0)
            )
        except:
            disruption_min_time_sec = 0
        # add to the record
        record["disruption_min_time_sec"] = disruption_min_time_sec

        try:
            disruption_start_epoch = float(
                disruption_queue_record.get("disruption_start_epoch", 0)
            )
        except:
            disruption_start_epoch = 0

        # Case 1: Entity is no longer in alert state (not red)
        if object_state != "red":
            # Only update if we were previously tracking a disruption
            if disruption_object_state == "red":
                disruption_queue_record["object_state"] = object_state
                disruption_queue_record["disruption_start_epoch"] = 0
                disruption_queue_record["mtime"] = time.time()

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")
            return object_state, status_message, status_message_json, anomaly_reason

        # Case 2: Entity is in alert state (red)
        if object_state == "red":
            current_time = time.time()

            # If this is a new disruption, start tracking it
            if disruption_object_state != "red":
                disruption_queue_record["object_state"] = "red"
                disruption_queue_record["disruption_start_epoch"] = current_time
                disruption_queue_record["mtime"] = current_time

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")

                # For new disruptions, if min time is set, show as blue with message
                if disruption_min_time_sec > 0:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is 0 which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message
                return object_state, status_message, status_message_json, anomaly_reason

            # If we're already tracking a disruption, check duration
            if disruption_min_time_sec > 0:
                try:
                    disruption_duration = current_time - disruption_start_epoch
                except Exception as e:
                    logger.error(f"error calculating disruption_duration: {e}")
                    disruption_duration = 0

                # If duration hasn't breached threshold, show as blue with message
                if disruption_duration < disruption_min_time_sec:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is {convert_seconds_to_duration(disruption_duration)} which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message

    # anomaly_reason sanitify check, if the list has more than 1 item, and contains "none", remove it
    if isinstance(anomaly_reason, list):
        if len(anomaly_reason) > 1 and "none" in anomaly_reason:
            anomaly_reason.remove("none")

    # return
    get_effective_logger().debug(
        f'set_flx_status, object="{record.get("object")}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
    )

    return object_state, status_message, status_message_json, anomaly_reason


def set_fqm_status(
    logger,
    splunkd_uri,
    session_key,
    tenant_id,
    record,
    isOutlier,
    isUnderMonitoring,
    isUnderMonitoringMsg,
    object_logical_group_dict,
    threshold_alert,
    threshold_messages,
    disruption_queue_collection,
    disruption_queue_record,
    source_handler=None,
    monitoring_anomaly_reason=None,
    score=None,
    score_outliers=None,
    threshold_scores=None,
    vtenant_account=None,
):
    """
    Create a function called set_fqm_status:
    - arguments: record, isOutlier, isFuture, isUnderMonitoring, isUnderMonitoringMsg, isUnderLogicalGroup, LogicalGroupStateInAlert, isUnderLatencyAlert, isUnderLatencyMessage, isUnderDelayAlert, isUnderDelayMessage
    - returns:
        object_state (string): blue, orange, green, red
        anomaly_reason (list): list of short code reasons why the object is in anomaly
        status_message (list): list of long description reasons why the object is in anomaly
    - behaviour:
        object_state:
            green if:
                isOutlier is 1
                isFuture is False
                isUnderMonitoring is True
                if isUnderLogicalGroup is True, then LogicalGroupStateInAlert must be False
                isUnderLatencyAlert is False
                isUnderDelayAlert is False
            blue if:
                Any of the condition above is not met, but isUnderLogicalGroup is True and LogicalGroupStateInAlert is True
            orange if:
                All green conditions are met except for isFuture which would be True
            red if:
                Any of the green conditions are not met, and blue conditions and orange conditions are not met
        anomaly_reason:
            if object_state is green, anomnaly_reason is None
            Otherwise, anomaly_reason is a list containing the reasons why the object is in anomaly
    """

    # init status_message and anomaly_reason
    status_message = []
    anomaly_reason = []

    # get percent_success
    percent_success = record.get("percent_success", None)
    if percent_success is not None:
        percent_success = float(percent_success)
        if percent_success == int(percent_success):
            percent_success = int(percent_success)
    else:
        percent_success = 0

    # get percent_coverage
    percent_coverage = record.get("percent_coverage", None)
    if percent_coverage is not None:
        percent_coverage = float(percent_coverage)
        if percent_coverage == int(percent_coverage):
            percent_coverage = int(percent_coverage)
    else:
        percent_coverage = 0

    # get ields_quality_summary JSON, and load as an object
    fields_quality_summary = record.get("fields_quality_summary", {})
    if isinstance(fields_quality_summary, str):
        try:
            fields_quality_summary = json.loads(fields_quality_summary)
        except Exception as e:
            fields_quality_summary = {}
    else:
        fields_quality_summary = {}

    # get total_fields_passed and total_fields_failed (for the global entity)
    if fields_quality_summary:
        total_fields_passed = fields_quality_summary.get("total_fields_passed", 0)
        if isinstance(total_fields_passed, str):
            try:
                total_fields_passed = int(total_fields_passed)
            except Exception as e:
                total_fields_passed = 0
        total_fields_failed = fields_quality_summary.get("total_fields_failed", 0)
        if isinstance(total_fields_failed, str):
            try:
                total_fields_failed = int(total_fields_failed)
            except Exception as e:
                total_fields_failed = 0

    # set fqm_type (if @global in object, then fqm_type is global, otherwise it is field)
    fqm_type = "field"
    if "@global" in record.get("object", ""):
        fqm_type = "global"

    # set object_description
    object_description = {}
    # 1 - try to load the content of fields_quality_summary (JSON as string)
    # 2 - iterate over the JSON and look for fields metadata.*
    # 3 - add them to the record as metadata_<fieldname> (instead of metadata.<fieldname>)
    if "fields_quality_summary" in record:
        try:
            fields_quality_summary = json.loads(record["fields_quality_summary"])
            for field in fields_quality_summary:
                if field.startswith("metadata."):
                    newfield_name = field.replace("metadata.", "metadata_")
                    object_description[f"{newfield_name}"] = fields_quality_summary[field]
        except:
            pass

    # add field
    object_description["field"] = record.get('fieldname')
    object_description = json.dumps(object_description, indent=2)

    record["object_description"] = object_description

    # init status_message_json
    status_message_json = {}

    # init status, status_description, status_description_short, object_state
    status = 1
    if fqm_type == "field":
        status_description = f"The field {record.get('fieldname')} is complying with monitoring rules, % success: {percent_success}, % coverage: {percent_coverage}"
        status_description_short = f"% success: {percent_success}, % coverage: {percent_coverage}"
    elif fqm_type == "global":
        status_description = f"The global entity is complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
        status_description_short = f"% success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"

    object_state = "green"

    # mandatorily update the record
    record["status"] = status
    record["status_description"] = status_description
    record["status_description_short"] = status_description_short
    record["object_state"] = object_state

    #
    # Threshold alert management
    #

    # In fqm. the threshold is mandatory and the root logic of the detection
    record["threshold_alert"] = threshold_alert
    record["threshold_messages"] = threshold_messages
    if threshold_alert == 1:
        object_state = "red"
        status = 2
        anomaly_reason.append("threshold_alert")
        for threshold_message in threshold_messages:
            status_message.append(threshold_message)
        # Update status_description for alert state
        if fqm_type == "field":
            status_description = f"The field {record.get('fieldname')} is not complying with monitoring rules, % success: {percent_success}, % coverage: {percent_coverage}"
            status_description_short = f"% success: {percent_success}, % coverage: {percent_coverage}"

            # include additional messages in status_message depending on the description field in fields_quality_summary
            if fields_quality_summary:
                quality_results_description = fields_quality_summary.get("quality_results_description", [])

                for description_item in quality_results_description:
                    if description_item.startswith("category: Field does not exist"):
                        status_message.append("The field has failed to pass quality verifications (is missing), review the results from the entity field view to troubleshoot these issues")
                    elif description_item.startswith("category: Field exists but contains 'unknown'"):
                        status_message.append("The field has failed to pass quality verifications (contains unknown values), review the results from the entity field view to troubleshoot these issues")
                    elif description_item.startswith("category: Field is empty"):
                        status_message.append("The field has failed to pass quality verifications (is empty), review the results from the entity field view to troubleshoot these issues")
                    elif description_item.startswith("category: Field is 'unknown'"):
                        status_message.append("The field has failed to pass quality verifications (is unknown), review the results from the entity field view to troubleshoot these issues")
                    elif description_item.startswith("category: Field exists but value does not match the required pattern"):
                        status_message.append("The field has failed to pass the regex pattern validation, review the results from the Search not matching regex from the entity field view to extract the list of values that do not match the required pattern")
                    elif description_item.startswith("category: Field exists but one or more values in the list do not match the required pattern"):
                        status_message.append("The field has failed to pass the regex pattern validation (list values), review the results from the Search not matching regex from the entity field view to extract the list of values that do not match the required pattern")
                    elif description_item.startswith("category: Field does not exist but is allowed to be missing"):
                        # Skip this category as it's a success case
                        continue
                    elif description_item.startswith("category: Field is empty but is allowed to be empty"):
                        # Skip this category as it's a success case
                        continue
                    elif description_item.startswith("category: Field exists and is valid"):
                        # Skip this category as it's a success case
                        continue

        elif fqm_type == "global":
            status_description = f"The global entity is not complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
            status_description_short = f"% success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"

            # include an additional message in status_message if total_fields_failed is greater than 0, including the number of fields that failed
            if total_fields_failed > 0:
                if total_fields_failed == 1:
                    status_message.append(f"The global entity has {total_fields_failed} field that failed to pass quality verifications (failed field: {fields_quality_summary.get('failed_fields', [])}), review the results from the entity field view to troubleshoot these issues")
                else:
                    status_message.append(f"The global entity has {total_fields_failed} fields that failed to pass quality verifications (failed fields: {fields_quality_summary.get('failed_fields', [])}), review the results from the entity field view to troubleshoot these issues")

        record["status_description"] = status_description
        record["status_description_short"] = status_description_short
        record["status"] = status
        record["object_state"] = object_state

    #
    # Logical group management
    #

    (
        isUnderLogicalGroup,
        LogicalGroupStateInAlert,
        LogicalGroupMsg,
    ) = get_and_manage_logical_group_status(
        splunkd_uri,
        session_key,
        tenant_id,
        record.get("object"),
        object_state,
        record.get("object_group_key"),
        object_logical_group_dict,
    )

    # log debug
    logger.debug(
        f'function get_and_manage_logical_group_status: object="{record.get("object")}", object_state="{object_state}", object_group_key="{record.get("object_group_key")}", isUnderLogicalGroup="{isUnderLogicalGroup}", LogicalGroupStateInAlert="{LogicalGroupStateInAlert}", LogicalGroupMsg="{LogicalGroupMsg}"'
    )

    # Verify isOutlier
    # Only set red if isOutlier == 1 AND score_outliers > 0 (or score_outliers is None for legacy)
    # If score_outliers <= 0, outliers are suppressed (false positive) and should not cause red state
    if isOutlier == 1:
        if score_outliers is not None:
            if score_outliers > 0:
                # Outliers present with positive score
                if score_outliers >= 100:
                    object_state = "red"
                    status = 2
                else:
                    # score_outliers > 0 and < 100, set to orange
                    object_state = "orange"
                    status = 3
            # If score_outliers <= 0, don't set state to red/orange (outliers suppressed)
        else:
            # Legacy behavior: if score_outliers is not provided, use isOutlier
            object_state = "red"
            status = 2
    else:
        pass

    # if object_state is red but isUnderMonitoring is False, then object_state is orange
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"
            status = 3
            # Update status_description for orange state
            if fqm_type == "field":
                status_description = f"The field {record.get('fieldname')} is not complying with monitoring rules, % success: {percent_success}, % coverage: {percent_coverage}"
                status_description_short = f"% success: {percent_success}, % coverage: {percent_coverage}"
            elif fqm_type == "global":
                status_description = f"The global entity is not complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
                status_description_short = f"% success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
            record["status_description"] = status_description
            record["status_description_short"] = status_description_short
            record["status"] = status
            record["object_state"] = object_state

    #
    # Hybrid scoring: Apply score-based logic
    # Outliers are handled separately via score_outliers in get_outliers_status
    #
    total_score = None
    score_definition = {}
    if score is not None:
        # Calculate total score with static increments for anomalies
        base_score = float(score) if score is not None else 0.0
        total_score = base_score
        
        # Build score definition to track where the score comes from
        # Convert base_score to integer if it's a whole number, otherwise keep as float
        if base_score == int(base_score):
            score_definition["base_score"] = int(base_score)
        else:
            score_definition["base_score"] = base_score
        score_definition["components"] = []
        
        # Add static increments for each anomaly type
        if threshold_alert == 1:
            # Use threshold scores if provided, otherwise default to 100
            if threshold_scores and len(threshold_scores) > 0:
                # Sum all threshold scores (multiple thresholds can be breached)
                increment = sum(threshold_scores)
            else:
                # Default to 100 for backward compatibility
                increment = 100
            total_score += increment
            score_definition["components"].append({
                "type": "threshold_breach",
                "score": increment,
                "description": "Threshold alert breached"
            })
        
        # Add outlier score if present
        if score_outliers is not None and score_outliers > 0:
            score_definition["score_outliers"] = float(score_outliers)
        
        # Add score sources if available
        score_source = record.get("score_source", [])
        if score_source:
            score_definition["score_source"] = score_source if isinstance(score_source, list) else [score_source]
        
        # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score
        
        # Apply score-based logic:
        # - If total_score >= 100: entity should be red (if not already red due to other reasons, keep current state)
        # - If total_score > 0 and < 100: entity should be orange (even if currently green)
        # - If total_score == 0: keep current state
        
        if total_score >= 100:
            # If score >= 100, ensure entity is red (unless it's blue due to logical group)
            if object_state not in ["red", "blue"]:
                object_state = "red"
                status = 2
                get_effective_logger().debug(
                    f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red (score >= 100)'
                )
            else:
                get_effective_logger().debug(
                    f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (score >= 100)'
                )
        elif total_score > 0 and total_score < 100:
            # If score > 0 and < 100, entity should be orange (even if currently green)
            if object_state == "green":
                object_state = "orange"
                status = 3
                # Update status_description for orange state
                if fqm_type == "field":
                    status_description = f"The field {record.get('fieldname')} is not complying with monitoring rules, % success: {percent_success}, % coverage: {percent_coverage}"
                    status_description_short = f"% success: {percent_success}, % coverage: {percent_coverage}"
                elif fqm_type == "global":
                    status_description = f"The global entity is not complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
                    status_description_short = f"% success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
                record["status_description"] = status_description
                record["status_description_short"] = status_description_short
                record["status"] = status
                record["object_state"] = object_state
                # Add status message about score
                score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                # Add outlier context if outliers are present
                if score_outliers is not None and score_outliers > 0:
                    score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                status_message.append(score_msg)
                get_effective_logger().debug(
                    f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting green to orange (0 < score < 100)'
                )
            elif object_state == "red":
                # Downgrade red to orange if score < 100
                # Only apply score-based downgrade if the red state is NOT due to outliers
                # (outliers with score_outliers >= 100 should still be red)
                if isOutlier != 1:
                    object_state = "orange"
                    status = 3
                    # Update status_description for orange state
                    if fqm_type == "field":
                        status_description = f"The field {record.get('fieldname')} is not complying with monitoring rules, % success: {percent_success}, % coverage: {percent_coverage}"
                        status_description_short = f"% success: {percent_success}, % coverage: {percent_coverage}"
                    elif fqm_type == "global":
                        status_description = f"The global entity is not complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
                        status_description_short = f"% success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
                    record["status_description"] = status_description
                    record["status_description_short"] = status_description_short
                    record["status"] = status
                    record["object_state"] = object_state
                    # Add status message about score when downgrading
                    score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                    if score_outliers is not None and score_outliers > 0:
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                    status_message.append(score_msg)
                    get_effective_logger().debug(
                        f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", downgrading red to orange (non-outlier anomalies only)'
                    )
                else:
                    # If outlier is present but score_outliers < 100, it was already set to isOutlier=2
                    # in get_outliers_status, so we can still apply score-based logic
                    if score_outliers is not None and score_outliers < 100:
                        object_state = "orange"
                        status = 3
                        # Update status_description for orange state
                        if fqm_type == "field":
                            status_description = f"The field {record.get('fieldname')} is not complying with monitoring rules, % success: {percent_success}, % coverage: {percent_coverage}"
                            status_description_short = f"% success: {percent_success}, % coverage: {percent_coverage}"
                        elif fqm_type == "global":
                            status_description = f"The global entity is not complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
                            status_description_short = f"% success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
                        record["status_description"] = status_description
                        record["status_description_short"] = status_description_short
                        record["status"] = status
                        record["object_state"] = object_state
                        # Add status message about score when downgrading due to low outlier score
                        score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                        score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                        status_message.append(score_msg)
                        get_effective_logger().debug(
                            f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'downgrading red to orange (outlier score too low)'
                        )
                    else:
                        get_effective_logger().debug(
                            f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", keeping red state (outlier score >= 100)'
                        )
            else:
                get_effective_logger().debug(
                    f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (0 < score < 100)'
                )
        else:
            # total_score == 0 or total_score <= 0
            # Check if score is 0 due to false_positive (global false positive, not just outliers)
            score_source = record.get("score_source", [])
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            has_false_positive = "false_positive" in score_source_list
            
            if has_false_positive:
                # Score is 0 due to false_positive, set to green (anomaly_reason will remain visible for audit)
                object_state = "green"
                status = 1
                get_effective_logger().debug(
                    f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", score_source="{score_source}", '
                    f'setting state to green (false positive set, score cancelled)'
                )
            else:
                # Check if total_score is 0 because all impact score weights are 0
                # If all components have score 0, then the entity should be green (unless outliers present or threshold alerts)
                all_components_zero = True
                if score_definition and "components" in score_definition:
                    components = score_definition.get("components", [])
                    if components:
                        for component in components:
                            component_score = component.get("score", 0)
                            if component_score != 0:
                                all_components_zero = False
                                break
                    # If no components exist yet, anomaly detection hasn't run
                    # (FQM populates some components after the scoring block).
                    # Check if anomaly conditions are pending — if so, don't force green.
                    elif not components and total_score == 0:
                        has_pending_anomalies = (
                            isOutlier == 1
                            or isUnderMonitoring is False
                        )
                        all_components_zero = not has_pending_anomalies

                # If all components have score 0, no outliers, and no threshold alerts, set to green
                if (all_components_zero and
                    (score_outliers is None or score_outliers <= 0) and
                    threshold_alert != 1):
                    object_state = "green"
                    status = 1
                    get_effective_logger().debug(
                        f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'threshold_alert="{threshold_alert}", '
                        f'setting state to green (all impact score weights are 0, no outliers, no threshold alerts)'
                    )
                else:
                    # Keep current state if there are other issues or legacy behavior
                    get_effective_logger().debug(
                        f'set_fqm_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'threshold_alert="{threshold_alert}", keeping current state (score == 0)'
                    )

    # define anomaly_reason
    if object_state == "green":
        if fqm_type == "field":
            status_message_str = f"The field {record.get('fieldname')} is complying with monitoring rules, % success: {percent_success}"
        elif fqm_type == "global":
            status_message_str = f"The global entity is complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
        status_message.append(status_message_str)
        
        # Check if false positive is set - if so, preserve anomaly reasons from score_definition
        score_source = record.get("score_source", [])
        score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
        has_false_positive = "false_positive" in score_source_list
        
        if has_false_positive and score_definition and "components" in score_definition:
            # Extract anomaly reasons from score_definition components
            for component in score_definition.get("components", []):
                component_type = component.get("type")
                if component_type:
                    mapped_reason = get_anomaly_reason_from_component_type(component_type)
                    if mapped_reason and mapped_reason not in anomaly_reason:
                        anomaly_reason.append(mapped_reason)
            # If no components found, still add "none"
            if not anomaly_reason:
                anomaly_reason.append("none")
        else:
            anomaly_reason.append("none")

        # if in a logical group, add the logical group message
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)

    #
    # Inactive entities management
    #

    # get max_sec_inactive
    max_sec_inactive = record.get("max_sec_inactive", 0)
    try:
        max_sec_inactive = int(max_sec_inactive)
    except Exception as e:
        max_sec_inactive = 0

    # get the age in seconds since the latest execution
    sec_since_last_execution = round(
        time.time() - float(record.get("tracker_runtime")), 0
    )
    duration_since_last_execution = convert_seconds_to_duration(
        sec_since_last_execution
    )

    # Check and act
    if float(sec_since_last_execution) > max_sec_inactive and max_sec_inactive > 0:
        status_message_str = f"This entity has been inactive for more than {duration_since_last_execution} (D+HH:MM:SS) and was not actively managed by any tracker, its status was updated automatically by the inactive entities tracker"
        status_message = [status_message_str]
        status_description_short = "entity is red due to inactivity"
        status_description = f"The entity status is red due to inactivity, it was not actively managed by any tracker for more than {duration_since_last_execution} (D+HH:MM:SS)"
        anomaly_reason = ["inactive"]
        object_state = "red"
        status = 2
        # in this case, we need to update the status_description and status_description_short
        record["status_description"] = status_description
        record["status_description_short"] = status_description_short
        record["object_state"] = object_state

    #
    # end of inactive entities management
    #

    #
    # Red status due to upstream logic / Orange state
    #

    if (object_state == "red" and not threshold_alert) or object_state == "orange":
        status_message_str = f"The entity status is not complying with monitoring rules (status: {status}, status_description: {status_description})"
        status_message.append(status_message_str)
        anomaly_reason.append("status_not_met")
        # Update status_description for alert state if not already set
        if fqm_type == "field":
            status_description = f"The field {record.get('fieldname')} is not complying with monitoring rules, % success: {percent_success}, % coverage: {percent_coverage}"
            status_description_short = f"% success: {percent_success}, % coverage: {percent_coverage}"
        elif fqm_type == "global":
            status_description = f"The global entity is not complying with monitoring rules, % success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
            status_description_short = f"% success: {percent_success}, fields passed: {total_fields_passed}, fields failed: {total_fields_failed}"
        record["status_description"] = status_description
        record["status_description_short"] = status_description_short
        record["status"] = status
        record["object_state"] = object_state
        # Add score increment for status_not_met if scoring is enabled (using VT-specific impact score)
        if score is not None and total_score is not None:
            increment = get_impact_score(vtenant_account, "impact_score_fqm_status_not_met", 100)
            total_score += increment
            score_definition["components"].append({
                "type": "status_not_met",
                "score": increment,
                "description": "Status not met"
            })
            # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score

    # Other statements
    if object_state == "red":

        # Check for outliers: either isOutlier == 1 (traditional) or score_outliers > 0 (hybrid scoring)
        if isOutlier == 1 or (score_outliers is not None and score_outliers > 0):
            # Always add outlier reasons when outliers are present (either traditional or hybrid scoring).
            # When the latest ML monitor cycle has cleared isOutlierReason but score_outliers (24h cumulative)
            # still indicates past outliers, fall back to the cached lastIsOutlierReason — see helper docstring.
            outlier_msg, _outlier_used_cached = build_outlier_reason_status_message(
                record, score_outliers
            )
            if outlier_msg:
                status_message.append(outlier_msg)
            # Add ml_outliers_detection to anomaly_reason for all outlier cases
            if "ml_outliers_detection" not in anomaly_reason:
                anomaly_reason.append("ml_outliers_detection")
            
            # Add score context message for red state with high outlier score (>= 100)
            # Note: orange state score messages are already added during score-based state transitions above
            if score_outliers is not None and score_outliers >= 100:
                base_score = float(score) if score is not None else 0.0
                total = float(total_score) if total_score is not None else score_outliers
                status_message.append(
                    f"Entity has an impact score of {total:.1f} (base score: {base_score:.1f}), which is 100 or above. "
                    f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    f"This indicates critical anomalies warranting an alert status."
                )

        # Monitoring time policy, add the message first then the anomaly reason
        if isUnderMonitoring is False:
            status_message.append(isUnderMonitoringMsg)
            # Use new monitoring anomaly reason if provided
            if monitoring_anomaly_reason:
                anomaly_reason.append(monitoring_anomaly_reason)

        # logical group
        if isUnderLogicalGroup is True:
            status_message.append(LogicalGroupMsg)
            anomaly_reason.append("in_logical_group")

    #
    # Logical group management (object_state is red but in a logical group which is not in alert)
    #

    # if object_state is red but isUnderLogicalGroup is True and LogicalGroupStateInAlert is False, then object_state is blue
    if object_state == "red" and isUnderLogicalGroup is True:
        if LogicalGroupStateInAlert is False:
            object_state = "blue"
            status = 3
    #
    # Out of monitoring days and hours management
    #

    # if object_state is red but isUnderMonitoring is False, then object_state is orange
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"
            status = 3

    # Fallback: manual score influence raised total_score > 0 but no actual
    # anomaly was detected — populate status_message / anomaly_reason so the
    # UI can explain the non-green state.
    apply_manual_score_without_anomaly_fallback(
        record,
        score_definition,
        total_score,
        score,
        status_message,
        anomaly_reason,
        object_state,
    )

    # update status, object_state, anomaly_reason and metrics
    record["status"] = status
    record["object_state"] = object_state
    record["anomaly_reason"] = anomaly_reason

    # ensure status metric in metrics is updated
    try:
        metrics_record = record.get("metrics", {})
        if isinstance(metrics_record, str):
            metrics_record = json.loads(metrics_record)
        metrics_record["status"] = status
        record["metrics"] = json.dumps(metrics_record)
    except Exception as e:
        pass
    status_message_json["status_message"] = status_message
    status_message_json["anomaly_reason"] = anomaly_reason

    # Add score information to status_message_json for UI display (sorted alphabetically)
    # Use total_score if calculated (hybrid scoring), otherwise use base score
    if total_score is not None:
        status_message_json["score"] = float(total_score)
        # Update record score to reflect the calculated total_score for UI consistency
        record["score"] = float(total_score)
        # Add score definition for drilldown modal
        if score_definition:
            status_message_json["score_definition"] = score_definition
            record["score_definition"] = json.dumps(score_definition) if isinstance(score_definition, dict) else score_definition
    elif score is not None:
        status_message_json["score"] = float(score)
    if score_outliers is not None:
        status_message_json["score_outliers"] = float(score_outliers)
    if total_score is not None:
        status_message_json["total_score"] = float(total_score)

    # handle fields_quality_summary
    try:
        fields_quality_summary = record.get("fields_quality_summary", {})
        if isinstance(fields_quality_summary, str):
            fields_quality_summary = json.loads(fields_quality_summary)
    except Exception as e:
        fields_quality_summary = {}
        pass
    if fields_quality_summary:
        status_message_json["fields_quality_summary"] = fields_quality_summary

    # get disruption_duration
    if not disruption_queue_record:
        record["disruption_min_time_sec"] = 0

    else:

        logger.debug(
            f'disruption_queue_record="{disruption_queue_record}", getting disruption_duration'
        )

        disruption_object_state = disruption_queue_record.get("object_state", "green")
        try:
            disruption_min_time_sec = int(
                disruption_queue_record.get("disruption_min_time_sec", 0)
            )
        except:
            disruption_min_time_sec = 0
        # add to the record
        record["disruption_min_time_sec"] = disruption_min_time_sec

        try:
            disruption_start_epoch = float(
                disruption_queue_record.get("disruption_start_epoch", 0)
            )
        except:
            disruption_start_epoch = 0

        # Case 1: Entity is no longer in alert state (not red)
        if object_state != "red":
            # Only update if we were previously tracking a disruption
            if disruption_object_state == "red":
                disruption_queue_record["object_state"] = object_state
                disruption_queue_record["disruption_start_epoch"] = 0
                disruption_queue_record["mtime"] = time.time()

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")
            return object_state, status_message, status_message_json, anomaly_reason

        # Case 2: Entity is in alert state (red)
        if object_state == "red":
            current_time = time.time()

            # If this is a new disruption, start tracking it
            if disruption_object_state != "red":
                disruption_queue_record["object_state"] = "red"
                disruption_queue_record["disruption_start_epoch"] = current_time
                disruption_queue_record["mtime"] = current_time

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")

                # For new disruptions, if min time is set, show as blue with message
                if disruption_min_time_sec > 0:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is 0 which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message
                return object_state, status_message, status_message_json, anomaly_reason

            # If we're already tracking a disruption, check duration
            if disruption_min_time_sec > 0:
                try:
                    disruption_duration = current_time - disruption_start_epoch
                except Exception as e:
                    logger.error(f"error calculating disruption_duration: {e}")
                    disruption_duration = 0

                # If duration hasn't breached threshold, show as blue with message
                if disruption_duration < disruption_min_time_sec:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is {convert_seconds_to_duration(disruption_duration)} which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message

    # anomaly_reason sanitify check, if the list has more than 1 item, and contains "none", remove it
    if isinstance(anomaly_reason, list):
        if len(anomaly_reason) > 1 and "none" in anomaly_reason:
            anomaly_reason.remove("none")

    # return
    get_effective_logger().debug(
        f'set_fqm_status, object="{record.get("object")}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
    )

    return object_state, status_message, status_message_json, anomaly_reason


def set_wlk_status(
    logger,
    splunkd_uri,
    session_key,
    tenant_id,
    record,
    isOutlier,
    isUnderMonitoring,
    isUnderMonitoringMsg,
    disruption_queue_collection,
    disruption_queue_record,
    source_handler=None,
    monitoring_anomaly_reason=None,
    score=None,
    score_outliers=None,
    vtenant_account=None,
    dynamic_thresholds=None,
):
    """
    Create a function called set_wlk_status:
    - arguments: record, isOutlier, isFuture, isUnderMonitoring, isUnderMonitoringMsg, isUnderLogicalGroup, LogicalGroupStateInAlert, isUnderLatencyAlert, isUnderLatencyMessage, isUnderDelayAlert, isUnderDelayMessage
    - returns:
        object_state (string): blue, orange, green, red
        anomaly_reason (list): list of short code reasons why the object is in anomaly
        status_message (list): list of long description reasons why the object is in anomaly
    - behaviour:
        object_state:
            green if:
                isOutlier is 1
                isFuture is False
                isUnderMonitoring is True
                if isUnderLogicalGroup is True, then LogicalGroupStateInAlert must be False
                isUnderLatencyAlert is False
                isUnderDelayAlert is False
            blue if:
                Any of the condition above is not met, but isUnderLogicalGroup is True and LogicalGroupStateInAlert is True
            orange if:
                All green conditions are met except for isFuture which would be True
            red if:
                Any of the green conditions are not met, and blue conditions and orange conditions are not met
        anomaly_reason:
            if object_state is green, anomnaly_reason is None
            Otherwise, anomaly_reason is a list containing the reasons why the object is in anomaly
    """

    # init status_message and anomaly_reason
    status_message = []
    anomaly_reason = []

    # init status_message_json
    status_message_json = {}

    # for wlk, first retrieve object_state which is defined upstream
    object_state = record.get("object_state", "green")

    # status and status_description are used to compose the anomaly_reason
    status = record.get("status", "unknown")
    status_description = record.get("status_description", "unknown")

    # Verify isOutlier
    # Only set red if isOutlier == 1 AND score_outliers > 0 (or score_outliers is None for legacy)
    # If score_outliers <= 0, outliers are suppressed (false positive) and should not cause red state
    if isOutlier == 1:
        if score_outliers is not None:
            if score_outliers > 0:
                # Outliers present with positive score
                if score_outliers >= 100:
                    object_state = "red"
                else:
                    # score_outliers > 0 and < 100, set to orange
                    object_state = "orange"
            # If score_outliers <= 0, don't set state to red/orange (outliers suppressed)
        else:
            # Legacy behavior: if score_outliers is not provided, use isOutlier
            object_state = "red"
    else:
        pass

    # for wlk, get various functional fields used for the anomaly_reason and status_message definition
    # skipping KPis: skipped_pct, skipped_pct_last_60m, skipped_pct_last_4h, skipped_pct_last_24h
    try:
        skipped_pct = float(record.get("skipped_pct", 0))
    except Exception as e:
        skipped_pct = 0

    try:
        skipped_pct_last_60m = float(record.get("skipped_pct_last_60m", 0))
    except Exception as e:
        skipped_pct_last_60m = 0

    try:
        skipped_pct_last_4h = float(record.get("skipped_pct_last_4h", 0))
    except Exception as e:
        skipped_pct_last_4h = 0

    try:
        skipped_pct_last_24h = float(record.get("skipped_pct_last_24h", 0))
    except Exception as e:
        skipped_pct_last_24h = 0

    # similarly, load:
    # count_errors, count_errors_last_60m, count_errors_last_4h, count_errors_last_24h
    try:
        count_errors = int(record.get("count_errors", 0))
    except Exception as e:
        count_errors = 0

    try:
        count_errors_last_60m = int(record.get("count_errors_last_60m", 0))
    except Exception as e:
        count_errors_last_60m = 0

    try:
        count_errors_last_4h = int(record.get("count_errors_last_4h", 0))
    except Exception as e:
        count_errors_last_4h = 0

    try:
        count_errors_last_24h = int(record.get("count_errors_last_24h", 0))
    except Exception as e:
        count_errors_last_24h = 0

    # retrieve last_seen (epochtime) and cron_exec_sequence_sec (value in seconds)
    try:
        last_seen = int(record.get("last_seen", 0))
    except Exception as e:
        last_seen = 0

    # get last_seen_datetime
    if last_seen > 0:
        last_seen_datetime = convert_epoch_to_datetime(last_seen)
    else:
        last_seen_datetime = "unknown"

    try:
        cron_exec_sequence_sec = int(record.get("cron_exec_sequence_sec", 0))
    except Exception as e:
        cron_exec_sequence_sec = 0

    # calculate isDelayed (0 or 1)
    # if now()-last_seen)>(cron_exec_sequence_sec+3600, isDelayed is 1
    now = time.time()
    if (now - last_seen) > (cron_exec_sequence_sec + 3600):
        isDelayed = 1
    else:
        isDelayed = 0

    # calculate the current delay in seconds
    current_delay = now - last_seen

    # get the current delay durection
    current_delay_duration = convert_seconds_to_duration(current_delay)

    # retrieve orphan boolean (0 or 1) and load as an integer, as well as orphan_last_check (human readable date)
    try:
        orphan = int(record.get("orphan", 0))
    except Exception as e:
        orphan = 0

    orphan_last_check = record.get("orphan_last_check", "unknown")

    # if object_state is red but isUnderMonitoring is False, then object_state is orange
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    #
    # Hybrid scoring: Apply score-based logic
    # Outliers are handled separately via score_outliers in get_outliers_status
    #
    total_score = None
    score_definition = {}
    if score is not None:
        # Calculate total score with static increments for anomalies
        base_score = float(score) if score is not None else 0.0
        total_score = base_score
        
        # Build score definition to track where the score comes from
        # Convert base_score to integer if it's a whole number, otherwise keep as float
        if base_score == int(base_score):
            score_definition["base_score"] = int(base_score)
        else:
            score_definition["base_score"] = base_score
        score_definition["components"] = []
        
        # Add outlier score if present
        if score_outliers is not None and score_outliers > 0:
            score_definition["score_outliers"] = float(score_outliers)
        
        # Add score sources if available
        score_source = record.get("score_source", [])
        if score_source:
            score_definition["score_source"] = score_source if isinstance(score_source, list) else [score_source]
        
        # Note: Score increments for WLK anomalies are added later when anomalies are detected
        # This ensures scoring happens in sync with anomaly_reason detection
        
        # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score
        
        # Apply score-based logic:
        # - If total_score >= 100: entity should be red (if not already red due to other reasons, keep current state)
        # - If total_score > 0 and < 100: entity should be orange (even if currently green)
        # - If total_score == 0: keep current state
        
        if total_score >= 100:
            # If score >= 100, ensure entity is red
            if object_state not in ["red", "blue"]:
                object_state = "red"
                get_effective_logger().debug(
                    f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red (score >= 100)'
                )
            else:
                get_effective_logger().debug(
                    f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (score >= 100)'
                )
        elif total_score > 0 and total_score < 100:
            # If score > 0 and < 100, entity should be orange (even if currently green)
            if object_state == "green":
                object_state = "orange"
                # Add status message about score
                score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                # Add outlier context if outliers are present
                if score_outliers is not None and score_outliers > 0:
                    score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                status_message.append(score_msg)
                get_effective_logger().debug(
                    f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting green to orange (0 < score < 100)'
                )
            elif object_state == "red":
                # Downgrade red to orange if score < 100
                # Only apply score-based downgrade if the red state is NOT due to outliers
                # (outliers with score_outliers >= 100 should still be red)
                if isOutlier != 1:
                    object_state = "orange"
                    # Add status message about score when downgrading
                    score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                    if score_outliers is not None and score_outliers > 0:
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                    status_message.append(score_msg)
                    get_effective_logger().debug(
                        f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", downgrading red to orange (non-outlier anomalies only)'
                    )
                else:
                    # If outlier is present but score_outliers < 100, it was already set to isOutlier=2
                    # in get_outliers_status, so we can still apply score-based logic
                    if score_outliers is not None and score_outliers < 100:
                        object_state = "orange"
                        # Add status message about score when downgrading due to low outlier score
                        score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {score:.1f}), which is above 0 but below 100. "
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                        score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                        status_message.append(score_msg)
                        get_effective_logger().debug(
                            f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'downgrading red to orange (outlier score too low)'
                        )
                    else:
                        get_effective_logger().debug(
                            f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", keeping red state (outlier score >= 100)'
                        )
            else:
                get_effective_logger().debug(
                    f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", keeping {object_state} state (0 < score < 100)'
                )
        else:
            # total_score == 0 or total_score <= 0
            # Check if score is 0 due to false_positive (global false positive, not just outliers)
            score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
            has_false_positive = "false_positive" in score_source_list
            
            if has_false_positive:
                # Score is 0 due to false_positive, set to green (anomaly_reason will remain visible for audit)
                object_state = "green"
                status = 1
                get_effective_logger().debug(
                    f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                    f'total_score="{total_score}", score_source="{score_source}", '
                    f'setting state to green (false positive set, score cancelled)'
                )
            else:
                # Check if total_score is 0 because all impact score weights are 0
                # If all components have score 0, then the entity should be green (unless outliers present)
                all_components_zero = True
                if score_definition and "components" in score_definition:
                    components = score_definition.get("components", [])
                    if components:
                        for component in components:
                            component_score = component.get("score", 0)
                            if component_score != 0:
                                all_components_zero = False
                                break
                    # If no components exist yet, anomaly detection hasn't run
                    # (WLK populates components after the scoring block).
                    # Check if anomaly conditions are pending — if so, don't force green.
                    elif not components and total_score == 0:
                        if dynamic_thresholds:
                            # When dynamic thresholds are configured, pre-evaluate them
                            # instead of using legacy hardcoded > 0 checks for error/skipping
                            # metrics. This prevents entities within configured thresholds
                            # from being stuck at a non-green state.
                            pre_alert, _, _ = wlk_check_dynamic_thresholds(
                                logger, dynamic_thresholds, record
                            )
                            has_pending_anomalies = (
                                isOutlier == 1
                                or pre_alert == 1
                                or orphan == 1
                                or (isDelayed == 1 and cron_exec_sequence_sec > 0)
                                or isUnderMonitoring is False
                            )
                        else:
                            has_pending_anomalies = (
                                isOutlier == 1
                                or count_errors > 0
                                or count_errors_last_60m > 0
                                or count_errors_last_4h > 0
                                or count_errors_last_24h > 0
                                or skipped_pct > 0
                                or skipped_pct_last_60m > 0
                                or skipped_pct_last_4h > 0
                                or skipped_pct_last_24h > 0
                                or orphan == 1
                                or (isDelayed == 1 and cron_exec_sequence_sec > 0)
                                or isUnderMonitoring is False
                            )
                        all_components_zero = not has_pending_anomalies

                # If all components have score 0 and no outliers (or outliers suppressed), set to green
                if all_components_zero and (score_outliers is None or score_outliers <= 0):
                    object_state = "green"
                    status = 1
                    get_effective_logger().debug(
                        f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                        f'total_score="{total_score}", score_outliers="{score_outliers}", '
                        f'setting state to green (all impact score weights are 0, no outliers)'
                    )
                else:
                    # Anomalies pending — ensure state is non-green so anomaly
                    # detection runs (thresholds, orphan, delayed, etc.)
                    if object_state == "green":
                        object_state = "orange"
                        get_effective_logger().debug(
                            f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'promoting green to orange (score == 0, pending anomalies)'
                        )
                    else:
                        get_effective_logger().debug(
                            f'set_wlk_status, hybrid scoring: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'keeping current state (score == 0, pending anomalies)'
                        )

    # define anomaly_reason
    if object_state == "green":
        status_message_str = f"The entity status is complying with monitoring rules (status: {status}, status_description: {status_description})"
        status_message.append(status_message_str)
        
        # Check if false positive is set - if so, preserve anomaly reasons from score_definition
        score_source = record.get("score_source", [])
        score_source_list = score_source if isinstance(score_source, list) else ([score_source] if score_source else [])
        has_false_positive = "false_positive" in score_source_list
        
        if has_false_positive and score_definition and "components" in score_definition:
            # Extract anomaly reasons from score_definition components
            for component in score_definition.get("components", []):
                component_type = component.get("type")
                if component_type:
                    mapped_reason = get_anomaly_reason_from_component_type(component_type)
                    if mapped_reason and mapped_reason not in anomaly_reason:
                        anomaly_reason.append(mapped_reason)
            # If no components found, still add "none"
            if not anomaly_reason:
                anomaly_reason.append("none")
        else:
            anomaly_reason.append("none")

    else:
        # Other statements

        # ML Outlier: Check for outliers: either isOutlier == 1 (traditional) or score_outliers > 0 (hybrid scoring)
        if isOutlier == 1 or (score_outliers is not None and score_outliers > 0):
            # Always add outlier reasons when outliers are present (either traditional or hybrid scoring).
            # When the latest ML monitor cycle has cleared isOutlierReason but score_outliers (24h cumulative)
            # still indicates past outliers, fall back to the cached lastIsOutlierReason — see helper docstring.
            outlier_msg, _outlier_used_cached = build_outlier_reason_status_message(
                record, score_outliers
            )
            if outlier_msg:
                status_message.append(outlier_msg)
            # Add anomaly reason for outliers (either traditional or hybrid scoring)
            if "ml_outliers_detection" not in anomaly_reason:
                anomaly_reason.append("ml_outliers_detection")
            
            # Add score context message for red state with high outlier score (>= 100)
            # Note: orange state score messages are already added during score-based state transitions above
            if score_outliers is not None and score_outliers >= 100:
                base_score = float(score) if score is not None else 0.0
                total = float(total_score) if total_score is not None else score_outliers
                status_message.append(
                    f"Entity has an impact score of {total:.1f} (base score: {base_score:.1f}), which is 100 or above. "
                    f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    f"This indicates critical anomalies warranting an alert status."
                )

        # Skipping searches and execution errors — threshold-based evaluation
        if dynamic_thresholds:
            # Use configurable thresholds
            threshold_alert, threshold_messages, threshold_scores = wlk_check_dynamic_thresholds(
                logger, dynamic_thresholds, record
            )
            if threshold_alert:
                for msg in threshold_messages:
                    status_message.append(msg)
                # Determine which anomaly types are present based on breached metric names
                skipping_alert = any("skipped_pct" in msg for msg in threshold_messages)
                errors_alert = any("count_errors" in msg for msg in threshold_messages)
                if skipping_alert:
                    anomaly_reason.append("skipping_searches_detected")
                if errors_alert:
                    anomaly_reason.append("execution_errors_detected")
                # Apply cumulative threshold scores with per-metric descriptions
                for ts, msg in zip(threshold_scores, threshold_messages):
                    if score is not None and total_score is not None:
                        total_score += ts
                        score_definition["components"].append({
                            "type": "threshold_breach",
                            "score": ts,
                            "description": msg
                        })
        else:
            # Legacy behavior (no thresholds configured) — alert if any metric > 0
            if (
                skipped_pct > 0
                or skipped_pct_last_60m > 0
                or skipped_pct_last_4h > 0
                or skipped_pct_last_24h > 0
            ):
                status_message.append(
                    f"skipping searches were detected, review and address performance issues for this search or finetune its scheduling plan to clear this alert. (skipped_pct_last_60m: {skipped_pct_last_60m}, skipped_pct_last_4h: {skipped_pct_last_4h}, skipped_pct_last_24h: {skipped_pct_last_24h})"
                )
                anomaly_reason.append("skipping_searches_detected")
                if score is not None and total_score is not None:
                    increment = get_impact_score(vtenant_account, "impact_score_wlk_skipping_searches", 100)
                    total_score += increment
                    score_definition["components"].append({
                        "type": "skipping_searches_detected",
                        "score": increment,
                        "description": "Skipping searches detected"
                    })

            if (
                count_errors > 0
                or count_errors_last_60m > 0
                or count_errors_last_4h > 0
                or count_errors_last_24h > 0
            ):
                status_message.append(
                    f"execution errors were detected, review and address these errors to clear this alert. (count_errors_last_60m: {count_errors_last_60m}, count_errors_last_4h: {count_errors_last_4h}, count_errors_last_24h: {count_errors_last_24h})"
                )
                anomaly_reason.append("execution_errors_detected")
                if score is not None and total_score is not None:
                    increment = get_impact_score(vtenant_account, "impact_score_wlk_execution_errors", 100)
                    total_score += increment
                    score_definition["components"].append({
                        "type": "execution_errors_detected",
                        "score": increment,
                        "description": "Execution errors detected"
                    })

        # Update total_score in score_definition
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score

        # orphan
        if orphan == 1:
            status_message.append(
                f"the search was detected as an orphan search which means the user owning the search is not currently a valid user (orphan: {orphan}, time check: {orphan_last_check}"
            )
            anomaly_reason.append("orphan_search_detected")
            # Add score increment for orphan search if scoring is enabled (using VT-specific impact score)
            if score is not None and total_score is not None:
                increment = get_impact_score(vtenant_account, "impact_score_wlk_orphan_search", 100)
                total_score += increment
                score_definition["components"].append({
                    "type": "orphan_search_detected",
                    "score": increment,
                    "description": "Orphan search detected"
                })
                # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score

        # delayed
        if isDelayed == 1 and cron_exec_sequence_sec > 0:
            status_message.append(
                f"the search was detected as delayed, this means the search is not running as expected (isDelayed: {isDelayed}, last_seen: {last_seen_datetime}, cron_exec_sequence_sec: {cron_exec_sequence_sec}, current delay: {current_delay_duration} duration)"
            )
            anomaly_reason.append("execution_delayed")
            # Add score increment for execution delayed if scoring is enabled (using VT-specific impact score)
            if score is not None and total_score is not None:
                increment = get_impact_score(vtenant_account, "impact_score_wlk_execution_delayed", 100)
                total_score += increment
                score_definition["components"].append({
                    "type": "execution_delayed",
                    "score": increment,
                    "description": "Execution delayed"
                })
                # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score

        # Monitoring time policy, add the message first then the anomaly reason
        if isUnderMonitoring is False:
            status_message.append(isUnderMonitoringMsg)
            # Use new monitoring anomaly reason if provided, otherwise use legacy
            if monitoring_anomaly_reason:
                anomaly_reason.append(monitoring_anomaly_reason)
            else:
                anomaly_reason.append("out_of_monitoring_times")

        # if we failed to identify the reason
        if len(status_message) == 0:
            status_message_str = f"The entity status is not complying with monitoring rules (status: {status}, status_description: {status_description})"
            status_message.append(status_message_str)
            anomaly_reason.append("status_not_met")
            # Add score increment for status_not_met if scoring is enabled
            if score is not None and total_score is not None:
                increment = get_impact_score(vtenant_account, "impact_score_wlk_status_not_met", 100)
                total_score += increment
                score_definition["components"].append({
                    "type": "status_not_met",
                    "score": increment,
                    "description": "Status not met"
                })
                # Convert total_score to integer if it's a whole number, otherwise keep as float
        if total_score is not None:
            if total_score == int(total_score):
                score_definition["total_score"] = int(total_score)
            else:
                score_definition["total_score"] = total_score
        else:
            score_definition["total_score"] = total_score

        # Final score-based state re-evaluation after all score increments
        # The initial state transition (above) ran before threshold, orphan, delayed,
        # and status_not_met scores were added. Re-evaluate now that total_score is final.
        if total_score is not None and total_score >= 100:
            if object_state not in ["red", "blue"]:
                object_state = "red"
                get_effective_logger().debug(
                    f'set_wlk_status, final score re-evaluation: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting state to red (score >= 100)'
                )
        elif total_score is not None and total_score > 0 and total_score < 100:
            base_score = float(score) if score is not None else 0.0
            if object_state == "green":
                object_state = "orange"
                score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {base_score:.1f}), which is above 0 but below 100. "
                if score_outliers is not None and score_outliers > 0:
                    score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                status_message.append(score_msg)
                get_effective_logger().debug(
                    f'set_wlk_status, final score re-evaluation: object="{record.get("object")}", '
                    f'total_score="{total_score}", setting green to orange (0 < score < 100)'
                )
            elif object_state == "red":
                # Downgrade red to orange when final score is below 100
                # Only apply score-based downgrade if the red state is NOT due to outliers
                # (outliers with score_outliers >= 100 should still be red)
                if isOutlier != 1:
                    object_state = "orange"
                    score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {base_score:.1f}), which is above 0 but below 100. "
                    if score_outliers is not None and score_outliers > 0:
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                    score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                    status_message.append(score_msg)
                    get_effective_logger().debug(
                        f'set_wlk_status, final score re-evaluation: object="{record.get("object")}", '
                        f'total_score="{total_score}", downgrading red to orange (0 < score < 100)'
                    )
                else:
                    # If outlier is present but score_outliers < 100, it was already set to isOutlier=2
                    # in get_outliers_status, so we can still apply score-based logic
                    if score_outliers is not None and score_outliers < 100:
                        object_state = "orange"
                        score_msg = f"Entity has an impact score of {total_score:.1f} (base score: {base_score:.1f}), which is above 0 but below 100. "
                        score_msg += f"Outlier anomalies detected with a score of {score_outliers:.1f}. "
                        score_msg += "This indicates potential anomalies that require attention but do not yet warrant a critical alert status."
                        status_message.append(score_msg)
                        get_effective_logger().debug(
                            f'set_wlk_status, final score re-evaluation: object="{record.get("object")}", '
                            f'total_score="{total_score}", score_outliers="{score_outliers}", '
                            f'downgrading red to orange (outlier score too low)'
                        )
                    else:
                        get_effective_logger().debug(
                            f'set_wlk_status, final score re-evaluation: object="{record.get("object")}", '
                            f'total_score="{total_score}", keeping red state (outlier score >= 100)'
                        )
        elif (
            total_score is not None and total_score == 0
            and dynamic_thresholds
            and object_state not in ["green", "blue"]
            and isOutlier != 1
            and (score_outliers is None or score_outliers <= 0)
            and orphan != 1
            and not (isDelayed == 1 and cron_exec_sequence_sec > 0)
            and isUnderMonitoring is not False
        ):
            # No threshold breaches, no score, no other anomalies — recover to green
            object_state = "green"
            status_message.clear()
            status_message.append(
                f"The entity status is complying with monitoring rules "
                f"(status: {status}, status_description: {status_description})"
            )
            anomaly_reason.clear()
            anomaly_reason.append("none")
            get_effective_logger().debug(
                f'set_wlk_status, final score re-evaluation: object="{record.get("object")}", '
                f'total_score="{total_score}", recovering to green (no threshold breaches, no anomalies)'
            )

    #
    # Out of monitoring days and hours management (post-scoring)
    # Monitoring time policy takes precedence over scoring — entities outside
    # their monitoring window must never be promoted to red by scoring logic
    #
    if object_state == "red":
        if isUnderMonitoring is False:
            object_state = "orange"

    # Fallback: manual score influence raised total_score > 0 but no actual
    # anomaly was detected — populate status_message / anomaly_reason so the
    # UI can explain the non-green state.
    apply_manual_score_without_anomaly_fallback(
        record,
        score_definition,
        total_score,
        score,
        status_message,
        anomaly_reason,
        object_state,
    )

    # form status_message_json
    status_message_json["status_message"] = status_message
    status_message_json["anomaly_reason"] = anomaly_reason

    # Add score information to status_message_json for UI display (sorted alphabetically)
    # Use total_score if calculated (hybrid scoring), otherwise use base score
    if total_score is not None:
        status_message_json["score"] = float(total_score)
        # Update record score to reflect the calculated total_score for UI consistency
        record["score"] = float(total_score)
        # Add score definition for drilldown modal
        if score_definition:
            status_message_json["score_definition"] = score_definition
            record["score_definition"] = json.dumps(score_definition) if isinstance(score_definition, dict) else score_definition
    elif score is not None:
        status_message_json["score"] = float(score)
    if score_outliers is not None:
        status_message_json["score_outliers"] = float(score_outliers)
    if total_score is not None:
        status_message_json["total_score"] = float(total_score)

    # get disruption_duration
    if not disruption_queue_record:
        record["disruption_min_time_sec"] = 0

    else:

        logger.debug(
            f'disruption_queue_record="{disruption_queue_record}", getting disruption_duration'
        )

        disruption_object_state = disruption_queue_record.get("object_state", "green")
        try:
            disruption_min_time_sec = int(
                disruption_queue_record.get("disruption_min_time_sec", 0)
            )
        except:
            disruption_min_time_sec = 0
        # add to the record
        record["disruption_min_time_sec"] = disruption_min_time_sec

        try:
            disruption_start_epoch = float(
                disruption_queue_record.get("disruption_start_epoch", 0)
            )
        except:
            disruption_start_epoch = 0

        # Case 1: Entity is no longer in alert state (not red)
        if object_state != "red":
            # Only update if we were previously tracking a disruption
            if disruption_object_state == "red":
                disruption_queue_record["object_state"] = object_state
                disruption_queue_record["disruption_start_epoch"] = 0
                disruption_queue_record["mtime"] = time.time()

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")
            return object_state, status_message, status_message_json, anomaly_reason

        # Case 2: Entity is in alert state (red)
        if object_state == "red":
            current_time = time.time()

            # If this is a new disruption, start tracking it
            if disruption_object_state != "red":
                disruption_queue_record["object_state"] = "red"
                disruption_queue_record["disruption_start_epoch"] = current_time
                disruption_queue_record["mtime"] = current_time

                try:
                    disruption_queue_update(
                        disruption_queue_collection, disruption_queue_record
                    )
                except Exception as e:
                    logger.error(f"error updating disruption_queue_record: {e}")

                # For new disruptions, if min time is set, show as blue with message
                if disruption_min_time_sec > 0:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is 0 which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message
                return object_state, status_message, status_message_json, anomaly_reason

            # If we're already tracking a disruption, check duration
            if disruption_min_time_sec > 0:
                try:
                    disruption_duration = current_time - disruption_start_epoch
                except Exception as e:
                    logger.error(f"error calculating disruption_duration: {e}")
                    disruption_duration = 0

                # If duration hasn't breached threshold, show as blue with message
                if disruption_duration < disruption_min_time_sec:
                    object_state = "blue"
                    status_message.append(
                        f"Minimal disruption time is configured for this entity, the current disruption duration is {convert_seconds_to_duration(disruption_duration)} which does not breach yet the minimal disruption time of {convert_seconds_to_duration(disruption_min_time_sec)}"
                    )
                    status_message_json["status_message"] = status_message

    # anomaly_reason sanitify check, if the list has more than 1 item, and contains "none", remove it
    if isinstance(anomaly_reason, list):
        if len(anomaly_reason) > 1 and "none" in anomaly_reason:
            anomaly_reason.remove("none")

    # return
    get_effective_logger().debug(
        f'set_wlk_status, object="{record.get("object")}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
    )

    return object_state, status_message, status_message_json, anomaly_reason


def ack_check(object_value, ack_collection_keys, ack_collection_dict, record):
    """
    Updates record with ack information if object_value exists in ack_collection_keys
    and the object categories match.
    """

    ack_defaults = {
        "ack_state": "inactive",
        "ack_type": "N/A",
        "ack_comment": "N/A",
        "ack_expiration": "N/A",
        "ack_mtime": "N/A",
    }

    if object_value in ack_collection_keys:
        ack_record = ack_collection_dict.get(object_value)
        # Check if ack_record exists and object_category matches
        if ack_record and ack_record.get("object_category") == record.get(
            "object_category"
        ):
            # Extract ack information from ack_record
            for key in ack_defaults.keys():
                record[key] = ack_record.get(key, ack_defaults[key])
        else:
            record.update(ack_defaults)
    else:
        record.update(ack_defaults)


def define_state_icon_code(record):
    """
    Determines the state_icon_code based on the object_state and ack_state
    contained within the record dictionary.

    Args:
    - record (dict): A dictionary containing 'object_state' and 'ack_state'.

    Returns:
    - str: The state_icon_code determined based on the provided conditions.
    """
    object_state = record.get("object_state")
    ack_state = record.get("ack_state")

    # Define a mapping based on the Splunk macro conditions
    state_icon_code_mapping = {
        ("green", "inactive"): "001",
        ("green", "active"): "002",
        ("green", None): "003",
        ("red", "inactive"): "004",
        ("red", "active"): "005",
        ("red", None): "006",
        ("orange", "inactive"): "007",
        ("orange", "active"): "008",
        ("orange", None): "009",
        ("blue", "inactive"): "010",
        ("blue", "active"): "011",
        ("blue", None): "012",
    }

    # Fallback code if none of the conditions match
    default_code = "999"

    # Determine state_icon_code based on object_state and ack_state
    state_icon_code = state_icon_code_mapping.get(
        (object_state, ack_state),
        state_icon_code_mapping.get((object_state, None), default_code),
    )

    return state_icon_code


def outliers_readiness(record):
    """
    Updates the record with outliers_readiness, OutliersIsOk, and OutliersStatus based on the record's values.
    Ensures robust handling of missing or non-integer isOutlier values.
    """
    # Set outliers_readiness based on its current value
    record["outliers_readiness"] = (
        "True" if record.get("outliers_readiness") == "True" else "False"
    )

    # Safely get and convert isOutlier to an integer
    try:
        is_outlier = int(record.get("isOutlier", 0))
    except ValueError:
        # Handle case where conversion fails
        is_outlier = 0

    # Determine OutliersIsOk based on isOutlier
    record["OutliersIsOk"] = 1 if is_outlier == 0 else 0

    # Set OutliersStatus based on OutliersIsOk (always use text-based status)
    record["OutliersStatus"] = "green" if record["OutliersIsOk"] == 1 else "red"


def sampling_anomaly_status(record):
    """
    Updates the record with SamplingIsOk and SamplingStatus based on the isAnomaly field.
    """

    # get isAnomaly
    try:
        isAnomaly = int(record.get("isAnomaly", 0))
    except Exception as e:
        isAnomaly = 0

    # define SamplingIsOk
    record["SamplingIsOk"] = 1 if isAnomaly == 0 else 1

    # define SamplingStatus (always use text-based status)
    record["SamplingStatus"] = "green" if record["SamplingIsOk"] == 1 else "red"


def logical_group_lookup(
    object_value,
    logicalgroup_members_collection_keys,
    logicalgroup_members_collection_dict,
    record,
):
    """
    Updates record with Logical Group information if object_value exists in lg_collection_keys.
    """

    logicalgroup_defaults = {
        "object_group_key": None,
        "object_group_name": None,
    }

    if object_value in logicalgroup_members_collection_keys:
        logicalgroup_record = logicalgroup_members_collection_dict.get(object_value)
        # Extract ack information from ack_record
        for key in logicalgroup_defaults.keys():
            record[key] = logicalgroup_record.get(key, logicalgroup_defaults[key])
    else:
        # for key in logicalgroup_defaults, remove the key from record if exists
        for key in logicalgroup_defaults.keys():
            if key in record:
                del record[key]


def set_feeds_lag_summary(record, component):
    """
    Generates a lag summary based on the data_last_lag_seen and data_last_ingestion_lag_seen fields
    """

    if component in ["dsm", "dhm"]:

        try:
            data_last_lag_seen = int(
                round(float(record.get("data_last_lag_seen", 0)), 0)
            )
        except Exception as e:
            data_last_lag_seen = 0
        try:
            data_last_ingestion_lag_seen = int(
                round(float(record.get("data_last_ingestion_lag_seen", 0)), 0)
            )
        except Exception as e:
            data_last_ingestion_lag_seen = 0

        if data_last_lag_seen > 60 or data_last_ingestion_lag_seen < -60:
            data_last_lag_seen_duration = (
                f"{convert_seconds_to_duration(data_last_lag_seen)}"
            )
        elif data_last_lag_seen == 0:
            data_last_lag_seen_duration = "0 sec"
        elif data_last_lag_seen < 60:
            data_last_lag_seen_duration = f"-{data_last_lag_seen} sec"
        else:
            data_last_lag_seen_duration = f"{data_last_lag_seen} sec"

        if data_last_ingestion_lag_seen > 60 or data_last_ingestion_lag_seen < -60:
            data_last_ingestion_lag_seen_duration = (
                f"{convert_seconds_to_duration(data_last_ingestion_lag_seen)}"
            )
        elif data_last_ingestion_lag_seen == 0:
            data_last_ingestion_lag_seen_duration = "0 sec"
        elif data_last_ingestion_lag_seen < 60:
            data_last_ingestion_lag_seen_duration = (
                f"-{data_last_ingestion_lag_seen} sec"
            )
        else:
            data_last_ingestion_lag_seen_duration = (
                f"{data_last_ingestion_lag_seen} sec"
            )

        # return
        lag_summary = (
            f"{data_last_lag_seen_duration} / {data_last_ingestion_lag_seen_duration}"
        )

    elif component in ["mhm"]:

        # original logic: lag_summary= if(last_lag_seen>60, tostring(last_lag_seen, "duration"), last_lag_seen . " sec")

        try:
            last_lag_seen = int(round(float(record.get("last_lag_seen", 0)), 0))
        except Exception as e:
            last_lag_seen = 0
        if last_lag_seen > 60:
            lag_summary = f"{convert_seconds_to_duration(last_lag_seen)}"
        else:
            lag_summary = f"{last_lag_seen} sec"

    return lag_summary


def set_feeds_thresholds_duration(record):

    try:
        data_max_delay_allowed = int(
            round(float(record.get("data_max_delay_allowed", 0)), 0)
        )
    except Exception as e:
        data_max_delay_allowed = 0
    data_max_delay_allowed_duration = convert_seconds_to_duration(
        data_max_delay_allowed
    )
    try:
        data_max_lag_allowed = int(
            round(float(record.get("data_max_lag_allowed", 0)), 0)
        )
    except Exception as e:
        data_max_lag_allowed = 0
    data_max_lag_allowed_duration = convert_seconds_to_duration(data_max_lag_allowed)

    return data_max_delay_allowed_duration, data_max_lag_allowed_duration


def set_cim_duration(record):

    try:
        tracker_last_duration = int(
            round(float(record.get("tracker_last_duration", 0)), 0)
        )
    except Exception as e:
        tracker_last_duration = 0
    tracker_last_duration = convert_seconds_to_duration(tracker_last_duration)

    return tracker_last_duration


def dsm_sampling_lookup(
    object_value, sampling_collection_keys, sampling_collection_dict, record
):
    """
    Updates record with ack information if object_value exists in sampling_collection_keys
    and the object categories match.
    """

    sampling_defaults = {
        "data_sample_feature": "enabled",
        "data_sample_status_message": {
            "state": "pending",
            "desc": "Data Sampling is pending and has not been performed yet for this entity",
        },
        "data_sample_status_colour": "N/A",
        "data_sample_anomaly_reason": "N/A",
    }

    if object_value in sampling_collection_keys:
        sampling_record = sampling_collection_dict.get(object_value)

        current_data_sample_feature = sampling_record.get(
            "data_sample_feature", "enabled"
        )

        if current_data_sample_feature == "enabled":
            for key in sampling_defaults.keys():
                record[key] = sampling_record.get(key, sampling_defaults[key])
        elif current_data_sample_feature == "disabled_auto":
            for key in sampling_defaults.keys():
                record[key] = sampling_record.get(key, sampling_defaults[key])
        else:
            sampling_fields = {
                "data_sample_feature": "disabled",
                "data_sample_status_message": {
                    "state": "disabled",
                    "desc": "Data sampling features are currently disabled for this entity.",
                },
                "data_sample_status_colour": "grey",
                "data_sample_anomaly_reason": "None",
            }
            for key in sampling_fields.keys():
                record[key] = sampling_fields[key]

    else:
        record.update(sampling_defaults)


def outliers_data_lookup(
    key_value,
    outliers_data_collection_keys,
    outliers_data_collection_dict,
    outliers_rules_collection_keys,
    outliers_rules_collection_dict,
    record,
):
    """
    Updates record with outliers information if object_value exists in outliers_data_collection_keys
    and the object categories match.
    """

    #
    # Handle data
    #

    outliers_data_defaults = {
        "isOutlier": 0,
        "isOutlierReason": "",
        "models_in_anomaly": "",
        "lastIsOutlierReason": "",
        "lastIsOutlierReason_models": "",
        "lastIsOutlierReason_mtime": "",
    }

    if key_value in outliers_data_collection_keys:
        outliers_data_record = outliers_data_collection_dict.get(key_value)
        for key in outliers_data_defaults.keys():
            record[key] = outliers_data_record.get(key, outliers_data_defaults[key])
    else:
        record.update(outliers_data_defaults)

    #
    # Handle rules
    #

    outliers_rules_defaults = {
        "is_disabled": 0,
    }

    if key_value in outliers_rules_collection_keys:
        outliers_rules_record = outliers_rules_collection_dict.get(key_value)

        for key in outliers_rules_defaults.keys():
            if key == "is_disabled":
                record["OutliersDisabled"] = outliers_rules_record.get(
                    key, outliers_rules_defaults[key]
                )
            else:
                record[key] = outliers_rules_record.get(
                    key, outliers_rules_defaults[key]
                )
    else:
        for key, value in outliers_rules_defaults.items():
            if key == "is_disabled":
                record["OutliersDisabled"] = value
            else:
                record[key] = value


def get_coll_docs_ref(collection, docs_collection_name):
    collection_records = []
    collection_records_dict = {}
    collection_members_list = []
    collection_members_dict = {}

    end = False
    skip_tracker = 0
    while not end:
        process_collection_records = collection.data.query(skip=skip_tracker)
        if process_collection_records:
            for item in process_collection_records:
                collection_records.append(item)
                collection_records_dict[item.get("_key")] = {
                    "doc_note": item.get("doc_note"),
                    "doc_link": item.get("doc_link"),
                    "object_members": item.get("object", []),
                }

                doc_members = item.get("object", [])
                # add members in collection_members_list, also create a dict per member
                for member in doc_members:
                    if member not in collection_members_list:
                        collection_members_list.append(member)
                        collection_members_dict[member] = {
                            "doc_key": item.get("_key"),
                            "doc_note": item.get("doc_note"),
                            "doc_link": item.get("doc_link"),
                            "object_members": item.get("object", []),
                        }
            skip_tracker += len(process_collection_records)
        else:
            end = True

    return (
        collection_records,
        collection_records_dict,
        collection_members_list,
        collection_members_dict,
    )


def docs_ref_lookup(
    docs_is_global,
    docs_note_default_global,
    docs_link_default_global,
    object_value,
    docs_members_collection_keys,
    docs_members_collection_dict,
    record,
):
    """
    Updates record with docs ref information if object_value exists in docs_members_collection_keys.
    """

    docs_defaults = {
        "doc_is_global": docs_is_global,
        "doc_note": docs_note_default_global,
        "doc_link": docs_link_default_global,
    }

    if object_value in docs_members_collection_keys:
        doc_record = docs_members_collection_dict.get(object_value)

        # override doc_is_global to False
        record["doc_is_global"] = False

        # Extract information from record
        for key in docs_defaults.keys():
            if key != "doc_is_global":
                record[key] = doc_record.get(key, docs_defaults[key])
    else:
        record.update(docs_defaults)


def wlk_disabled_apps_lookup(
    app_value,
    apps_enablement_collection_keys,
    apps_enablement_collection_dict,
    record,
):
    """
    Updates record with apps_disabled ref information if object_value exists in apps_enablement_collection_keys.
    """

    apps_enablement_defaults = {
        "app_is_enabled": "True",
    }

    if app_value in apps_enablement_collection_keys:
        lookup_record = apps_enablement_collection_dict.get(app_value)
        # Extract ack information from record
        record["app_is_enabled"] = lookup_record.get("enabled", "True")
    else:
        record.update(apps_enablement_defaults)


def wlk_versioning_lookup(
    key_value,
    versioning_collection_keys,
    versioning_collection_dict,
    record,
):
    """
    Updates record with apps_disabled ref information if object_value exists in cron_exec_sequence_sec_collection_keys.
    """

    versioning_defaults = {
        "cron_exec_sequence_sec": 0,
        "object_description": "No description",
        "versioning_available": "False",
    }

    # lookup and override if found, otherwise do nothing
    if key_value in versioning_collection_keys:
        record["versioning_available"] = "True"
        lookup_record = versioning_collection_dict.get(key_value)

        for key in versioning_defaults.keys():
            if key == "object_description":
                lookup_record_description = lookup_record.get("description", None)
                # if len of lookup_record_description is 0, then use the default
                if lookup_record_description:
                    if len(lookup_record_description) == 0:
                        record["object_description"] = versioning_defaults[
                            "object_description"
                        ]
                    else:
                        record["object_description"] = lookup_record_description
                else:
                    record["object_description"] = versioning_defaults[
                        "object_description"
                    ]

            elif key == "versioning_available":
                record["versioning_available"] = "True"
            else:
                record[key] = lookup_record.get(key, versioning_defaults[key])

        get_effective_logger().debug(
            f'versioning found for object="{record.get("object")}", object_key="{record.get("keyid")}", using key_value="{key_value}"'
        )

    else:
        record.update(versioning_defaults)
        get_effective_logger().debug(
            f'no versioning found for object="{record.get("object")}", object_key="{record.get("keyid")}", using key_value="{key_value}"'
        )


def wlk_orphan_lookup(
    key_value,
    orphan_collection_keys,
    orphan_collection_dict,
    record,
):
    """
    Updates record with orphan ref information if key_value exists in orphan_collection_keys.
    """

    orphan_defaults = {
        "orphan": 0,
    }

    if key_value in orphan_collection_keys:
        lookup_record = orphan_collection_dict.get(key_value)
        record["orphan"] = lookup_record.get("orphan", 0)
    else:
        record.update(orphan_defaults)


def apply_blocklist(record, blocklist_not_regex, blocklist_regex):
    """
    Determines whether a record should be appended based on blocklist rules.

    :param record: The record to check.
    :param blocklist_not_regex: Dict of blocklist rules without regex.
    :param blocklist_regex: Dict of blocklist rules with regex.
    :return: True if the record should be appended, False otherwise.
    """

    def match_not_regex(field_value, rule):
        """
        Check if a field value matches a non-regex blocklist rule.
        """
        if isinstance(field_value, list):
            return any(item == rule.get("object") for item in field_value)
        else:
            return field_value == rule.get("object")

    def match_regex(field_value, rule):
        """
        Check if a field value matches a regex blocklist rule.
        """
        if isinstance(field_value, list):
            return any(re.match(rule.get("object"), item) for item in field_value)
        else:
            return re.match(rule.get("object"), field_value)

    # define index and add to the record, using data_index if available and turn into a list from csv
    if "data_index" in record:
        record["index"] = record["data_index"].split(",")

    # same for data_sourcetype and sourcetype
    if "data_sourcetype" in record:
        record["sourcetype"] = record["data_sourcetype"].split(",")

    # metric_category is called equally in record and blocklist, but it can be a list too
    if "metric_category" in record:
        record["metric_category"] = record["metric_category"].split(",")

    # Check blocklist without regex
    for _, rule in blocklist_not_regex.items():
        object_category = rule.get("object_category")
        if object_category in record and match_not_regex(record[object_category], rule):
            return False  # Match found in blocklist not regex, do not append

    # Check blocklist with regex
    for _, rule in blocklist_regex.items():
        object_category = rule.get("object_category")
        if object_category in record and match_regex(record[object_category], rule):
            return False  # Regex match found in blocklist, do not append

    # before returning, remove index and sourcetype from the record
    if "index" in record:
        del record["index"]
    if "sourcetype" in record:
        del record["sourcetype"]
    # turn metric_category is existing back to a comma separated string
    if "metric_category" in record:
        record["metric_category"] = ",".join(record["metric_category"])

    return True  # If no blocklist rules matched, append the record


def dsm_check_default_thresholds(record, trackme_conf):
    """
    Verify that the record contains expected fields, if not or if they are None, set them to default values.
    """

    # Define a dictionary for the DSM fields and their respective default values
    fields_defaults = {
        "data_max_delay_allowed": trackme_conf["splk_general"][
            "splk_general_dsm_delay_default"
        ],
        "data_max_lag_allowed": trackme_conf["splk_general"][
            "splk_general_dsm_threshold_default"
        ],
        "data_override_lagging_class": "false",
        "allow_adaptive_delay": "true",
    }

    # Iterate through the fields to check their presence and value
    for field, default_value in fields_defaults.items():
        # Check if field is missing or explicitly set to None
        if field not in record or record[field] is None:
            record[field] = default_value
        else:
            # Additional checks for numeric fields to ensure they can be converted to float
            if field in ["data_max_delay_allowed", "data_max_lag_allowed"]:
                try:
                    # Attempt to convert to float to validate
                    record[field] = float(record[field])
                except ValueError:
                    # Set to default if conversion fails
                    record[field] = default_value


def dhm_check_default_thresholds(record, trackme_conf):
    """
    Verify that the record contains expected fields, if not or if they are None, set them to default values.
    """

    # Define a dictionary for the DHM fields and their respective default values
    fields_defaults = {
        "data_max_delay_allowed": trackme_conf["splk_general"][
            "splk_general_dhm_delay_default"
        ],
        "data_max_lag_allowed": trackme_conf["splk_general"][
            "splk_general_dhm_threshold_default"
        ],
        "data_override_lagging_class": "false",
        "allow_adaptive_delay": "true",
        "splk_dhm_alerting_policy": "global_policy",
    }

    # Iterate through the fields to check their presence and value
    for field, default_value in fields_defaults.items():
        # Check if field is missing or explicitly set to None
        if field not in record or record[field] is None:
            record[field] = default_value
        else:
            # Additional checks for numeric fields to ensure they can be converted to float
            if field in ["data_max_delay_allowed", "data_max_lag_allowed"]:
                try:
                    # Attempt to convert to float to validate
                    record[field] = float(record[field])
                except ValueError:
                    # Set to default if conversion fails
                    record[field] = default_value


def dynamic_priority_lookup(
    key_value, priority_collection_keys, priority_collection_dict, record
):
    """
    Updates record with dynamic priority information if key_value exists in priority_collection_keys.
    """

    # get the value for priority_external and priority_reason
    priority_external = record.get("priority_external", None)
    priority_reason = record.get("priority_reason", "entity_managed")

    # first, check the value of priority_updated, if does not exist in the record, set to 0 and update the record
    try:
        priority_updated = int(record["priority_updated"])
        # valid option are 0 or 1, if not one of these, set to 0
        if priority_updated not in [0, 1]:
            priority_updated = 0
    except Exception as e:
        priority_updated = 0

    # add to record as priority_updated
    record["priority_updated"] = priority_updated

    # priority policies always have precedence
    if key_value in priority_collection_keys:
        dynamic_priority_record = priority_collection_dict.get(key_value)
        dynamic_priority = dynamic_priority_record.get("priority", None)
        dynamic_priority_reason = dynamic_priority_record.get(
            "priority_reason", "entity_managed"
        )

        # if we have a match, and a priority, then update the record, otherwise do nothing
        if dynamic_priority:

            # add to record as priority_policy_value
            record["priority_policy_value"] = dynamic_priority

            if priority_updated != 1:
                record["priority"] = dynamic_priority
                get_effective_logger().debug(
                    f'match found applying dynamic priority="{dynamic_priority}" for object="{record.get("object")}", key="{key_value}", priority_reason="{dynamic_priority_reason}"'
                )
            else:
                get_effective_logger().debug(
                    f'priority_updated is set to 1, skipping dynamic priority="{dynamic_priority}" for object="{record.get("object")}", key="{key_value}", priority_reason="{dynamic_priority_reason}"'
                )
            record["priority_policy_id"] = dynamic_priority_reason
            record["priority_reason"] = f"priority policy id: {dynamic_priority_reason}"

        # no match, set to default reason
        else:
            # if priority_reason contains "priority policy id" but we have no match, then set to default
            # otherwise, keep the existing value, it could be externally managed
            # also check that the fields is in record first
            if "priority_reason" in record:
                if "priority policy id" in record["priority_reason"]:
                    record["priority_reason"] = "entity_managed"
            else:
                record["priority_reason"] = "entity_managed"

    elif priority_external:

        # attempt to get priority_reason, it not set, define to "externally_managed"
        priority_reason = record.get("priority_reason", "externally_managed")

        # if priority_external is in one of low, medium, high, critical, pending, then update
        if priority_external in ["low", "medium", "high", "critical", "pending"]:
            if priority_updated != 1:
                record["priority"] = priority_external
                get_effective_logger().debug(
                    f'applying external priority="{priority_external}" for object="{record.get("object")}", priority_reason="{priority_reason}"'
                )
            else:
                get_effective_logger().debug(
                    f'priority_updated is set to 1, skipping external priority="{priority_external}" for object="{record.get("object")}", priority_reason="{priority_reason}"'
                )
            record["priority_reason"] = f"{priority_reason}"

        else:
            # if priority_external is not in one of low, medium, high, critical, pending, log a warning as we refused this value
            get_effective_logger().warning(
                f'external priority="{priority_external}" for object="{record.get("object")}" is not in the list of allowed values, priority_reason="{priority_reason}"'
            )

    else:
        # simply set priority_reason to the default value
        record["priority_reason"] = "entity_managed"
        get_effective_logger().debug(
            f'no match found for object="{record.get("object")}", key="{key_value}", priority_reason="{priority_reason}"'
        )


def dynamic_tags_lookup(key_value, tags_collection_keys, tags_collection_dict, record):
    """
    Updates record with dynamic tags information if key_value exists in tags_collection_keys.
    """

    if key_value in tags_collection_keys:
        dynamic_tags_record = tags_collection_dict.get(key_value)
        dynamic_tags = dynamic_tags_record.get("tags_auto", None)
        dynamic_tags_policies = dynamic_tags_record.get("tags_auto_policies", None)

        # if we have a match, then update the record, otherwise do nothing
        if dynamic_tags:
            record["tags_auto"] = dynamic_tags
            if dynamic_tags_policies:
                record["tags_auto_policies"] = dynamic_tags_policies
            get_effective_logger().debug(
                f'match found applying dynamic tags="{dynamic_tags}" for object="{record.get("object")}", key="{key_value}"'
            )


def dynamic_labels_lookup(key_value, component, labels_def_collection_dict, labels_assign_collection_dict, record):
    """
    Updates record with resolved label information.
    Uses deterministic key {component}:{key_value} to look up assignments,
    then resolves label_ids against definitions.

    Sets two fields:
      - labels_objects: full JSON array of {label_id, label_name, label_color, label_description} (for UI rendering)
      - labels: sorted list of label name strings (for filtering, Virtual Groups, search)
    """

    assign_key = f"{component}:{key_value}"
    assignment = labels_assign_collection_dict.get(assign_key)

    if assignment:
        try:
            label_ids = json.loads(assignment.get("label_ids", "[]"))
        except Exception:
            label_ids = []

        resolved = []
        label_names = []
        for lid in label_ids:
            label_def = labels_def_collection_dict.get(lid)
            if label_def:
                name = label_def.get("label_name", "")
                resolved.append({
                    "label_id": lid,
                    "label_name": name,
                    "label_color": label_def.get("label_color", "#9e9e9e"),
                    "label_description": label_def.get("label_description", ""),
                })
                if name:
                    label_names.append(name)
        record["labels_objects"] = resolved
        record["labels"] = sorted(label_names)
    else:
        record["labels_objects"] = []
        record["labels"] = []


def dynamic_sla_class_lookup(
    key_value, sla_collection_keys, sla_collection_dict, record
):
    """
    Updates record with dynamic SLA class information if key_value exists in sla_collection_keys.
    Respects sla_updated flag to protect manual overrides (same pattern as priority_updated).
    """

    # first, check the value of sla_updated, if does not exist in the record, set to 0 and update the record
    try:
        sla_updated = int(record["sla_updated"])
        # valid option are 0 or 1, if not one of these, set to 0
        if sla_updated not in [0, 1]:
            sla_updated = 0
    except Exception as e:
        sla_updated = 0

    # add to record as sla_updated
    record["sla_updated"] = sla_updated

    if key_value in sla_collection_keys:
        dynamic_sla_record = sla_collection_dict.get(key_value)
        dynamic_sla = dynamic_sla_record.get("sla_class", None)
        dynamic_sla_reason = dynamic_sla_record.get(
            "sla_class_reason", "entity_managed"
        )

        # if we have a match, and a sla_class, then update the record, otherwise do nothing
        if dynamic_sla:

            # add to record as sla_policy_value
            record["sla_policy_value"] = dynamic_sla

            if sla_updated != 1:
                record["sla_class"] = dynamic_sla
                get_effective_logger().debug(
                    f'match found applying dynamic sla_class="{dynamic_sla}" for object="{record.get("object")}", key="{key_value}", sla_class_reason="{dynamic_sla_reason}"'
                )
            else:
                get_effective_logger().debug(
                    f'sla_updated is set to 1, skipping dynamic sla_class="{dynamic_sla}" for object="{record.get("object")}", key="{key_value}", sla_class_reason="{dynamic_sla_reason}"'
                )
            record["sla_policy_id"] = dynamic_sla_reason
            record["sla_class_reason"] = f"sla_policy_id: {dynamic_sla_reason}"

        # no match, set to default reason
        else:
            if "sla_class_reason" in record:
                if "sla_policy_id" in str(record.get("sla_class_reason", "")):
                    record["sla_class_reason"] = "entity_managed"
            else:
                record["sla_class_reason"] = "entity_managed"

    else:
        # no match in sub-collection, check if previously managed by policy
        if "sla_class_reason" in record:
            if "sla_policy_id" in str(record.get("sla_class_reason", "")):
                record["sla_class_reason"] = "entity_managed"
        else:
            record["sla_class_reason"] = "entity_managed"


def get_sla_timer(record, sla_classes, sla_default_class):
    """
    Calculates and render the sla_timer
    """

    # a JSON object comntaining a summary for sla information for rendering purposes
    sla_message_json = {}

    # check sla_class (if not in the record, use sla_default_class)
    sla_class = record.get("sla_class", None)
    if not sla_class:
        sla_class = sla_default_class
        record["sla_class"] = sla_default_class

    else:
        # get sla_threshold from sla_classes, if the mentioned sla_class is not found in sla_classes, use the default and replace the record
        if sla_class not in sla_classes:
            sla_class = sla_default_class
            record["sla_class"] = sla_default_class

    # add to sla_message_json
    sla_message_json["sla_class"] = sla_class

    # get sla_threshold from sla_classes
    try:
        sla_threshold = int(sla_classes[sla_class]["sla_threshold"])
    except Exception as e:
        sla_threshold = 86400

    # convert to sla_threshold_duration
    record["sla_threshold_duration"] = convert_seconds_to_duration(sla_threshold)

    # add to record
    record["sla_threshold"] = sla_threshold

    # add to sla_message_json
    sla_message_json["object"] = record.get("object")

    # Calculates
    # for sla, we need to use the current object_state from the KVstore, rather than realtime calculate object_state
    object_state = record.get("kvcurrent_object_state", "red")

    # we will use the realtime object_state to manage a different SLA message if we detect that the KVstore object_state is not yet updated
    realtime_object_state = record.get("object_state", "red")

    sla_message_json["object_state"] = object_state

    if object_state == "red":

        try:
            latest_flip_time = float(record.get("latest_flip_time", 0))
        except Exception as e:
            latest_flip_time = 0

        if latest_flip_time > 0:
            sla_timer = int(round(float(int(time.time()) - latest_flip_time), 0))
        else:
            sla_timer = 0

        # add sla_timer
        record["sla_timer"] = sla_timer
        sla_message_json["sla_timer"] = sla_timer

        # calculate sla_timer_duration
        sla_timer_duration = convert_seconds_to_duration(sla_timer)

        # add
        record["sla_timer_duration"] = convert_seconds_to_duration(sla_timer)
        sla_message_json["sla_timer_duration"] = sla_timer_duration

        # SLA breached
        sla_is_breached = 1 if sla_timer > sla_threshold else 0
        record["sla_is_breached"] = sla_is_breached
        sla_message_json["sla_is_breached"] = sla_is_breached

        # add an sla_message
        if sla_is_breached == 1:

            sla_message = f"SLA breached, the entity has been in a red state for more than {convert_seconds_to_duration(sla_timer)} (sla_class: {sla_class}, sla_class_threshold: {convert_seconds_to_duration(sla_threshold)}, sla_timer_sec: {int(round(sla_timer, 0))} sec, sla_threshold_sec: {sla_threshold} sec)"
            record["sla_message"] = sla_message
            sla_message_json["sla_message"] = sla_message

        else:
            sla_message = f"SLA is not breached, the entity has been in a red state for {convert_seconds_to_duration(sla_timer)} (sla_class: {sla_class}, sla_class_threshold: {convert_seconds_to_duration(sla_threshold)}, sla_timer_sec: {int(round(sla_timer, 0))} sec, sla_threshold_sec: {sla_threshold} sec)"
            record["sla_message"] = sla_message
            sla_message_json["sla_message"] = sla_message

    elif object_state == "green" and realtime_object_state == "red":
        record["sla_timer"] = 0
        sla_message_json["sla_timer"] = 0

        record["sla_timer_duration"] = "0 sec"
        sla_message_json["sla_timer_duration"] = "0 sec"

        record["sla_is_breached"] = 0
        sla_message_json["sla_is_breached"] = 0

        record["sla_message"] = (
            "SLA status refresh is pending, the realtime entity state is red and SLA will be reflected in the next minutes once the KVstore status is updated by trackers"
        )
        sla_message_json["sla_message"] = (
            "SLA status refresh is pending, the realtime entity state is red and SLA will be reflected in the next minutes once the KVstore status is updated by trackers"
        )

    else:
        record["sla_timer"] = 0
        sla_message_json["sla_timer"] = 0

        record["sla_timer_duration"] = "0 sec"
        sla_message_json["sla_timer_duration"] = "0 sec"

        record["sla_is_breached"] = 0
        sla_message_json["sla_is_breached"] = 0

        record["sla_message"] = "SLA is not breached, the entity is not in a red state"
        sla_message_json["sla_message"] = (
            "SLA is not breached, the entity is not in a red state"
        )

    # add sla_message_json to record
    record["sla_message_json"] = sla_message_json


def flx_thresholds_lookup(object_value, key_value, record, thresholds_collection_dict):
    """
    Updates record with dynamic thresholds information (field dynamic_thresholds) if key_value matches the object_id value in thresholds_collection_dict records.

    ex:

    {
        "c6745c4d9190e2f18bd83e4448a0584da54a832fa57dfd838b58940c8fced934": {
            "metric_name": "soar.mem_used_pct",
            "value": 80,
            "operator": ">",
            "condition_true": True,
            "mtime": 1747012850.5604594,
            "comment": "No comment for update.",
            "object_id": "199fc4f889ff4946181bb00f56aad44c7580dd87691de699e1c0d2fc851a1ec5",
            "_user": "nobody",
            "_key": "c6745c4d9190e2f18bd83e4448a0584da54a832fa57dfd838b58940c8fced934"
        }
    }


    """

    dynamic_thresholds = {}

    if thresholds_collection_dict:
        for key, value in thresholds_collection_dict.items():
            object_id = value.get("object_id", None)
            if object_id and object_id == key_value:
                # add the dynamic threshold record to the dynamic_thresholds dictionary
                dynamic_thresholds[key] = thresholds_collection_dict[key]

    # add the dynamic_thresholds dictionary to the record
    record["dynamic_thresholds"] = dynamic_thresholds

    return True


def flx_drilldown_searches_lookup(tenant_id, tracker_name, account, record, drilldown_searches_collection_dict):

    if drilldown_searches_collection_dict:

        # Helper function to expand tokens in drilldown_search string
        def expand_tokens(search_string, record):
            if not isinstance(search_string, str):
                return search_string
            
            result = ""
            i = 0
            while i < len(search_string):
                if search_string[i] == "$":
                    # Look for closing $
                    end = search_string.find("$", i + 1)
                    if end != -1:
                        token = search_string[i + 1 : end]
                        # Handle $result.<token_name>$ format
                        if token.startswith("result."):
                            token_name = token[7:]  # Remove "result." prefix
                        else:
                            token_name = token
                        # Replace if token_name exists in record
                        if token_name in record:
                            replacement = str(record[token_name])
                            result += replacement
                        else:
                            # No replacement, keep token as is
                            result += "$" + token + "$"
                        i = end + 1
                    else:
                        # No closing $, just add the rest
                        result += search_string[i:]
                        break
                else:
                    result += search_string[i]
                    i += 1
            return result

        # Handle concurrent trackers: tracker_name can be a JSON array string, comma-separated string, or a simple string
        tracker_names = []
        
        if tracker_name:
            if isinstance(tracker_name, str):
                try:
                    # Try to parse as JSON array (concurrent tracker format from KVstore)
                    parsed_tracker_names = json.loads(tracker_name)
                    if isinstance(parsed_tracker_names, list):
                        tracker_names = parsed_tracker_names
                    else:
                        # Single tracker name as string
                        tracker_names = [tracker_name]
                except (json.JSONDecodeError, TypeError):
                    # Not a JSON array, check if it's a comma-separated string (aggregated format)
                    if "," in tracker_name:
                        # Comma-separated string, split and strip whitespace
                        tracker_names = [tn.strip() for tn in tracker_name.split(",") if tn.strip()]
                    else:
                        # Single tracker name as string
                        tracker_names = [tracker_name]
            elif isinstance(tracker_name, list):
                # Already a list
                tracker_names = tracker_name
            else:
                # Fallback: convert to string and treat as single tracker
                tracker_names = [str(tracker_name)]
        
        # Collect all drilldown searches from all matching trackers
        drilldown_searches_list = []
        
        for tn in tracker_names:
            # Normalize tracker name using the dedicated function
            normalized_tracker_name = normalize_flx_tracker_name(tenant_id, tn)
            
            # Look up all matching entries in the collection
            for key, value in drilldown_searches_collection_dict.items():
                if value.get("tracker_name") == normalized_tracker_name:
                    # get drilldown_search, drilldown_search_earliest, drilldown_search_latest
                    drilldown_search = value.get("drilldown_search")
                    drilldown_search_earliest = value.get("drilldown_search_earliest")
                    drilldown_search_latest = value.get("drilldown_search_latest")
                    
                    if drilldown_search:
                        # expand tokens in drilldown_search if it's a string
                        expanded_search = expand_tokens(drilldown_search, record)
                        
                        # Add to list with tracker name for reference
                        drilldown_searches_list.append({
                            "drilldown_search": expanded_search,
                            "drilldown_search_earliest": drilldown_search_earliest or "-24h",
                            "drilldown_search_latest": drilldown_search_latest or "now",
                            "tracker_name": normalized_tracker_name,  # Include tracker name for UI display
                        })
        
        # Store drilldown searches as array for UI to iterate over
        if drilldown_searches_list:
            record["drilldown_searches"] = drilldown_searches_list
            
            # For backward compatibility, also set the first drilldown search as single values
            # This ensures existing UI code that expects drilldown_search, drilldown_search_earliest, drilldown_search_latest still works
            first_drilldown = drilldown_searches_list[0]
            record["drilldown_search"] = first_drilldown["drilldown_search"]
            record["drilldown_search_earliest"] = first_drilldown["drilldown_search_earliest"]
            record["drilldown_search_latest"] = first_drilldown["drilldown_search_latest"]
            
            return True

    return False


def flx_default_metrics_lookup(tenant_id, tracker_name, record, default_metrics_collection_dict):

    if default_metrics_collection_dict:

        # Handle concurrent trackers: tracker_name can be a JSON array string, comma-separated string, or a simple string
        tracker_names = []
        
        if tracker_name:
            if isinstance(tracker_name, str):
                try:
                    # Try to parse as JSON array (concurrent tracker format from KVstore)
                    parsed_tracker_names = json.loads(tracker_name)
                    if isinstance(parsed_tracker_names, list):
                        tracker_names = parsed_tracker_names
                    else:
                        # Single tracker name as string
                        tracker_names = [tracker_name]
                except (json.JSONDecodeError, TypeError):
                    # Not a JSON array, check if it's a comma-separated string (aggregated format)
                    if "," in tracker_name:
                        # Comma-separated string, split and strip whitespace
                        tracker_names = [tn.strip() for tn in tracker_name.split(",") if tn.strip()]
                    else:
                        # Single tracker name as string
                        tracker_names = [tracker_name]
            elif isinstance(tracker_name, list):
                # Already a list
                tracker_names = tracker_name
            else:
                # Fallback: convert to string and treat as single tracker
                tracker_names = [str(tracker_name)]
        
        # Normalize all tracker names and collect all matching metric names
        metric_names = []
        seen_metrics = set()  # Track unique metrics to avoid duplicates
        
        for tn in tracker_names:
            # Normalize tracker name using the dedicated function
            normalized_tracker_name = normalize_flx_tracker_name(tenant_id, tn)
            
            # Look up all matching entries in the collection
            for key, value in default_metrics_collection_dict.items():
                if value.get("tracker_name") == normalized_tracker_name:
                    metric_name = value.get("metric_name")
                    if metric_name and metric_name not in seen_metrics:
                        metric_names.append(metric_name)
                        seen_metrics.add(metric_name)
        
        # Set default_metric based on number of metrics found
        if metric_names:
            # If only one metric, keep as string for backward compatibility
            # If multiple metrics, return as array for UI multi-select support
            if len(metric_names) == 1:
                record["default_metric"] = metric_names[0]
            else:
                record["default_metric"] = metric_names
            return True

    # set to status
    record["default_metric"] = "status"
    return False


def flx_check_dynamic_thresholds(logger, dynamic_thresholds, metrics_record):
    """
    Checks if the dynamic thresholds are breached and updates the record accordingly.

    Returns:
        - threshold_alert: 1 if one or more thresholds are in alert, 0 otherwise
        - threshold_messages: list of messages indicating which thresholds are in alert
        - threshold_scores: list of scores for breached thresholds (defaults to 100 if not specified)
    """
    ops = {
        ">": operator.gt,
        "<": operator.lt,
        "==": operator.eq,
        "!=": operator.ne,
        ">=": operator.ge,
        "<=": operator.le,
    }

    if not isinstance(metrics_record, dict):
        try:
            metrics_record = json.loads(metrics_record)
        except Exception as e:
            logger.error(
                f'metrics_record="{metrics_record}" value can not be converted to dict, exception="{e}"'
            )
            return 0, [], []

    logger.debug(
        f'starting function flx_check_dynamic_thresholds, dynamic_thresholds="{json.dumps(dynamic_thresholds, indent=2)}", metrics_record="{json.dumps(metrics_record, indent=2)}"'
    )

    threshold_alert = 0
    threshold_messages = []
    threshold_scores = []

    for threshold_key, threshold in dynamic_thresholds.items():

        logger.debug(
            f'checking threshold_key="{threshold_key}", threshold="{json.dumps(threshold, indent=2)}"'
        )

        metric_name = threshold.get("metric_name")
        op_str = threshold.get("operator")
        condition_true = strict_interpret_boolean(threshold.get("condition_true"))
        # Get threshold score, default to 100 if not present (for backward compatibility with existing records)
        try:
            threshold_score = int(threshold.get("score", 100))
        except (TypeError, ValueError):
            threshold_score = 100

        if metric_name not in metrics_record:
            logger.debug(
                f'function flx_check_dynamic_thresholds, metric_name="{metric_name}" not found in metrics_record="{json.dumps(metrics_record, indent=2)}", skipping threshold (metric may not be available for this tracker)'
            )
            continue

        if op_str not in ops:
            logger.error(
                f'functionflx_check_dynamic_thresholds, op_str="{op_str}" not found in ops'
            )
            continue

        # Resolve variable threshold value if enabled
        variable_active_slot = None
        is_variable_threshold = False
        variable_threshold_enabled = str(threshold.get("variable_threshold_enabled", "false")).lower()
        if variable_threshold_enabled == "true":
            resolved_value, variable_active_slot, is_variable_threshold = resolve_variable_threshold_value(threshold)
            if is_variable_threshold and resolved_value is not None:
                # Use a shallow copy to avoid mutating the original threshold dict
                threshold = dict(threshold)
                threshold["value"] = resolved_value
                logger.debug(
                    f'function flx_check_dynamic_thresholds, variable threshold resolved: '
                    f'metric="{metric_name}", slot="{variable_active_slot}", resolved_value={resolved_value}'
                )

        # threshold value can be a string referencing a field in the metrics_record, or a proper numerical value
        threshold_num_parsed = False

        # first, try to load the threshold value as a float
        try:
            threshold_value = float(threshold.get("value"))
            threshold_num_parsed = True
        except (TypeError, ValueError):
            pass

        # if failed, try to load the threshold value from the field value referenced in the threshold value
        if not threshold_num_parsed and threshold.get("value") in metrics_record:
            try:
                threshold_value = float(metrics_record.get(threshold.get("value")))
                threshold_num_parsed = True
            except (TypeError, ValueError):
                pass

        # if both failed, log a warning message and skip the threshold
        if not threshold_num_parsed:
            logger.warning(
                f'function flx_check_dynamic_thresholds threshold_value value can not be converted to float, skipping threshold_record="{json.dumps(threshold, indent=2)}"'
            )
            continue

        try:
            metric_value = float(metrics_record.get(metric_name, 0))
        except (TypeError, ValueError):
            logger.error(
                f'function flx_check_dynamic_thresholds metric_value value can not be converted to float, skipping threshold_key="{threshold_key}"'
            )
            continue  # Skip if value can't be converted to float

        op_func = ops[op_str]
        match = op_func(metric_value, threshold_value)

        # Fixed logic: alert if the expected condition is NOT matched
        should_alert = (condition_true and not match) or (not condition_true and match)

        if should_alert:
            threshold_alert = 1
            if is_variable_threshold and variable_active_slot:
                threshold_messages.append(
                    f"Threshold condition is in alert: "
                    f"metric='{metric_name}', value={metric_value}, "
                    f"threshold={threshold_value} (variable, slot='{variable_active_slot}'), operator='{op_str}', "
                    f"condition_true={condition_true}"
                )
            else:
                threshold_messages.append(
                    f"Threshold condition is in alert: "
                    f"metric='{metric_name}', value={metric_value}, "
                    f"threshold={threshold_value}, operator='{op_str}', "
                    f"condition_true={condition_true}"
                )
            threshold_scores.append(threshold_score)

        logger.debug(
            f"function flx_check_dynamic_thresholds, Checking threshold '{threshold_key}' on metric '{metric_name}': value={metric_value}, threshold={threshold_value}, operator='{op_str}', condition_true={condition_true}, match={match}, should_alert={should_alert}"
        )

    return threshold_alert, threshold_messages, threshold_scores


def fqm_thresholds_lookup(object_value, key_value, record, thresholds_collection_dict):
    """
    Updates record with dynamic thresholds information (field dynamic_thresholds) if key_value matches the object_id value in thresholds_collection_dict records.

    ex:

    {
        "c6745c4d9190e2f18bd83e4448a0584da54a832fa57dfd838b58940c8fced934": {
            "metric_name": "soar.mem_used_pct",
            "value": 80,
            "operator": ">",
            "condition_true": True,
            "mtime": 1747012850.5604594,
            "comment": "No comment for update.",
            "object_id": "199fc4f889ff4946181bb00f56aad44c7580dd87691de699e1c0d2fc851a1ec5",
            "_user": "nobody",
            "_key": "c6745c4d9190e2f18bd83e4448a0584da54a832fa57dfd838b58940c8fced934"
        }
    }


    """

    dynamic_thresholds = {}

    if thresholds_collection_dict:
        for key, value in thresholds_collection_dict.items():
            object_id = value.get("object_id", None)
            if object_id and object_id == key_value:
                # add the dynamic threshold record to the dynamic_thresholds dictionary
                dynamic_thresholds[key] = thresholds_collection_dict[key]

    # add the dynamic_thresholds dictionary to the record
    record["dynamic_thresholds"] = dynamic_thresholds

    return True


def fqm_check_dynamic_thresholds(logger, dynamic_thresholds, metrics_record):
    """
    Checks if the dynamic thresholds are breached and updates the record accordingly.

    Returns:
        - threshold_alert: 1 if one or more thresholds are in alert, 0 otherwise
        - threshold_messages: list of messages indicating which thresholds are in alert
        - threshold_scores: list of scores for breached thresholds (defaults to 100 if not specified)
    """
    ops = {
        ">": operator.gt,
        "<": operator.lt,
        "==": operator.eq,
        "!=": operator.ne,
        ">=": operator.ge,
        "<=": operator.le,
    }

    if not isinstance(metrics_record, dict):
        try:
            metrics_record = json.loads(metrics_record)
        except Exception as e:
            logger.error(
                f'metrics_record="{metrics_record}" value can not be converted to dict, exception="{e}"'
            )
            return 0, [], []

    logger.debug(
        f'starting function fqm_check_dynamic_thresholds, dynamic_thresholds="{json.dumps(dynamic_thresholds, indent=2)}", metrics_record="{json.dumps(metrics_record, indent=2)}"'
    )

    threshold_alert = 0
    threshold_messages = []
    threshold_scores = []

    for threshold_key, threshold in dynamic_thresholds.items():

        logger.debug(
            f'checking threshold_key="{threshold_key}", threshold="{json.dumps(threshold, indent=2)}"'
        )

        metric_name = threshold.get("metric_name")
        op_str = threshold.get("operator")
        condition_true = strict_interpret_boolean(threshold.get("condition_true"))
        # Get threshold score, default to 100 if not present (for backward compatibility with existing records)
        try:
            threshold_score = int(threshold.get("score", 100))
        except (TypeError, ValueError):
            threshold_score = 100

        if metric_name not in metrics_record:
            logger.debug(
                f'function fqm_check_dynamic_thresholds, metric_name="{metric_name}" not found in metrics_record="{json.dumps(metrics_record, indent=2)}", skipping threshold (metric may not be available for this tracker)'
            )
            continue

        if op_str not in ops:
            logger.error(
                f'functionfqm_check_dynamic_thresholds, op_str="{op_str}" not found in ops'
            )
            continue

        try:
            threshold_value = float(threshold.get("value"))
        except (TypeError, ValueError):
            logger.error(
                f'function fqm_check_dynamic_thresholds threshold_value value can not be converted to float, skipping threshold_key="{threshold_key}"'
            )
            continue

        try:
            metric_value = float(metrics_record.get(metric_name, 0))
        except (TypeError, ValueError):
            logger.error(
                f'function fqm_check_dynamic_thresholds metric_value value can not be converted to float, skipping threshold_key="{threshold_key}"'
            )
            continue  # Skip if value can't be converted to float

        op_func = ops[op_str]
        match = op_func(metric_value, threshold_value)

        # Fixed logic: alert if the expected condition is NOT matched
        should_alert = (condition_true and not match) or (not condition_true and match)

        if should_alert:
            threshold_alert = 1
            threshold_messages.append(
                f"Threshold condition is in alert: "
                f"metric='{metric_name}', value={metric_value}, "
                f"threshold={threshold_value}, operator='{op_str}', "
                f"condition_true={condition_true}"
            )
            threshold_scores.append(threshold_score)

        logger.debug(
            f"function fqm_check_dynamic_thresholds, Checking threshold '{threshold_key}' on metric '{metric_name}': value={metric_value}, threshold={threshold_value}, operator='{op_str}', condition_true={condition_true}, match={match}, should_alert={should_alert}"
        )

    return threshold_alert, threshold_messages, threshold_scores


def wlk_thresholds_lookup(object_value, key_value, record, thresholds_collection_dict):
    """
    Updates record with dynamic thresholds information (field dynamic_thresholds) if key_value matches the object_id value in thresholds_collection_dict records.
    WLK thresholds follow the same pattern as FLX/FQM thresholds.

    If no entity-specific thresholds are found (object_id == key_value), falls back to
    tenant-level default thresholds (object_id == "default").
    """

    dynamic_thresholds = {}
    default_thresholds = {}

    if thresholds_collection_dict:
        for key, value in thresholds_collection_dict.items():
            object_id = value.get("object_id", None)
            if object_id and object_id == key_value:
                # Entity-specific threshold
                dynamic_thresholds[key] = thresholds_collection_dict[key]
            elif object_id and object_id == "default":
                # Tenant-level default threshold (used as fallback)
                default_thresholds[key] = thresholds_collection_dict[key]

    # If no entity-specific thresholds found, use tenant defaults
    if not dynamic_thresholds and default_thresholds:
        dynamic_thresholds = default_thresholds

    # add the dynamic_thresholds dictionary to the record
    record["dynamic_thresholds"] = dynamic_thresholds

    return True


def wlk_check_dynamic_thresholds(logger, dynamic_thresholds, entity_record):
    """
    Checks if the WLK dynamic thresholds are breached.
    Unlike FLX/FQM, WLK metrics are top-level fields on the entity record
    (e.g. skipped_pct_last_24h, count_errors_last_60m) rather than nested in a metrics JSON dict.

    Returns:
        - threshold_alert: 1 if one or more thresholds are in alert, 0 otherwise
        - threshold_messages: list of messages indicating which thresholds are in alert
        - threshold_scores: list of scores for breached thresholds (defaults to 100 if not specified)
    """
    ops = {
        ">": operator.gt,
        "<": operator.lt,
        "==": operator.eq,
        "!=": operator.ne,
        ">=": operator.ge,
        "<=": operator.le,
    }

    if not isinstance(entity_record, dict):
        logger.error(
            f'wlk_check_dynamic_thresholds: entity_record is not a dict'
        )
        return 0, [], []

    logger.debug(
        f'starting function wlk_check_dynamic_thresholds, dynamic_thresholds="{json.dumps(dynamic_thresholds, indent=2)}"'
    )

    threshold_alert = 0
    threshold_messages = []
    threshold_scores = []

    for threshold_key, threshold in dynamic_thresholds.items():

        logger.debug(
            f'checking threshold_key="{threshold_key}", threshold="{json.dumps(threshold, indent=2)}"'
        )

        metric_name = threshold.get("metric_name")
        op_str = threshold.get("operator")
        condition_true = strict_interpret_boolean(threshold.get("condition_true"))
        # Get threshold score, default to 100 if not present
        try:
            threshold_score = int(threshold.get("score", 100))
        except (TypeError, ValueError):
            threshold_score = 100

        if metric_name not in entity_record:
            logger.debug(
                f'function wlk_check_dynamic_thresholds, metric_name="{metric_name}" not found in entity_record, skipping threshold'
            )
            continue

        if op_str not in ops:
            logger.error(
                f'function wlk_check_dynamic_thresholds, op_str="{op_str}" not found in ops'
            )
            continue

        try:
            threshold_value = float(threshold.get("value"))
        except (TypeError, ValueError):
            logger.error(
                f'function wlk_check_dynamic_thresholds threshold_value value can not be converted to float, skipping threshold_key="{threshold_key}"'
            )
            continue

        # WLK metrics are top-level entity record fields (e.g. count_skipped_last_4h, count_errors_last_60m)
        # that may be absent, empty, or non-numeric depending on search activity — this is expected,
        # so we silently skip the threshold check rather than logging an error or warning.
        try:
            raw_metric_value = entity_record.get(metric_name, 0)
            if raw_metric_value is None or raw_metric_value == "":
                continue
            metric_value = float(raw_metric_value)
        except (TypeError, ValueError):
            continue

        op_func = ops[op_str]
        match = op_func(metric_value, threshold_value)

        # Alert if the expected condition is NOT matched
        should_alert = (condition_true and not match) or (not condition_true and match)

        if should_alert:
            threshold_alert = 1
            threshold_messages.append(
                f"Threshold condition is in alert: "
                f"metric='{metric_name}', value={metric_value}, "
                f"threshold={threshold_value}, operator='{op_str}', "
                f"condition_true={condition_true}"
            )
            threshold_scores.append(threshold_score)

        logger.debug(
            f"function wlk_check_dynamic_thresholds, Checking threshold '{threshold_key}' on metric '{metric_name}': value={metric_value}, threshold={threshold_value}, operator='{op_str}', condition_true={condition_true}, match={match}, should_alert={should_alert}"
        )

    return threshold_alert, threshold_messages, threshold_scores


def calculate_score(service, tenant_id, component, tenant_trackme_metric_idx="trackme_metrics"):
    """
    Calculates the score for each object_id based on outlier scoring metrics from the past 24 hours.

    :param service: The Splunk service object.
    :param tenant_id: The tenant ID to query scores for.
    :param component: The component to query scores for.
    :return: A dictionary keyed by object_id, where each value contains:
        - score: The sum of scores for the object_id (float)
        - score_outliers: The sum of scores for the object_id that are outliers (float)
        - object: The object name (string)
        - score_source: A list of scoring sources (list of strings)
    """

    if not service:
        get_effective_logger().error('function calculate_score, service parameter is None or empty')
        return {}

    if not tenant_id:
        get_effective_logger().error('function calculate_score, tenant_id parameter is None or empty')
        return {}

    # Build the search query
    search_query = remove_leading_spaces(
        f"""
        | mstats sum(trackme.scoring.score) as score where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="{component}" by object_id, object, score_source
        | eval score_outliers=if(match(score_source,"^(false_positive_outlier$|lowerbound_outlier|upperbound_outlier)"),score,null())
        | stats sum(score) as score, sum(score_outliers) as score_outliers, values(score_source) as score_source by object_id, object
        """
    )

    # Search parameters for past 24 hours
    kwargs_search = {
        "earliest_time": "-24h",
        "latest_time": "now",
        "preview": "false",
        "output_mode": "json",
        "count": 0,
    }

    # Initialize the result dictionary
    scores_dict = {}

    start_time = time.time()

    try:

        get_effective_logger().debug(
            f'function calculate_score, tenant_id="{tenant_id}", component="{component}", search_query="{search_query}", kwargs_search="{json.dumps(kwargs_search, indent=2)}"'
        )

        # Execute the search
        reader = run_splunk_search(
            service,
            search_query,
            kwargs_search,
            24,  # max_retries
            5,   # sleep_time
        )

        # Process results
        for item in reader:
            if isinstance(item, dict):
                object_id = item.get("object_id")
                if object_id:
                    # Get score, defaulting to 0 if not present or invalid
                    try:
                        score = float(item.get("score", 0))
                    except (TypeError, ValueError):
                        score = 0.0

                    # Get score_outliers, defaulting to 0 if not present or invalid
                    try:
                        score_outliers = float(item.get("score_outliers", 0))
                    except (TypeError, ValueError):
                        score_outliers = 0.0

                    # Get object name
                    object_name = item.get("object", "")

                    # Get score_source - it may be a string or a list
                    score_source_raw = item.get("score_source")
                    if isinstance(score_source_raw, list):
                        score_source_list = score_source_raw
                    elif isinstance(score_source_raw, str):
                        score_source_list = [score_source_raw]
                    else:
                        score_source_list = []

                    # Store in dictionary
                    scores_dict[object_id] = {
                        "score": score,
                        "score_outliers": score_outliers,
                        "object": object_name,
                        "score_source": score_source_list,
                    }

        runtime = round(time.time() - start_time, 3)
        get_effective_logger().debug(
            f'function calculate_score, tenant_id="{tenant_id}", '
            f'no_objects="{len(scores_dict)}", run_time="{runtime}"'
        )

    except Exception as e:
        get_effective_logger().error(
            f'function calculate_score, tenant_id="{tenant_id}", '
            f'failed with exception="{str(e)}"'
        )
        # Return empty dict on error
        return {}

    # Merge score cache records for immediate false_positive/manual_score visibility
    # Cache entries are only used when mstats has not yet indexed the corresponding score source
    try:
        cache_records = read_score_cache(service, tenant_id, component)
        if cache_records:
            # Group cache entries by (object_id, score_source)
            from collections import defaultdict
            cache_by_obj = defaultdict(lambda: defaultdict(float))
            cache_objects = {}

            for rec in cache_records:
                oid = rec.get("object_id")
                src = rec.get("score_source", "")
                if oid and src:
                    try:
                        cache_by_obj[oid][src] += float(rec.get("score", 0))
                    except (TypeError, ValueError):
                        pass
                    if oid not in cache_objects:
                        cache_objects[oid] = rec.get("object", "")

            # Outlier source pattern — must match the mstats eval in the search above
            import re
            _outlier_source_re = re.compile(r"^(false_positive_outlier$|lowerbound_outlier|upperbound_outlier)")

            # Merge: for each object_id, add cache scores only for sources not yet in mstats
            for oid, sources in cache_by_obj.items():
                existing = scores_dict.get(oid, {})
                existing_sources = existing.get("score_source", [])

                for src, cached_score in sources.items():
                    if src in existing_sources:
                        continue  # mstats already has this source, skip cache

                    is_outlier_source = bool(_outlier_source_re.match(src))

                    if oid in scores_dict:
                        scores_dict[oid]["score"] += cached_score
                        scores_dict[oid]["score_source"].append(src)
                        if is_outlier_source:
                            scores_dict[oid]["score_outliers"] += cached_score
                    else:
                        scores_dict[oid] = {
                            "score": cached_score,
                            "score_outliers": cached_score if is_outlier_source else 0.0,
                            "object": cache_objects.get(oid, ""),
                            "score_source": [src],
                        }

            get_effective_logger().debug(
                f'function calculate_score, tenant_id="{tenant_id}", '
                f'merged {len(cache_records)} score cache records'
            )

    except Exception as e:
        get_effective_logger().warning(
            f'function calculate_score, tenant_id="{tenant_id}", '
            f'failed to merge score cache, exception="{str(e)}"'
        )

    return scores_dict
