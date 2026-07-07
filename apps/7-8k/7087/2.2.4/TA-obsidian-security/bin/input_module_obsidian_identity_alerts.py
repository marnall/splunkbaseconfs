# encoding = utf-8

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import jwt
import obsidian_utils
import requests

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""

IDENTITY_ALERTS_FETCH_TYPE = "obsidian:identity_alerts"

# Constants
DEFAULT_DATE_RANGE_DAYS = 7


def canonicalize_aggregate_record(record: Dict[str, Any]) -> str:
    """
    Canonicalize an aggregate record for stable hashing.
    
    Args:
        record: Dict from alerts_grouped_aggregate response
        
    Returns:
        Canonical JSON string
    """
    # Normalize email
    email = (record.get("email", "") or "").lower().strip()
    
    # Sort and dedupe names (case-insensitive)
    names = sorted(set(
        n.lower().strip() 
        for n in record.get("names", []) 
        if n and isinstance(n, str)
    ))
    
    # Sort and dedupe services (uppercase)
    services = sorted(set(
        s.upper().strip() 
        for s in record.get("services", []) 
        if s and isinstance(s, str)
    ))
    
    # Build canonical dict with sorted keys
    canonical = {
        "email": email,
        "alertCount": int(record.get("alertCount", 0)),
        "confidenceScore": str(record.get("confidenceScore", "")).upper(),
        "names": names,
        "services": services,
        "hasMaliciousAlert": bool(record.get("hasMaliciousAlert", False))
    }
    
    # Stable JSON: sorted keys, no whitespace
    return json.dumps(canonical, sort_keys=True, separators=(',', ':'))


def compute_hash(canonical_json: str) -> str:
    """
    Compute SHA-256 hash of canonical JSON.
    
    Args:
        canonical_json: Canonical JSON string
        
    Returns:
        Hex digest (lowercase)
    """
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


def compute_email_diff(
    aggregate_records: List[Dict[str, Any]],
    existing_checkpoint: Dict[str, Dict[str, Any]]
) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """
    Compute diff between aggregate response and checkpoint.
    
    Args:
        aggregate_records: List of records from alerts_grouped_aggregate
        existing_checkpoint: Dict[email, {hash, updatedAt}]
        
    Returns:
        Tuple of (new_emails, changed_emails, unchanged_emails, removed_emails)
    """
    new_emails = set()
    changed_emails = set()
    unchanged_emails = set()
    
    checkpoint_emails = set(existing_checkpoint.keys())
    aggregate_emails = set()
    
    for record in aggregate_records:
        email = (record.get("email", "") or "").lower().strip()
        if not email:
            continue
        
        aggregate_emails.add(email)
        canonical = canonicalize_aggregate_record(record)
        new_hash = compute_hash(canonical)
        
        if email not in existing_checkpoint:
            # New email
            new_emails.add(email)
        else:
            old_hash = existing_checkpoint[email].get("hash", "")
            if old_hash != new_hash:
                # Hash changed
                changed_emails.add(email)
            else:
                # Hash unchanged
                unchanged_emails.add(email)
    
    # Emails in checkpoint but not in aggregate
    removed_emails = checkpoint_emails - aggregate_emails
    
    return new_emails, changed_emails, unchanged_emails, removed_emails


def build_new_checkpoint(
    aggregate_records: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Build new checkpoint dict from aggregate records.
    
    Args:
        aggregate_records: List of records from alerts_grouped_aggregate
        
    Returns:
        Checkpoint dict: {email: {hash, updatedAt}}
    """
    checkpoint = {}
    current_time = int(datetime.now(timezone.utc).timestamp())
    
    for record in aggregate_records:
        email = (record.get("email", "") or "").lower().strip()
        if not email:
            continue
        
        canonical = canonicalize_aggregate_record(record)
        hash_val = compute_hash(canonical)
        
        checkpoint[email] = {
            "hash": hash_val,
            "updatedAt": current_time
        }
    
    return checkpoint


def format_datetime_for_api(dt: datetime) -> str:
    """
    Format datetime in the required API format: YYYY-MM-DDTHH:MM:SS.mmmZ
    
    Args:
        dt: Datetime object (should be timezone-aware UTC)
        
    Returns:
        Formatted datetime string (e.g., "2026-01-15T07:59:59.999Z")
    """
    # Ensure UTC timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    
    # Format: YYYY-MM-DDTHH:MM:SS.mmmZ
    # Use strftime for date/time, then add milliseconds manually
    date_time_str = dt.strftime("%Y-%m-%dT%H:%M:%S")
    milliseconds = dt.microsecond // 1000  # Convert microseconds to milliseconds
    return f"{date_time_str}.{milliseconds:03d}Z"


def build_aggregate_payload(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    date_range: int,
    min_confidence_score: str,
    show_resolved_alerts: bool
) -> Dict[str, Any]:
    """
    Build payload for alerts_grouped_aggregate endpoint.
    
    Args:
        start_date: Optional start date
        end_date: Optional end date
        date_range: Days to look back if dates not provided
        min_confidence_score: Confidence threshold (if "MINIMAL", field is omitted)
        show_resolved_alerts: Whether to include resolved alerts
        
    Returns:
        Payload dict
    """
    payload = {
        "show_resolved_alerts": bool(show_resolved_alerts)
    }
    
    # Only include min_confidence_score if it's not "MINIMAL"
    confidence_upper = min_confidence_score.upper()
    if confidence_upper != "MINIMAL":
        payload["min_confidence_score"] = confidence_upper
    
    if start_date and end_date:
        # Use explicit dates
        payload["start_date"] = format_datetime_for_api(start_date)
        payload["end_date"] = format_datetime_for_api(end_date)
    else:
        # Use date_range_days
        payload["date_range_days"] = int(date_range)
        if end_date:
            payload["end_date"] = format_datetime_for_api(end_date)
    
    return payload


def build_grouped_payload(
    email: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    date_range: int,
    min_confidence_score: str,
    show_resolved_alerts: bool,
    correlation_id: str = ""
) -> Dict[str, Any]:
    """
    Build payload for alerts_grouped endpoint.
    
    Args:
        email: Email address
        start_date: Optional start date
        end_date: Optional end date
        date_range: Days to look back if dates not provided
        min_confidence_score: Confidence threshold (if "MINIMAL", field is omitted)
        show_resolved_alerts: Whether to include resolved alerts
        correlation_id: Optional correlation ID
        
    Returns:
        Payload dict
    """
    payload = {
        "email": email,
        "show_resolved_alerts": bool(show_resolved_alerts),
        "correlationId": correlation_id or ""
    }
    
    # Only include min_confidence_score if it's not "MINIMAL"
    confidence_upper = min_confidence_score.upper()
    if confidence_upper != "MINIMAL":
        payload["min_confidence_score"] = confidence_upper
    
    if start_date and end_date:
        # Use explicit dates
        payload["start_date"] = format_datetime_for_api(start_date)
        payload["end_date"] = format_datetime_for_api(end_date)
    else:
        # Use date_range_days
        payload["date_range_days"] = int(date_range)
        if end_date:
            payload["end_date"] = format_datetime_for_api(end_date)
    
    return payload


def find_group_for_email(
    grouped_data: List[Dict[str, Any]],
    email: str
) -> Optional[Dict[str, Any]]:
    """
    Find the group object for a specific email in grouped response.
    
    Args:
        grouped_data: Response from alerts_grouped endpoint
        email: Email address to find
        
    Returns:
        Group dict or None if not found
    """
    expected_email = email.lower().strip()
    
    for group in grouped_data:
        group_email = (group.get("email", "") or "").lower().strip()
        if group_email == expected_email:
            return group
    
    return None


def build_splunk_events_from_group(
    helper,
    group: Dict[str, Any],
    subdomain: str
) -> List[Any]:
    """
    Build Splunk events from grouped identity alerts response.
    Creates a parent event (obsidian:identity_alerts) without the identityAlerts array,
    and individual child events (obsidian:identity_alert) for each alert with UUID correlation.
    
    Args:
        helper: Splunk helper object
        group: Group dict from alerts_grouped response
        subdomain: Tenant subdomain
        
    Returns:
        List of Splunk event objects [parent_event, child_event_1, child_event_2, ...]
    """
    # Extract identityAlerts array
    identity_alerts = group.get("identityAlerts", [])
    total_alert_count = len(identity_alerts)
    
    # Generate parent event UUID for correlation
    parent_event_uuid = str(uuid.uuid4())
    
    # Determine event time from the first alert's eventTime, or use current time
    event_time = None
    if identity_alerts:
        # Use the most recent eventTime from alerts
        event_times = []
        for alert in identity_alerts:
            event_time_str = (
                alert.get("eventTime")
                or alert.get("alertGenerationTime")
                or alert.get("lastUpdated")
            )
            if event_time_str:
                event_times.append(event_time_str)
        
        if event_times:
            # Sort and use the most recent
            try:
                event_times.sort(reverse=True)
                event_time = obsidian_utils.get_event_time(event_times[0])
            except Exception:
                pass
    
    # If no event time found, use current time
    if event_time is None:
        event_time = datetime.now(timezone.utc).timestamp()
    
    confidence_score = group.get("confidenceScore", "MINIMAL")
    if confidence_score.upper() == "NONE":
        confidence_score = "MINIMAL"
    # Build parent event data WITHOUT identityAlerts array
    parent_event_data = {
        # Critical metadata fields
        "event_uuid": parent_event_uuid,
        "email": group.get("email", ""),
        "obsidian_tenant": subdomain,
        "confidenceScore": confidence_score,
        "services": group.get("services", []),
        "names": group.get("names", []),
        "identityAlerts_count": total_alert_count,
    }
    
    # Create parent event with sourcetype obsidian:identity_alerts
    parent_event = helper.new_event(
        time=event_time,
        source=helper.get_input_type(),
        index=helper.get_output_index(),
        sourcetype="obsidian:identity_alerts",
        data=json.dumps(parent_event_data)
    )
    
    # List to store all events (parent + children)
    events = [parent_event]
    
    # Create child events for each identity alert
    for alert in identity_alerts:
        # Generate child event UUID
        child_event_uuid = str(uuid.uuid4())
        
        # Determine child event time
        child_event_time = None
        child_event_time_str = (
            alert.get("eventTime")
            or alert.get("alertGenerationTime")
            or alert.get("lastUpdated")
        )
        if child_event_time_str:
            try:
                child_event_time = obsidian_utils.get_event_time(child_event_time_str)
            except Exception:
                pass
        
        # Fallback to parent event time if child time not found
        if child_event_time is None:
            child_event_time = event_time
        
        # Build child event data with correlation UUIDs
        child_event_data = {
            "event_uuid": child_event_uuid,
            "parent_event_uuid": parent_event_uuid,
            "email": group.get("email", ""),
            "obsidian_tenant": subdomain,
        }
        
        # Add all alert fields to child event
        child_event_data.update(alert)
        
        # Create child event with sourcetype obsidian:identity_alert (singular)
        child_event = helper.new_event(
            time=child_event_time,
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype="obsidian:identity_alert",
            data=json.dumps(child_event_data)
        )
        
        events.append(child_event)
    
    helper.log_debug(
        f'msg="Created parent and child events", email={group.get("email", "unknown")}, '
        f'parent_uuid={parent_event_uuid}, total_child_events={total_alert_count}'
    )
    
    return events


def fetch_and_index_grouped_alerts(
    helper,
    ew,
    email: str,
    headers: dict,
    proxy_setting: Optional[str],
    api_url: str,
    filter_params: Dict[str, Any]
) -> Tuple[bool, int]:
    """
    Fetch and index grouped alerts for a single email.
    Indexes the entire grouped response as a single event.
    
    Args:
        helper: Splunk helper object
        ew: Event writer object
        email: Email address
        headers: API headers
        proxy_setting: Optional proxy setting
        api_url: API base URL
        filter_params: Filter parameters dict
        
    Returns:
        Tuple of (success: bool, event_count: int) where event_count is 1 if indexed, 0 otherwise
    """
    try:
        # Build grouped payload
        grouped_payload = build_grouped_payload(
            email=email,
            start_date=filter_params.get("start_date"),
            end_date=filter_params.get("end_date"),
            date_range=filter_params.get("date_range"),
            min_confidence_score=filter_params.get("min_confidence_score"),
            show_resolved_alerts=filter_params.get("show_resolved_alerts"),
            correlation_id=filter_params.get("correlation_id", "")
        )
        
        grouped_url = api_url.replace("gql", "intel/identity/alerts_grouped")
        
        # Fetch grouped alerts
        try:
            grouped_response = obsidian_utils.make_request(
                helper, grouped_payload, headers, proxy_setting, grouped_url
            )
            if grouped_response.status_code != 200:
                helper.log_error(
                    f'msg="Failed to fetch grouped alerts", email={email}, '
                    f'status_code={grouped_response.status_code}, '
                    f'response={grouped_response.text[:200]}'
                )
                return False, 0
        except Exception as e:
            helper.log_error(
                f'msg="Failed to fetch grouped alerts", email={email}, error={str(e)}'
            )
            return False, 0
        
        # Parse response
        grouped_data = grouped_response.json()
        if not grouped_data:
            helper.log_warning(
                f'msg="No grouped alerts found", email={email}'
            )
            return True, 0  # Success but no data
        
        # Find the group for this email
        group = find_group_for_email(grouped_data, email)
        if not group:
            helper.log_warning(
                f'msg="No group found for email in response", email={email}'
            )
            return True, 0  # Success but no matching group
        
        # Index the group as parent event + child events
        subdomain = filter_params.get("subdomain", "")
        try:
            events = build_splunk_events_from_group(
                helper, group, subdomain
            )
            
            # Write all events (parent + children)
            for event in events:
                ew.write_event(event)
            
            # Count alerts in the group for logging
            alert_count = len(group.get("identityAlerts", []))
            total_events_indexed = len(events)
            helper.log_debug(
                f'msg="Indexed grouped alerts as parent-child events", email={email}, '
                f'alert_count={alert_count}, total_events_indexed={total_events_indexed}'
            )
            
            return True, total_events_indexed  # Parent event + child events
            
        except Exception as e:
            helper.log_error(
                f'msg="Failed to index grouped alerts", email={email}, error={str(e)}'
            )
            return False, 0
        
    except Exception as e:
        helper.log_error(
            f'msg="Failed to process email", email={email}, error={str(e)}',
            exc_info=True
        )
        return False, 0


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    try:
        interval = int(definition.parameters.get("interval") or "180")
    except (ValueError, TypeError) as e:
        raise Exception(
            f"Invalid interval value: {definition.parameters.get('interval')} - {str(e)}"
        )
    if interval != -1 and interval < 180:
        raise Exception(
            "Interval must be greater or equal to 180, or -1 for one-time execution"
        )
    
    # Obtain the api_token
    input_name = definition.metadata.get("name")
    session_key = definition.metadata.get("session_key")
    opt_obsidian_api_token = obsidian_utils.lookup_api_token(
        "obsidian_identity_alerts", input_name, session_key
    )
    
    # Validate subdomain
    opt_subdomain = definition.parameters.get("subdomain")
    if (
        opt_subdomain.find(":") > -1
        or opt_subdomain.find("/") > -1
        or obsidian_utils.is_full_domain(opt_subdomain)
    ):
        raise Exception(
            "Subdomain: unexpected input. Please input only subdomain, not the full url."
        )
    
    # Validate token matches subdomain
    token_payload = jwt.decode(
        opt_obsidian_api_token, options={"verify_signature": False}
    )
    token_subdomain_name = token_payload.get("aud")
    if token_subdomain_name:
        if token_subdomain_name.lower() != opt_subdomain.lower():
            raise Exception(
                f"The token is not valid for the given subdomain. "
                f"The subdomain name is {token_subdomain_name}, but your input subdomain name is {opt_subdomain}, please check!"
            )
    else:
        helper.log_info(
            f'msg="The subdomain name in the token is not able to be validated. '
            f'The subdomain name in token is: {token_subdomain_name}"'
        )
    
    # Validate confidence score
    confidence = definition.parameters.get("confidence") or "MEDIUM"
    valid_confidence = ["MINIMAL", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    if confidence.upper() not in valid_confidence:
        raise Exception(
            f"Invalid confidence score: {confidence}. Must be one of {valid_confidence}"
        )
    
    # Validate date_range
    try:
        date_range = int(definition.parameters.get("date_range") or str(DEFAULT_DATE_RANGE_DAYS))
    except (ValueError, TypeError) as e:
        raise Exception(
            f"Invalid date_range value: {definition.parameters.get('date_range')} - {str(e)}"
        )
    if date_range < 1:
        raise Exception("date_range must be greater than 0")
    if date_range > 730:
        raise Exception("date_range must be less than or equal to 730")
    
    # Validate show_resolved_alerts
    show_resolved = definition.parameters.get("show_resolved_alerts")
    if show_resolved is not None and not isinstance(show_resolved, bool):
        try:
            show_resolved = str(show_resolved).lower() in ("true", "1", "yes")
        except Exception:
            raise Exception("show_resolved_alerts must be a boolean value")
    
    opt_proxy_setting = definition.parameters.get("proxy_setting") or None
    obsidian_api_url = (
        definition.parameters.get("obsidian_api_url") or "https://api.obsec.io"
    )
    
    # Test API connection
    try:
        headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)
        # Use a simple test endpoint or version check
        test_payload = {"query": "query { __typename }"}
        helper.log_debug(
            f'msg="Validating identity alerts input through Obsidian API", '
            f'org={opt_subdomain}, api_url={obsidian_api_url}, proxy={opt_proxy_setting}'
        )
        response = obsidian_utils.make_request(
            helper, test_payload, headers, opt_proxy_setting, obsidian_api_url
        )
        response.raise_for_status()
        helper.log_debug(
            f'msg="Successfully connected to Obsidian API", '
            f'org={opt_subdomain}, api_url={obsidian_api_url}, proxy={opt_proxy_setting}'
        )
    except requests.HTTPError as e:
        helper.log_error(
            f'msg="HTTP Error: {e}", org={opt_subdomain}, '
            f'api_url={obsidian_api_url}, proxy={opt_proxy_setting}'
        )
        raise Exception(f"HTTP Error: {e}")


def collect_events(helper, ew):
    """Event collection logic"""
    # Set log level
    helper.set_log_level(helper.get_log_level())
    
    # Get configuration
    opt_subdomain = obsidian_utils.sanitize_subdomain(helper.get_arg("subdomain"))
    opt_obsidian_api_token = helper.get_arg("api_token")
    api_url = helper.get_arg("obsidian_api_url") or "https://api.obsec.io/v1/gql"
    min_confidence = (helper.get_arg("confidence") or "MEDIUM").upper()
    
    try:
        date_range = int(helper.get_arg("date_range") or str(DEFAULT_DATE_RANGE_DAYS))
    except (ValueError, TypeError) as e:
        helper.log_error(
            f"Invalid date_range value: {helper.get_arg('date_range')}, "
            f"using default {DEFAULT_DATE_RANGE_DAYS} - {str(e)}"
        )
        date_range = DEFAULT_DATE_RANGE_DAYS
    
    show_resolved_raw = helper.get_arg("show_resolved_alerts")
    if show_resolved_raw is not None:
        if isinstance(show_resolved_raw, bool):
            show_resolved = show_resolved_raw
        else:
            show_resolved = str(show_resolved_raw).lower() in ("true", "1", "yes")
    else:
        show_resolved = False
    
    proxy_setting = helper.get_arg("proxy_setting") or None
    
    # Build headers
    headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=date_range)
    
    # Load checkpoint
    checkpoint_key = f"{opt_subdomain}_identity_alert"
    existing_checkpoint = helper.get_check_point(checkpoint_key) or {}
    
    proxy_log_message = ""
    if proxy_setting:
        proxy_log_message = f" (proxy: {proxy_setting})"
    
    helper.log_info(
        f'msg="Starting identity alerts collection{proxy_log_message}", '
        f'org={opt_subdomain}, fetch_type={IDENTITY_ALERTS_FETCH_TYPE}, '
        f'confidence={min_confidence}, date_range={date_range}, '
        f'show_resolved={show_resolved}, obsidian_api_url={api_url}'
    )
    
    try:
        # Build aggregate payload
        aggregate_payload = build_aggregate_payload(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            min_confidence_score=min_confidence,
            show_resolved_alerts=show_resolved
        )
        
        aggregate_url = api_url.replace("gql", "intel/identity/alerts_grouped_aggregate")
        
        # Fetch aggregate
        helper.log_debug(
            f'msg="Fetching aggregate alerts", org={opt_subdomain}, '
            f'url={aggregate_url}, payload={json.dumps(aggregate_payload)}'
        )
        
        try:
            aggregate_response = obsidian_utils.make_request(
                helper, aggregate_payload, headers, proxy_setting, aggregate_url
            )
            if aggregate_response.status_code != 200:
                helper.log_error(
                    f'msg="Failed to fetch aggregate alerts", org={opt_subdomain}, '
                    f'status_code={aggregate_response.status_code}, '
                    f'response={aggregate_response.text[:200]}'
                )
                return
        except Exception as e:
            helper.log_error(
                f'msg="Failed to fetch aggregate alerts", org={opt_subdomain}, error={str(e)}'
            )
            return
        
        aggregate_records = aggregate_response.json()
        if not aggregate_records:
            helper.log_info(
                f'msg="No identity alerts found matching criteria", org={opt_subdomain}'
            )
            # Update checkpoint to empty
            helper.save_check_point(checkpoint_key, {})
            return
        
        helper.log_info(
            f'msg="Aggregate response received", org={opt_subdomain}, '
            f'email_count={len(aggregate_records)}'
        )
        
        # Compute diff
        new_emails, changed_emails, unchanged_emails, removed_emails = \
            compute_email_diff(aggregate_records, existing_checkpoint)
        
        helper.log_info(
            f'msg="Aggregate diff computed", org={opt_subdomain}, '
            f'new={len(new_emails)}, changed={len(changed_emails)}, '
            f'unchanged={len(unchanged_emails)}, removed={len(removed_emails)}'
        )
        
        # Process emails that need fetching
        emails_to_fetch = new_emails | changed_emails
        
        if not emails_to_fetch:
            helper.log_info(
                f'msg="No identity alerts need fetching, all unchanged", org={opt_subdomain}'
            )
            # Still update checkpoint (in case aggregate changed but hashes match)
            new_checkpoint = build_new_checkpoint(aggregate_records)
            helper.save_check_point(checkpoint_key, new_checkpoint)
            return
        
        # Filter parameters for grouped calls
        filter_params = {
            "start_date": start_date,
            "end_date": end_date,
            "date_range": date_range,
            "min_confidence_score": min_confidence,
            "show_resolved_alerts": show_resolved,
            "correlation_id": "",
            "subdomain": opt_subdomain
        }
        
        total_events = 0
        processed_count = 0
        failed_count = 0
        
        # Process each email
        for idx, email in enumerate(emails_to_fetch, 1):
            helper.log_debug(
                f'msg="Processing email", org={opt_subdomain}, '
                f'email={email}, progress={idx}/{len(emails_to_fetch)}'
            )
            
            success, event_count = fetch_and_index_grouped_alerts(
                helper, ew, email, headers, proxy_setting, api_url, filter_params
            )
            
            if success:
                processed_count += 1
                total_events += event_count
                helper.log_debug(
                    f'msg="Processed email", org={opt_subdomain}, '
                    f'email={email}, events={event_count}'
                )
            else:
                failed_count += 1
        
        # Update checkpoint
        new_checkpoint = build_new_checkpoint(aggregate_records)
        helper.save_check_point(checkpoint_key, new_checkpoint)
        
        helper.log_info(
            f'msg="Collection complete", org={opt_subdomain}, '
            f'emails_processed={processed_count}, events_indexed={total_events}, '
            f'failed={failed_count}, total_emails_in_aggregate={len(aggregate_records)}'
        )
        
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            f'msg="HTTP exception in collect_events", org={opt_subdomain}, '
            f'fetch_type={IDENTITY_ALERTS_FETCH_TYPE}, error={str(e)}'
        )
    except Exception as e:
        helper.log_error(
            f'msg="Exception in collect_events", org={opt_subdomain}, '
            f'fetch_type={IDENTITY_ALERTS_FETCH_TYPE}, error={str(e)}',
            exc_info=True
        )
