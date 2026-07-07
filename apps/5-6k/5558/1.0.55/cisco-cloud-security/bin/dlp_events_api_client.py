# encoding = utf-8
"""DLP Events API Client for Splunk App.

This module provides a REST API handler for fetching DLP events from Cisco DLP Reporting API.
Supports realTime, saasApi, and aiGuardrails event types.
"""
import sys
import json
import time
import re
import threading
import concurrent.futures
from datetime import datetime, timedelta
from os.path import dirname, abspath

sys.path.append(dirname(abspath(__file__)))

_identity_cache = {}
_identity_cache_lock = threading.Lock()
IDENTITY_CACHE_TTL = 300

from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from exceptions import ReportingAPIClientException
from exceptions import DLPAPIException
from enums import DLPReportingAPIEndpoints
from reporting_api_client import ReportingAPIClient
from global_org_client import GlobalOrgClient


_NUMERIC_ONLY_PATTERN = re.compile(r'^\d+$')
_URL_DOMAIN_PATTERN = re.compile(
    r'^(https?://)?'  # Optional protocol
    r'([a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'  # Domain (word.tld)
    r'(:\d+)?'  # Optional port
    r'(/.*)?$'  # Optional path
    r'|'  # OR
    r'^(https?://)?(\d{1,3}\.){3}\d{1,3}(:\d+)?(/.*)?$',  # IP address
    re.IGNORECASE
)


# ============================================================================
# Filter Validator Classes - Each class handles validation for a specific field
# ============================================================================

class SeverityFilter:
    """Validator for severity filter field."""
    valid_values = frozenset(["critical", "warning", "info", "alert"])
    
    @classmethod
    def validate(cls, value):
        if value.strip().lower() not in cls.valid_values:
            return {
                "valid": False,
                "message": f"Invalid Severity. Valid values: {', '.join(cls.valid_values)}"
            }
        return {"valid": True}


class ActionFilter:
    """Validator for action filter field."""
    valid_values = frozenset(["block", "allow", "audit", "quarantine", "encrypt", "monitor", "notify"])
    
    @classmethod
    def validate(cls, value):
        if value.strip().lower() not in cls.valid_values:
            return {
                "valid": False,
                "message": f"Invalid Action. Valid values: {', '.join(cls.valid_values)}"
            }
        return {"valid": True}


class EventActorFilter:
    """Validator for eventActor filter field."""
    
    @classmethod
    def validate(cls, value):
        if not value.strip():
            return {
                "valid": False,
                "message": "Event Actor cannot be empty"
            }
        return {"valid": True}


class FileNameFilter:
    """Validator for fileName filter field."""
    
    @classmethod
    def validate(cls, value):
        trimmed = value.strip()
        if _NUMERIC_ONLY_PATTERN.match(trimmed):
            return {
                "valid": False,
                "message": "Invalid File Name. File name should contain letters or file extension"
            }
        return {"valid": True}


class DestinationFilter:
    """Validator for destination filter field."""
    
    @classmethod
    def validate(cls, value):
        trimmed = value.strip()
        if not _URL_DOMAIN_PATTERN.match(trimmed):
            return {
                "valid": False,
                "message": "Invalid Destination. Enter a valid URL or domain (e.g., http://example.com or example.com)"
            }
        return {"valid": True}


class RuleFilter:
    """Validator for rule filter field."""
    
    @classmethod
    def validate(cls, value):
        trimmed = value.strip()
        if _NUMERIC_ONLY_PATTERN.match(trimmed):
            return {
                "valid": False,
                "message": "Invalid Rule. Rule name should contain letters"
            }
        return {"valid": True}


class DetectedFilter:
    """Validator for detected (date) filter field."""
    
    @classmethod
    def validate(cls, value):
        trimmed = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                datetime.strptime(trimmed, fmt)
                return {"valid": True}
            except ValueError:
                continue
        return {
            "valid": False,
            "message": "Invalid Detected format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
        }


class EventTypeFilter:
    """Validator for eventType field."""
    valid_values = frozenset(["all", "realtime", "saasapi", "aiguardrails"])

    @classmethod
    def validate(cls, value):
        if value.strip().lower() not in cls.valid_values:
            return {
                "valid": False,
                "message": f"Invalid event type: {value}. Valid types are: all, realTime, saasApi, aiGuardrails"
            }
        return {"valid": True}


FILTER_VALIDATORS = {
    "severity": SeverityFilter,
    "action": ActionFilter,
    "eventActor": EventActorFilter,
    "fileName": FileNameFilter,
    "destination": DestinationFilter,
    "rule": RuleFilter,
    "detected": DetectedFilter,
    "eventType": EventTypeFilter
}

_API_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'
}

_EVENT_TYPE_MAP = {
    "all": "all",
    "realtime": "realTime",
    "saasapi": "saasApi",
    "aiguardrails": "aiGuardrails"
}

_SEARCH_FIELD_MAP = {
    "detected": "detected",
    "fileName": "fileName",
    "destination": "destinationUrl",
    "rule": "ruleName",
    "eventActor": "eventActor"
}

_ENDPOINT_MAP = {
    "realTime": DLPReportingAPIEndpoints.REALTIME_EVENTS.value,
    "saasApi": DLPReportingAPIEndpoints.SAAS_API_EVENTS.value,
    "aiGuardrails": DLPReportingAPIEndpoints.AI_GUARDRAILS_EVENTS.value
}


def validate_filter(field, value):
    """Validate a filter field using its corresponding validator class.

    Args:
        field: The filter field name (severity, action, eventActor, etc.)
        value: The filter value (guaranteed non-empty by caller)

    Returns:
        dict: {"valid": True} or {"valid": False, "message": "error message"}
    """
    validator = FILTER_VALIDATORS.get(field)
    if validator:
        return validator.validate(value)

    return {
        "valid": False,
        "message": f"Unknown filter field: {field}. Valid fields: {', '.join(FILTER_VALIDATORS.keys())}"
    }


def validate_all_filters(filters):
    """Validate all provided filters (only non-empty filters should be passed).

    Args:
        filters: Dictionary of filter field -> value (pre-filtered, no empty values)

    Returns:
        dict: {"valid": True} or {"valid": False, "field": "...", "message": "error message"}
    """
    for field, value in filters.items():
        result = validate_filter(field, value)
        if not result.get("valid"):
            result["field"] = field
            return result
    return {"valid": True}


class DLPEventsAPIClient(PersistentServerConnectionApplication):
    """REST API handler for DLP events."""

    def __init__(self, command_line, command_arg):
        """Initialize the DLP Events API Client."""
        PersistentServerConnectionApplication.__init__(self)
        self.reporting_api_client_inst = None
        self.session_token = None
        self.global_org_client = None

    def handle(self, in_string):
        """Main entry point for handling REST requests.

        Args:
            in_string: JSON string containing request details

        Returns:
            dict: Response with payload and status code
        """
        try:
            request = json.loads(in_string)

            self.session_token = request["session"]["authtoken"]
            self.global_org_client = GlobalOrgClient(self.session_token)
            self.reporting_api_client_inst = ReportingAPIClient(self.session_token)

            method = request.get("method", "GET")
            query_params = dict(request.get("query", []))

            if method == "GET":
                return self._handle_get(query_params)
            else:
                return {
                    "payload": {"error_msg": f"Method {method} not supported"},
                    "status": 405
                }

        except ReportingAPIClientException as e:
            Logger().error(f"ReportingAPIClientException: {e.error_msg}")
            return {
                "payload": {"error_msg": e.error_msg},
                "status": e.error_code
            }
        except DLPAPIException as e:
            Logger().error(f"DLPAPIException: {e.error_msg}")
            return {
                "payload": {"error_msg": e.error_msg},
                "status": e.error_code
            }
        except Exception as e:
            Logger().error(f"Unexpected error in DLPEventsAPIClient: {str(e)}")
            return {
                "payload": {"error_msg": str(e)},
                "status": 500
            }

    def _validation_error_response(self, validation_result, limit, offset):
        """Build standardized validation error response."""
        failed_field = validation_result.get("field", "unknown")
        Logger().warning(f"Validation failed for {failed_field}: {validation_result.get('message')}")
        return {
            "payload": {
                "success": False,
                "error_msg": validation_result.get("message"),
                "validation_error": True,
                "field": failed_field,
                "pagination": {"total": 0, "limit": limit, "offset": offset, "hasMore": False},
                "data": []
            },
            "status": 400
        }

    def _handle_get(self, query_params):
        """Handle GET requests for DLP events.

        Args:
            query_params: Dictionary of query parameters

        Returns:
            dict: Response with payload and status code
        """
        def get_param(name, default=""):
            val = query_params.get(name, [default])
            if isinstance(val, list):
                return val[0] if val else default
            return val if val is not None else default

        from_timestamp = get_param("from", "")
        to_timestamp = get_param("to", "")

        if not from_timestamp or not to_timestamp:
            Logger().error("Missing required parameters: from, to")
            return {
                "payload": {"error_msg": "Missing required parameters: from, to"},
                "status": 400
            }

        event_type = get_param("eventType", "all") or "all"

        limit_raw = get_param("limit", "20")
        try:
            limit = int(limit_raw)
        except (ValueError, TypeError):
            return {
                "payload": {"error_msg": f"Invalid 'limit' parameter: '{limit_raw}'. Must be an integer."},
                "status": 400
            }
        if limit < 0:
            return {
                "payload": {"error_msg": f"Invalid 'limit' parameter: '{limit}'. Must be non-negative."},
                "status": 400
            }

        offset_raw = get_param("offset", "0")
        try:
            offset = int(offset_raw)
        except (ValueError, TypeError):
            return {
                "payload": {"error_msg": f"Invalid 'offset' parameter: '{offset_raw}'. Must be an integer."},
                "status": 400
            }
        if offset < 0:
            return {
                "payload": {"error_msg": f"Invalid 'offset' parameter: '{offset}'. Must be non-negative."},
                "status": 400
            }

        severity = get_param("severity")
        action = get_param("action")

        event_actor = get_param("eventActor")
        file_name = get_param("fileName")
        destination = get_param("destination")
        rule = get_param("rule")
        detected = get_param("detected")

        tz_offset_raw = get_param("tzOffset", "")
        try:
            tz_offset_minutes = int(tz_offset_raw) if tz_offset_raw else 0
        except (ValueError, TypeError):
            tz_offset_minutes = 0

        api_filters = {
            "severity": severity,
            "action": action
        }

        client_filters = {
            "eventActor": event_actor,
            "fileName": file_name,
            "destination": destination,
            "rule": rule,
            "detected": detected
        }

        all_filters = {k: v for k, v in {**api_filters, **client_filters, "eventType": event_type}.items() if v}
        validation_result = validate_all_filters(all_filters)
        if not validation_result.get("valid"):
            return self._validation_error_response(validation_result, limit, offset)

        event_type = _EVENT_TYPE_MAP.get(event_type.strip().lower(), event_type)

        if event_type == "all":
            result = self._fetch_all_event_types(
                from_timestamp, to_timestamp, limit, offset, api_filters, client_filters, tz_offset_minutes
            )
        else:
            result = self._fetch_events(
                event_type, from_timestamp, to_timestamp, limit, offset, api_filters, client_filters, tz_offset_minutes
            )

        return {
            "payload": result,
            "status": 200
        }

    def _fetch_events(self, event_type, from_ts, to_ts, limit, offset, api_filters, client_filters, tz_offset_minutes=0):
        """Fetch events from a specific endpoint.

        Args:
            event_type: Type of events (realTime, saasApi, aiGuardrails)
            from_ts: Start timestamp (epoch ms)
            to_ts: End timestamp (epoch ms)
            limit: Number of results per page
            offset: Pagination offset
            api_filters: Server-side filter parameters
            client_filters: Client-side filter parameters (direct field -> value mapping)
            tz_offset_minutes: Client timezone offset in minutes from UTC

        Returns:
            dict: Events data with pagination info
        """
        events = self._fetch_all_pages_for_filtering(
            event_type, from_ts, to_ts, api_filters, max_events=500
        )

        return self._process_and_paginate_events(events, client_filters, limit, offset, tz_offset_minutes=tz_offset_minutes)

    def _fetch_all_pages_for_filtering(self, event_type, from_ts, to_ts, api_filters, max_events=500):
        """Fetch multiple pages of events for client-side filtering.

        Args:
            event_type: Type of events
            from_ts: Start timestamp
            to_ts: End timestamp
            api_filters: Server-side filter parameters
            max_events: Maximum total events to fetch

        Returns:
            list: All fetched events
        """
        all_events = []
        page_size = 100  # Fetch in chunks of 100
        current_offset = 0

        while len(all_events) < max_events:
            endpoint = self._get_endpoint_path(
                event_type, from_ts, to_ts, page_size, current_offset, api_filters
            )
            response = self._send_request(endpoint, _API_HEADERS)
            data = response.json()

            raw_events = data.get("events", [])
            if not raw_events:
                break

            events = self._transform_response(raw_events, event_type)
            all_events.extend(events)

            if len(raw_events) < page_size:
                break

            current_offset += page_size

        return all_events

    def _process_and_paginate_events(self, events, client_filters, limit, offset, warnings=None, tz_offset_minutes=0):
        """Process events with filtering, sorting, pagination and enrichment.

        This is a common method used by both _fetch_events and _fetch_all_event_types
        to avoid code duplication.

        Args:
            events: List of raw events to process
            client_filters: Client-side filter parameters
            limit: Number of results per page
            offset: Pagination offset
            warnings: Optional list of warning messages (for partial failures)

        Returns:
            dict: Processed events data with pagination info
        """
        # eventActor filter requires special handling: enrich ALL events first, then filter
        event_actor_filter = client_filters.get("eventActor", "")

        active_client_filters = {k: v for k, v in client_filters.items() if v}
        
        if active_client_filters:
            if event_actor_filter:
                events = self._enrich_events_with_identity(events)

                search_lower = event_actor_filter.strip().lower()
                events = [e for e in events if search_lower in e.get("eventActor", "").lower()]

                other_filters = {k: v for k, v in client_filters.items() if k != "eventActor" and v}
                if other_filters:
                    events = self._apply_client_side_filters(events, other_filters, tz_offset_minutes)
            else:
                events = self._apply_client_side_filters(events, client_filters, tz_offset_minutes)
        
        events.sort(key=lambda x: x.get("detected", ""), reverse=True)

        total = len(events)

        paginated_events = events[offset:offset + limit]
        current_page = (offset // limit) + 1 if limit > 0 else 1
        
        if not event_actor_filter:
            paginated_events = self._enrich_events_with_identity(paginated_events)
        
        result = {
            "success": True,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "hasMore": (offset + limit) < total,
                "currentPage": current_page,
                "pageSize": len(paginated_events)
            },
            "data": paginated_events
        }
        
        if warnings:
            result["warnings"] = warnings

        return result

    def _fetch_all_event_types(self, from_ts, to_ts, limit, offset, api_filters, client_filters, tz_offset_minutes=0):
        """Fetch events from all three endpoints and merge results.

        Args:
            from_ts: Start timestamp (epoch ms)
            to_ts: End timestamp (epoch ms)
            limit: Number of results per page
            offset: Pagination offset
            api_filters: Server-side filter parameters
            client_filters: Client-side search parameters
            tz_offset_minutes: Client timezone offset in minutes from UTC

        Returns:
            dict: Merged events data with pagination info
        """
        event_types = ["realTime", "saasApi", "aiGuardrails"]
        all_events = []
        failures = []
        warnings = []

        # Fetch enough from each endpoint to cover offset + limit after merging
        fetch_limit = min(offset + limit + 50, 200)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_type = {
                executor.submit(
                    self._fetch_all_pages_for_filtering,
                    event_type, from_ts, to_ts, api_filters, fetch_limit
                ): event_type
                for event_type in event_types
            }

            for future in concurrent.futures.as_completed(future_to_type):
                event_type = future_to_type[future]
                try:
                    events = future.result()
                    all_events.extend(events)
                except Exception as e:
                    error_msg = f"Failed to fetch {event_type} events: {str(e)}"
                    Logger().error(error_msg)
                    failures.append({"eventType": event_type, "error": str(e)})
                    warnings.append(f"{event_type}: {str(e)}")

        # If ALL requests failed, raise error instead of returning empty success
        if len(failures) == len(event_types):
            Logger().error("All DLP event type fetches failed")
            raise DLPAPIException(
                503,
                f"Unable to fetch DLP events. All API requests failed: {'; '.join(warnings)}"
            )

        return self._process_and_paginate_events(all_events, client_filters, limit, offset, warnings, tz_offset_minutes=tz_offset_minutes)

    def _get_endpoint_path(self, event_type, from_ts, to_ts, limit, offset, api_filters):
        """Build the API endpoint path with parameters.

        Args:
            event_type: Type of events
            from_ts: Start timestamp
            to_ts: End timestamp
            limit: Results limit
            offset: Pagination offset
            api_filters: Filter parameters

        Returns:
            str: Formatted endpoint path
        """
        base_path = _ENDPOINT_MAP[event_type]
        path = base_path.format(from_ts, to_ts, limit, offset)

        if api_filters.get("severity"):
            path += f"&severity={api_filters['severity']}"
        if api_filters.get("action"):
            path += f"&action={api_filters['action']}"

        return path

    def _send_request(self, path, headers):
        """Send HTTP request to DLP API.

        Args:
            path: API endpoint path
            headers: Request headers

        Returns:
            Response object
        """
        try:
            response = self.reporting_api_client_inst.send_request(path, "get", headers=headers)
            return response
        except Exception as e:
            Logger().error(f"DLP API Request failed: {str(e)}")
            raise

    def _transform_response(self, api_data, event_type):
        """Transform API response to UI format.

        Args:
            api_data: Raw API response data
            event_type: Type of event (for eventType field)

        Returns:
            list: Transformed events
        """
        events = []

        for item in api_data:
            origin_id = None
            if isinstance(item.get("identity"), dict):
                origin_id = item["identity"].get("originId")
            
            event = {
                "eventId": item.get("eventId", ""),
                "eventType": event_type,
                "detected": self._format_timestamp(item.get("detected", "")),
                "severity": item.get("severity", "INFO"),
                "fileName": item.get("fileName", "") or item.get("form", ""),  # aiGuardrails uses 'form'
                "destinationUrl": item.get("destinationUrl", "") or item.get("resourceName", ""),  # saasApi uses resourceName
                "ruleName": item.get("rule", {}).get("name", "") if isinstance(item.get("rule"), dict) else "",
                "action": item.get("action", ""),
                "fileOwner": "N/A",  # Not available in DLP API
                "eventActor": "N/A",  
                "identity": str(origin_id) if origin_id else "N/A",
                "_originId": origin_id
            }
            events.append(event)

        return events

    def _format_timestamp(self, timestamp):
        """Format ISO timestamp for display.

        Args:
            timestamp: ISO 8601 timestamp string

        Returns:
            str: Formatted timestamp
        """
        if not timestamp:
            return ""

        try:
            if "T" in timestamp:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M:%S") + "Z"
            return timestamp
        except Exception:
            return timestamp

    def _apply_client_side_filters(self, events, filters, tz_offset_minutes=0):
        """Apply client-side search filters.

        Args:
            events: List of events
            filters: Dictionary of filter field -> value (direct params like severity, action, etc.)
            tz_offset_minutes: Client timezone offset in minutes from UTC

        Returns:
            list: Filtered events
        """
        active_filters = {k: v.strip().lower() for k, v in filters.items() if v}
        
        if not active_filters:
            return events

        filtered = []
        for event in events:
            match = True
            for filter_field, filter_value in active_filters.items():
                event_field = _SEARCH_FIELD_MAP.get(filter_field, filter_field)
                field_value = str(event.get(event_field, "")).lower()

                if filter_field == "detected" and tz_offset_minutes != 0:
                    field_value = self._convert_to_local_time(field_value, tz_offset_minutes)

                if filter_value not in field_value:
                    match = False
                    break
            
            if match:
                filtered.append(event)

        return filtered

    def _convert_to_local_time(self, utc_timestamp, tz_offset_minutes):
        """Convert a UTC timestamp string to local time using the client's timezone offset.

        Args:
            utc_timestamp: UTC timestamp string (e.g., '2024-02-11 20:00:00z')
            tz_offset_minutes: Minutes offset from UTC (JS getTimezoneOffset convention: negative = ahead of UTC)

        Returns:
            str: Local time string in 'YYYY-MM-DD HH:MM:SS' format, or original string on parse failure
        """
        try:
            cleaned = utc_timestamp.strip().rstrip("z")
            dt = datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
            local_dt = dt - timedelta(minutes=tz_offset_minutes)
            return local_dt.strftime("%Y-%m-%d %H:%M:%S").lower()
        except (ValueError, AttributeError):
            return utc_timestamp

    def fetch_event_details(self, event_type, event_id):
        """Fetch details for a single event.

        Args:
            event_type: Type of event
            event_id: Event ID

        Returns:
            dict: Event details
        """
        path = DLPReportingAPIEndpoints.EVENT_DETAILS.value.format(event_type, event_id)
        response = self._send_request(path, _API_HEADERS)
        data = response.json()

        if data.get("data"):
            return {
                "success": True,
                "data": self._transform_response([data["data"]], event_type)[0]
            }

        return {
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "Event not found"}
        }

    def _enrich_events_with_identity(self, events):
        """Enrich events with identity labels (eventActor).

        Args:
            events: List of transformed events

        Returns:
            list: Events with eventActor populated
        """
        origin_ids = list({e["_originId"] for e in events if e.get("_originId") is not None})

        if not origin_ids:
            for event in events:
                event.pop("_originId", None)
            return events

        org_id = self.global_org_client.global_org if self.global_org_client else None
        lookup = self._fetch_identity_labels(origin_ids, org_id)

        for event in events:
            origin_id = event.get("_originId")
            if origin_id is not None:
                event["eventActor"] = lookup.get(origin_id, "Not Available")
            else:
                event["eventActor"] = "Not Available"
            event.pop("_originId", None)

        return events

    def _fetch_identity_labels(self, origin_ids, org_id=None):
        """Fetch identity labels with caching.

        Args:
            origin_ids: List of origin IDs from events
            org_id: Organization ID to scope cache entries

        Returns:
            dict: {originId: label} lookup map
        """
        global _identity_cache
        current_time = time.time()
        lookup = {}
        uncached_ids = []

        with _identity_cache_lock:
            for oid in origin_ids:
                cache_key = (org_id, oid)
                if cache_key in _identity_cache:
                    cached = _identity_cache[cache_key]
                    if current_time - cached["timestamp"] < IDENTITY_CACHE_TTL:
                        lookup[oid] = cached["label"]
                    else:
                        del _identity_cache[cache_key]
                        uncached_ids.append(oid)
                else:
                    uncached_ids.append(oid)

        # Step 2: Fetch uncached IDs from API in batches of 100
        BATCH_SIZE = 100
        if uncached_ids:
            for i in range(0, len(uncached_ids), BATCH_SIZE):
                batch = uncached_ids[i:i + BATCH_SIZE]
                try:
                    api_response = self._call_identities_api(batch)
                    with _identity_cache_lock:
                        for item in api_response.get("data", []):
                            identity_id = item.get("id")
                            label = item.get("label", "Not Available")
                            if identity_id is not None:
                                cache_key = (org_id, identity_id)
                                _identity_cache[cache_key] = {
                                    "label": label,
                                    "timestamp": current_time
                                }
                                lookup[identity_id] = label
                except Exception as e:
                    Logger().warning(f"Identity lookup failed: {str(e)}. Some event actors may show as 'Not Available'.")
                    for oid in batch:
                        lookup[oid] = "Not Available"

        # Step 3: Handle IDs not returned by API (set default)
        for oid in origin_ids:
            if oid not in lookup:
                lookup[oid] = "Not Available"

        return lookup

    def _call_identities_api(self, origin_ids):
        """Call POST /identities endpoint.

        Args:
            origin_ids: List of identity IDs to fetch

        Returns:
            dict: API response with data array

        Raises:
            Exception: Propagates any API call failures to the caller.
        """
        path = DLPReportingAPIEndpoints.IDENTITIES.value.format(len(origin_ids))
        body = json.dumps({"identityids": origin_ids})

        response = self.reporting_api_client_inst.send_request(
            path, "post", payload=body, headers=_API_HEADERS
        )
        return response.json()
