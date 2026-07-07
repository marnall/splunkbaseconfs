# encoding = utf-8

import json
from datetime import datetime, timezone
from collections import OrderedDict
from ctm360_api import ctm360_api
from timestamp_utils import get_timestamp_format, format_timestamp_ms, epoch_ms_to_seconds

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""



# --- Event timestamp normalisation -------------------------------------------
# Rewrite every date-like field in an event (including nested meta/comments) to
# the user's configured timestamp format (the input's timestamp_format setting),
# so that all logged events share one consistent timestamp representation
# regardless of the format each CTM360 endpoint happens to return.
_TS_PARSE_FORMATS = [
    "%d-%m-%Y %I:%M:%S %p",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
]
_TS_DATE_HINTS = ("date", "seen", "_at", "timestamp", "time")


def _parse_any_ts(value):
    if not value or not isinstance(value, str):
        return None
    for fmt in _TS_PARSE_FORMATS:
        try:
            return int(datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).timestamp() * 1000)
        except Exception:
            continue
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def normalize_event_timestamps(obj, ts_format):
    """Recursively rewrite date-like fields to ts_format; non-dates are left untouched."""
    if isinstance(obj, dict):
        for key, val in list(obj.items()):
            if key == "timestamp_epoch_ms":
                continue
            if isinstance(val, (dict, list)):
                normalize_event_timestamps(val, ts_format)
            elif isinstance(val, str) and val and any(h in key.lower() for h in _TS_DATE_HINTS):
                ms = _parse_any_ts(val)
                if ms is not None:
                    obj[key] = format_timestamp_ms(ms, ts_format)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                normalize_event_timestamps(item, ts_format)
    return obj


class hackerview_feed(ctm360_api):
    def __init__(self, helper):
        super().__init__(helper, helper.get_arg("hackerview_api_key"))
        self.base_URL = "https://hackerview.ctm360.com/api/v2"

    def detail_len(self, detail):
        if detail:
            return len(detail.encode('utf-8'))
        else:
            return 0

    def get_issues(self):
        """
        Returns:
            issues: List of Issue objects
        """
        try:
            offset = self.get_offset(self.base_URL + "/api_offset/issues")
            parameters = {"first_seen": offset}
            data = self.api_call(self.base_URL + "/issues", parameters)
            issues = data["issues"]
            return issues
        except Exception as e:
            self.helper.log_error("Error retrieving Hackerview Issues")
            self.helper.log_error(str(e))
            return None

    def get_resolved_issues(self):
        """
        Returns:
            resolved_issues: List of Resolved Issue objects
        """
        try:
            offset = self.get_offset(self.base_URL + "/api_offset/resolved_issues")
            parameters = {"from_date": offset}
            data = self.api_call(self.base_URL + "/resolved_issues", parameters)
            resolved_issues = data["resolved_issues"]
            return resolved_issues
        except Exception as e:
            self.helper.log_error("Error retrieving Hackerview Resolved Issues")
            self.helper.log_error(str(e))
            return None

    def get_host(self):
        """
        Returns:
            hosts: List of host objects
        """
        try:
            offset = self.get_offset(self.base_URL + "/api_offset/host")
            parameters = {"first_seen": offset}
            data = self.api_call(self.base_URL + "/assets/host", parameters)
            hosts = data["host"]
            return hosts
        except Exception as e:
            self.helper.log_error("Error retrieving Hackerview Hosts")
            self.helper.log_error(str(e))
            return None

    def get_ip(self):
        """
        Returns:
            ip_addresses: List of IP objects
        """
        try:
            offset = self.get_offset(self.base_URL + "/api_offset/ip_address")
            parameters = {"first_seen": offset}
            data = self.api_call(self.base_URL + "/assets/ip_address", parameters)
            ip_addresses = data["ip_address"]
            return ip_addresses
        except Exception as e:
            self.helper.log_error("Error retrieving Hackerview IPs")
            self.helper.log_error(str(e))
            return None

    def event_obj_gen(self, timestamp_str, event):
        """
        Generate event object
        """
        try:
            timestamp = (
                datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000
            )
            event_obj = OrderedDict({"timestamp": int(timestamp)})
            event_obj.update(event)
            return event_obj
        except Exception as e:
            raise Exception(e)

    def push_events(self, event_writer):
        """
        Push events to splunk index
        """

        index = self.helper.get_output_index()
        source_type = self.helper.get_sourcetype()

        issues = self.get_issues()
        if issues is not None:
            self.helper.log_info(f"New issues: {len(issues)}")
            for issue in issues:
                try:
                    event_obj = self.event_obj_gen(
                        issue.get("meta").get("last_seen"), issue
                    )
                    if (self.detail_len(event_obj.get("detail"))>7000):
                        event_obj["detail"] = event_obj["detail"][:7000]
                    event = self.helper.new_event(
                        data=json.dumps(event_obj),
                        index=index,
                        source="issue",
                        sourcetype=source_type,
                    )
                    event_writer.write_event(event)
                except Exception as e:
                    self.helper.log_error(str(e))

        resolved_issues = self.get_resolved_issues()
        if resolved_issues is not None:
            self.helper.log_info(f"Resolved issues: {len(resolved_issues)}")
            for issue in resolved_issues:
                try:
                    event_obj = self.event_obj_gen(
                        issue.get("meta").get("last_seen"), issue
                    )
                    if (self.detail_len(event_obj.get("detail"))>7000):
                        event_obj["detail"] = event_obj["detail"][:7000]
                    event = self.helper.new_event(
                        data=json.dumps(event_obj),
                        index=index,
                        source="resolved_issue",
                        sourcetype=source_type,
                    )
                    event_writer.write_event(event)
                except Exception as e:
                    self.helper.log_error(str(e))

        hosts = self.get_host()
        if hosts is not None:
            self.helper.log_info(f"Hosts: {len(hosts)}")
            for host in hosts:
                try:
                    event_obj = self.event_obj_gen(
                        host.get("meta").get("first_seen"), host
                    )
                    event = self.helper.new_event(
                        data=json.dumps(event_obj),
                        index=index,
                        source="host",
                        sourcetype=source_type,
                    )
                    event_writer.write_event(event)
                except Exception as e:
                    self.helper.log_error(str(e))

        ip_addresses = self.get_ip()
        if ip_addresses is not None:
            self.helper.log_info(f"IP addresses: {len(ip_addresses)}")
            for ip in ip_addresses:
                try:
                    event_obj = self.event_obj_gen(ip.get("meta").get("first_seen"), ip)
                    event = self.helper.new_event(
                        data=json.dumps(event_obj),
                        index=index,
                        source="ip",
                        sourcetype=source_type,
                    )
                    event_writer.write_event(event)
                except Exception as e:
                    self.helper.log_error(str(e))


def validate_input(helper, definition):
    """Validate input stanza configuration."""
    params = getattr(definition, "parameters", {}) or {}

    # Required
    api_key = params.get("hackerview_api_key")
    if not api_key:
        raise ValueError("HackerView API key (hackerview_api_key) is required")

    # Optional retry knobs
    for key in ("max_retries", "retry_base_delay", "max_retry_delay"):
        val = params.get(key)
        if val is None:
            continue
        try:
            iv = int(str(val))
            if iv < 0:
                raise ValueError
        except Exception:
            raise ValueError(f"{key} must be a non-negative integer if provided")


def collect_events(helper, ew):
    """Collect HackerView events with resilient retries and safe parsing."""
    import time
    import requests

    hv = hackerview_feed(helper)

    index = helper.get_output_index()
    source_type = helper.get_sourcetype()

    # ---- User-configurable timestamp format ----
    ts_format = get_timestamp_format(helper)
    helper.log_info(f"Using timestamp format: {ts_format}")

    # ---- Checkpoint keys ----
    LIGHTSCAN_CHECKPOINT_KEY = "lightscan_processed_ticket_ids"
    DEEPSCAN_CHECKPOINT_KEY = "deepscan_processed_ticket_ids"
    DEEPSCAN_RESOLVED_CHECKPOINT_KEY = "deepscan_resolved_processed_ticket_ids"
    
    # ---- Max records limit ----
    MAX_RECORDS = 5000

    # ---- Configurable retry knobs (safe defaults) ----
    def _int_arg(name, default):
        try:
            v = helper.get_arg(name)
            return int(v) if v is not None and str(v) != "" else default
        except Exception:
            return default

    MAX_RETRIES = _int_arg("max_retries", 5)
    BASE_DELAY = _int_arg("retry_base_delay", 1)   # seconds
    MAX_DELAY = _int_arg("max_retry_delay", 60)    # seconds cap

    # ---- Timestamp parsing ----
    def parse_ts(ts_str):
        """Accept common 24h and ISO-8601 variants."""
        if not ts_str:
            return None
        fmts = [
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %I:%M:%S %p",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
        ]
        for f in fmts:
            try:
                dt = datetime.strptime(ts_str, f).replace(tzinfo=timezone.utc)
                return int(dt.timestamp() * 1000)
            except Exception:
                continue
        try:
            ts2 = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts2)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except Exception:
            return None

    # Timeout for HackerView API calls: (connect=30s, read=120s).
    # The AOB default is (10, 5) which is too short for large responses.
    HV_HTTP_TIMEOUT = (30, 120)

    # ---- HTTP GET without params (for endpoints without offset) ----
    def http_get_no_params(url):
        """
        GET without parameters for endpoints that don't use offset.
        Returns status, body, and JSON data.
        """
        proxy_settings = helper.get_proxy()
        use_proxy = bool(proxy_settings)
        attempt = 0

        while True:
            try:
                resp = helper.send_http_request(
                    url,
                    "GET",
                    headers=getattr(hv, "headers", None),
                    timeout=HV_HTTP_TIMEOUT,
                    use_proxy=use_proxy,
                )
                resp.raise_for_status()
                body = getattr(resp, "text", "") or ""
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                return resp.status_code, body, data

            except requests.exceptions.HTTPError as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status in (502, 503, 504) and attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    helper.log_warning(
                        f"Transient HTTP {status} from {url}. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                helper.log_error(f"HTTP error calling {url}: {str(e)}")
                raise

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    helper.log_warning(
                        f"{type(e).__name__} calling {url}. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                helper.log_error(f"Network error calling {url}: {str(e)}")
                raise

            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    helper.log_warning(
                        f"Request error calling {url}. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                helper.log_error(f"Request error calling {url}: {str(e)}")
                raise

    # ---- HTTP GET with params (for endpoints that still use offset or need params) ----
    def http_get(url, params):
        """
        GET with parameters and retries.
        Returns status, body, and JSON data.
        """
        proxy_settings = helper.get_proxy()
        use_proxy = bool(proxy_settings)
        attempt = 0

        while True:
            try:
                resp = helper.send_http_request(
                    url,
                    "GET",
                    headers=getattr(hv, "headers", None),
                    parameters=params,
                    timeout=HV_HTTP_TIMEOUT,
                    use_proxy=use_proxy,
                )
                resp.raise_for_status()
                body = getattr(resp, "text", "") or ""
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                return resp.status_code, body, data

            except requests.exceptions.HTTPError as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status in (502, 503, 504) and attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    helper.log_warning(
                        f"Transient HTTP {status} from {url}. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                helper.log_error(f"HTTP error calling {url}: {str(e)}")
                raise

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    helper.log_warning(
                        f"{type(e).__name__} calling {url}. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                helper.log_error(f"Network error calling {url}: {str(e)}")
                raise

            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    helper.log_warning(
                        f"Request error calling {url}. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                helper.log_error(f"Request error calling {url}: {str(e)}")
                raise

    # ---- Resource fetchers ----
    def get_offset(path_suffix):
        return hv.get_offset(hv.base_URL + path_suffix)

    def fetch_lightscan_issues():
        """Fetch Light Scan issues without offset - returns all active issues."""
        status, body, data = http_get_no_params(hv.base_URL + "/issues")
        helper.log_info(f"lightscan_issues status: {status}")
        if body:
            helper.log_info(f"lightscan_issues body (first 1000 chars): {body[:1000]}")
        return data.get("issues", []) if isinstance(data, dict) else []

    def fetch_deepscan_issues():
        """Fetch DeepScan active issues (status=active by default)."""
        status, body, data = http_get_no_params(hv.base_URL + "/issues/deepscan")
        helper.log_info(f"deepscan_issues status: {status}")
        if body:
            helper.log_info(f"deepscan_issues body (first 1000 chars): {body[:1000]}")
        return data.get("issues", []) if isinstance(data, dict) else []

    def fetch_deepscan_resolved_issues():
        """Fetch DeepScan resolved/inactive issues (status=inactive)."""
        params = {"status": "inactive"}
        status, body, data = http_get(hv.base_URL + "/issues/deepscan", params)
        helper.log_info(f"deepscan_resolved_issues status: {status}")
        if body:
            helper.log_info(f"deepscan_resolved_issues body (first 1000 chars): {body[:1000]}")
        return data.get("issues", []) if isinstance(data, dict) else []

    def fetch_resolved_issues():
        """Fetch Light Scan resolved issues (still using offset API)."""
        off = get_offset("/api_offset/resolved_issues")
        params = {"from_date": off}
        status, body, data = http_get(hv.base_URL + "/resolved_issues", params)
        helper.log_info(f"resolved_issues status: {status}")
        if body:
            helper.log_info(f"resolved_issues body (first 1000 chars): {body[:1000]}")
        return data.get("resolved_issues", []) if isinstance(data, dict) else []

    def fetch_hosts():
        off = get_offset("/api_offset/host")
        params = {"first_seen": off}
        status, body, data = http_get(hv.base_URL + "/assets/host", params)
        helper.log_info(f"host status: {status}")
        if body:
            helper.log_info(f"host body (first 1000 chars): {body[:1000]}")
        return data.get("host", []) if isinstance(data, dict) else []

    def fetch_ips():
        off = get_offset("/api_offset/ip_address")
        params = {"first_seen": off}
        status, body, data = http_get(hv.base_URL + "/assets/ip_address", params)
        helper.log_info(f"ip_address status: {status}")
        if body:
            helper.log_info(f"ip_address body (first 1000 chars): {body[:1000]}")
        return data.get("ip_address", []) if isinstance(data, dict) else []

    # ---- Write events ----
    def write_event(obj_dict, source):
        # Extract epoch_ms for _time before formatting
        event_time = epoch_ms_to_seconds(obj_dict.get("timestamp_epoch_ms"))
        event = helper.new_event(
            data=json.dumps(normalize_event_timestamps(obj_dict, ts_format)),
            time=event_time,
            index=index,
            source=source,
            sourcetype=source_type,
        )
        ew.write_event(event)

    # ---- Light Scan Issues (with checkpoint to avoid duplicates) ----
    try:
        # Get previously processed ticket IDs from checkpoint
        processed_ticket_ids = helper.get_check_point(LIGHTSCAN_CHECKPOINT_KEY) or {}
        
        all_issues = fetch_lightscan_issues()
        helper.log_info(f"Total Light Scan issues from API: {len(all_issues)}")
        
        # Limit to MAX_RECORDS (5000)
        issues_to_process = all_issues[:MAX_RECORDS] if len(all_issues) > MAX_RECORDS else all_issues
        if len(all_issues) > MAX_RECORDS:
            helper.log_info(f"Limiting Light Scan issues to {MAX_RECORDS} records (had {len(all_issues)})")
        
        new_ticket_ids = {}
        new_issues_count = 0
        
        for issue in issues_to_process:
            # Light Scan issues have ticket_id in meta.ticket_id
            ticket_id = (issue or {}).get("meta", {}).get("ticket_id")
            
            # Skip if already processed
            if ticket_id and ticket_id in processed_ticket_ids:
                helper.log_debug(f"Skipping already processed Light Scan ticket: {ticket_id}")
                continue
            
            # Light Scan issues use meta.last_seen for timestamp
            ts = (issue or {}).get("meta", {}).get("last_seen")
            ts_ms = parse_ts(ts) or int(datetime.now(timezone.utc).timestamp() * 1000)
            event_obj = OrderedDict({
                "timestamp": format_timestamp_ms(ts_ms, ts_format),
                "timestamp_epoch_ms": ts_ms,
            })
            event_obj.update(issue or {})
            
            # Format first_seen and last_seen fields if present
            if "first_seen" in event_obj and event_obj["first_seen"]:
                first_seen_ms = parse_ts(event_obj["first_seen"])
                if first_seen_ms:
                    event_obj["first_seen"] = format_timestamp_ms(first_seen_ms, ts_format)
            if "last_seen" in event_obj and event_obj["last_seen"]:
                last_seen_ms = parse_ts(event_obj["last_seen"])
                if last_seen_ms:
                    event_obj["last_seen"] = format_timestamp_ms(last_seen_ms, ts_format)
            
            # Truncate detail if too long
            detail = event_obj.get("detail")
            if detail and hv.detail_len(detail) > 7000:
                event_obj["detail"] = detail[:7000]
            
            write_event(event_obj, "issue")
            
            # Track this ticket_id as processed
            if ticket_id:
                new_ticket_ids[ticket_id] = True
                new_issues_count += 1
        
        helper.log_info(f"New Light Scan issues written: {new_issues_count}")
        
        # Update checkpoint with newly processed ticket IDs
        if new_ticket_ids:
            processed_ticket_ids.update(new_ticket_ids)
            helper.save_check_point(LIGHTSCAN_CHECKPOINT_KEY, processed_ticket_ids)
            helper.log_info(f"Updated Light Scan checkpoint with {len(new_ticket_ids)} new ticket IDs. Total tracked: {len(processed_ticket_ids)}")
            
    except Exception as e:
        helper.log_error(f"lightscan_issues fetch/write failed: {str(e)}")

    # ---- DeepScan Issues (with checkpoint to avoid duplicates) ----
    try:
        # Get previously processed ticket IDs from checkpoint
        processed_ticket_ids = helper.get_check_point(DEEPSCAN_CHECKPOINT_KEY) or {}
        
        all_deepscan_issues = fetch_deepscan_issues()
        helper.log_info(f"Total DeepScan issues from API: {len(all_deepscan_issues)}")
        
        # Limit to MAX_RECORDS (5000)
        deepscan_to_process = all_deepscan_issues[:MAX_RECORDS] if len(all_deepscan_issues) > MAX_RECORDS else all_deepscan_issues
        if len(all_deepscan_issues) > MAX_RECORDS:
            helper.log_info(f"Limiting DeepScan issues to {MAX_RECORDS} records (had {len(all_deepscan_issues)})")
        
        new_ticket_ids = {}
        new_issues_count = 0
        
        for issue in deepscan_to_process:
            # DeepScan issues have ticket_id at root level
            ticket_id = (issue or {}).get("ticket_id")
            
            # Skip if already processed
            if ticket_id and ticket_id in processed_ticket_ids:
                helper.log_debug(f"Skipping already processed DeepScan ticket: {ticket_id}")
                continue
            
            # DeepScan issues use last_seen directly (not nested in meta)
            ts = (issue or {}).get("last_seen")
            ts_ms = parse_ts(ts) or int(datetime.now(timezone.utc).timestamp() * 1000)
            event_obj = OrderedDict({
                "timestamp": format_timestamp_ms(ts_ms, ts_format),
                "timestamp_epoch_ms": ts_ms,
            })
            event_obj.update(issue or {})
            
            # Format first_seen and last_seen fields if present
            if "first_seen" in event_obj and event_obj["first_seen"]:
                first_seen_ms = parse_ts(event_obj["first_seen"])
                if first_seen_ms:
                    event_obj["first_seen"] = format_timestamp_ms(first_seen_ms, ts_format)
            if "last_seen" in event_obj and event_obj["last_seen"]:
                last_seen_ms = parse_ts(event_obj["last_seen"])
                if last_seen_ms:
                    event_obj["last_seen"] = format_timestamp_ms(last_seen_ms, ts_format)
            
            # Truncate issue_description if too long
            desc = event_obj.get("issue_description")
            if desc and hv.detail_len(desc) > 7000:
                event_obj["issue_description"] = desc[:7000]
            
            write_event(event_obj, "deepscan_issue")
            
            # Track this ticket_id as processed
            if ticket_id:
                new_ticket_ids[ticket_id] = True
                new_issues_count += 1
        
        helper.log_info(f"New DeepScan issues written: {new_issues_count}")
        
        # Update checkpoint with newly processed ticket IDs
        if new_ticket_ids:
            processed_ticket_ids.update(new_ticket_ids)
            helper.save_check_point(DEEPSCAN_CHECKPOINT_KEY, processed_ticket_ids)
            helper.log_info(f"Updated DeepScan checkpoint with {len(new_ticket_ids)} new ticket IDs. Total tracked: {len(processed_ticket_ids)}")
            
    except Exception as e:
        helper.log_error(f"deepscan_issues fetch/write failed: {str(e)}")

    # ---- DeepScan Resolved Issues (with checkpoint to avoid duplicates) ----
    try:
        # Get previously processed ticket IDs from checkpoint
        processed_ticket_ids = helper.get_check_point(DEEPSCAN_RESOLVED_CHECKPOINT_KEY) or {}
        
        all_deepscan_resolved = fetch_deepscan_resolved_issues()
        helper.log_info(f"Total DeepScan resolved issues from API: {len(all_deepscan_resolved)}")
        
        # Limit to MAX_RECORDS (5000)
        deepscan_resolved_to_process = all_deepscan_resolved[:MAX_RECORDS] if len(all_deepscan_resolved) > MAX_RECORDS else all_deepscan_resolved
        if len(all_deepscan_resolved) > MAX_RECORDS:
            helper.log_info(f"Limiting DeepScan resolved issues to {MAX_RECORDS} records (had {len(all_deepscan_resolved)})")
        
        new_ticket_ids = {}
        new_issues_count = 0
        
        for issue in deepscan_resolved_to_process:
            # DeepScan issues have ticket_id at root level
            ticket_id = (issue or {}).get("ticket_id")
            
            # Skip if already processed
            if ticket_id and ticket_id in processed_ticket_ids:
                helper.log_debug(f"Skipping already processed DeepScan resolved ticket: {ticket_id}")
                continue
            
            # DeepScan issues use last_seen directly (not nested in meta)
            ts = (issue or {}).get("last_seen")
            ts_ms = parse_ts(ts) or int(datetime.now(timezone.utc).timestamp() * 1000)
            event_obj = OrderedDict({
                "timestamp": format_timestamp_ms(ts_ms, ts_format),
                "timestamp_epoch_ms": ts_ms,
            })
            event_obj.update(issue or {})
            
            # Format first_seen and last_seen fields if present
            if "first_seen" in event_obj and event_obj["first_seen"]:
                first_seen_ms = parse_ts(event_obj["first_seen"])
                if first_seen_ms:
                    event_obj["first_seen"] = format_timestamp_ms(first_seen_ms, ts_format)
            if "last_seen" in event_obj and event_obj["last_seen"]:
                last_seen_ms = parse_ts(event_obj["last_seen"])
                if last_seen_ms:
                    event_obj["last_seen"] = format_timestamp_ms(last_seen_ms, ts_format)
            
            # Truncate issue_description if too long
            desc = event_obj.get("issue_description")
            if desc and hv.detail_len(desc) > 7000:
                event_obj["issue_description"] = desc[:7000]
            
            write_event(event_obj, "deepscan_resolved_issue")
            
            # Track this ticket_id as processed
            if ticket_id:
                new_ticket_ids[ticket_id] = True
                new_issues_count += 1
        
        helper.log_info(f"New DeepScan resolved issues written: {new_issues_count}")
        
        # Update checkpoint with newly processed ticket IDs
        if new_ticket_ids:
            processed_ticket_ids.update(new_ticket_ids)
            helper.save_check_point(DEEPSCAN_RESOLVED_CHECKPOINT_KEY, processed_ticket_ids)
            helper.log_info(f"Updated DeepScan resolved checkpoint with {len(new_ticket_ids)} new ticket IDs. Total tracked: {len(processed_ticket_ids)}")
            
    except Exception as e:
        helper.log_error(f"deepscan_resolved_issues fetch/write failed: {str(e)}")

    # ---------- Attack Surface feeds (documented range params + local checkpoint; no /api_offset) ----------
    # The new HV endpoints have no server-side offset API. Incremental pull works by
    # sending the documented range param (first_seen / added_date / from_date) derived
    # from a local checkpoint, deduplicating via processed ids, and only advancing the
    # checkpoint on success. The checkpoint tracks the SAME field the server filters on
    # (e.g. meta.first_seen), never last_seen, so late-discovered assets are not missed.

    def fmt_range_param(epoch_ms):
        if not epoch_ms:
            return None
        dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        # API range params use DD-MM-YYYY HH:mm (24h, minute precision). Flooring to
        # the minute re-fetches up to a minute of overlap, which dedup absorbs.
        return dt.strftime("%d-%m-%Y %H:%M")

    def resolve_list(data, documented_key, source_name):
        """Resolve the response list tolerantly: prefer the expected key, else
        fall back to the first array value in the response (some endpoints
        return their list under a different key than expected)."""
        if not isinstance(data, dict):
            return []
        v = data.get(documented_key)
        if isinstance(v, list):
            return v
        for k, vv in data.items():
            if k in ("statusCode", "success", "message", "count"):
                continue
            if isinstance(vv, list):
                helper.log_warning(
                    f"{source_name}: documented list key '{documented_key}' absent; using '{k}'"
                )
                return vv
        return []

    def write_asset_feed(path, source_name, list_key, checkpoint_key, range_param,
                         checkpoint_ts_fields, id_fields, extra_params=None):
        checkpoint = helper.get_check_point(checkpoint_key) or {}
        last_ts = checkpoint.get("last_ts")
        processed_ids = checkpoint.get("processed_ids", {})

        params = dict(extra_params or {})
        df = fmt_range_param(last_ts)
        if df:
            params[range_param] = df

        helper.log_info(
            f"{source_name} checkpoint: last_ts={last_ts} | processed_ids={len(processed_ids)} | "
            f"{range_param}={params.get(range_param)}"
        )

        try:
            if params:
                status, body, data = http_get(hv.base_URL + path, params)
            else:
                status, body, data = http_get_no_params(hv.base_URL + path)
        except Exception as e:
            # Never advance the checkpoint on failure
            helper.log_error(f"{source_name} HTTP failure: {str(e)}")
            return

        helper.log_info(f"{source_name} status: {status}")
        if body:
            helper.log_info(f"{source_name} response body (first 500 chars): {body[:500]}")

        items = resolve_list(data, list_key, source_name)
        helper.log_info(f"{source_name} items found: {len(items)}")
        if not items:
            helper.log_info(f"{source_name} returned no items; checkpoint unchanged.")
            return

        max_ts = last_ts or 0
        new_processed = {}
        events_written = 0

        for item in items:
            if not isinstance(item, dict):
                continue
            meta = item.get("meta") or {}

            key_parts = []
            for f in id_fields:
                v = item.get(f)
                if v is None:
                    v = meta.get(f)
                if v not in (None, ""):
                    key_parts.append(f"{f}:{v}")
            item_id = "|".join(key_parts) if key_parts else None

            if item_id and (item_id in processed_ids or item_id in new_processed):
                continue

            # Checkpoint timestamp: the field the server-side range param filters on
            ck_ms = None
            for f in checkpoint_ts_fields:
                ck_ms = parse_ts(meta.get(f)) or parse_ts(item.get(f))
                if ck_ms:
                    break

            # Display/event timestamp: prefer recency
            ev_ms = None
            for f in ("last_seen", "first_seen", "added_date", "detected_at"):
                ev_ms = parse_ts(meta.get(f)) or parse_ts(item.get(f))
                if ev_ms:
                    break
            event_ts = ev_ms or ck_ms or int(datetime.now(timezone.utc).timestamp() * 1000)

            event_obj = OrderedDict({
                "timestamp": format_timestamp_ms(event_ts, ts_format),
                "timestamp_epoch_ms": event_ts,
                "source": source_name,
            })
            if item_id:
                event_obj["item_id"] = item_id
            event_obj.update(item)

            write_event(event_obj, source_name)
            events_written += 1

            if item_id:
                new_processed[item_id] = True
            if ck_ms and ck_ms > max_ts:
                max_ts = ck_ms

        processed_ids.update(new_processed)
        if len(processed_ids) > 10000:
            processed_ids = dict(list(processed_ids.items())[-10000:])

        if events_written > 0:
            new_ts = max_ts if max_ts > (last_ts or 0) else last_ts
        elif max_ts == last_ts and last_ts is not None:
            new_ts = max_ts + 1000
            helper.log_warning(
                f"{source_name} all {len(items)} items were duplicates at checkpoint ts; "
                f"advancing by 1s to prevent a stuck loop"
            )
        else:
            new_ts = max_ts if max_ts > (last_ts or 0) else last_ts

        helper.save_check_point(checkpoint_key, {"last_ts": new_ts, "processed_ids": processed_ids})
        helper.log_info(
            f"{source_name} saved checkpoint: last_ts={new_ts} | "
            f"processed_ids={len(processed_ids)} | events_written={events_written}"
        )

    ASSET_FEEDS = [
        ("/assets/domain", "domain"),
        ("/assets/ip_range", "ip_range"),
        ("/assets/website", "website"),
        ("/assets/mobile_app", "mobile_app"),
        ("/assets/executive", "executive"),
        ("/assets/social_media_profile", "social_media_profile"),
        ("/assets/third_party", "third_party"),
        ("/assets/code_repository", "code_repository"),
        ("/assets/bin", "bin"),
        ("/assets/service", "service"),
    ]
    for feed_path, feed_name in ASSET_FEEDS:
        try:
            write_asset_feed(
                path=feed_path,
                source_name=feed_name,
                list_key=feed_name,
                checkpoint_key=f"hv_{feed_name}_checkpoint",
                range_param="first_seen",
                checkpoint_ts_fields=("first_seen",),
                id_fields=("value", "protocol", "port") if feed_name == "service" else ("value",),
            )
        except Exception as e:
            helper.log_error(f"{feed_name} feed failed: {str(e)}")

    # Potential assets: filtered by added_date; status is part of the identity so
    # pending -> approved/rejected transitions land as new events.
    try:
        write_asset_feed(
            path="/assets/potential_assets",
            source_name="potential_assets",
            list_key="potential_assets",
            checkpoint_key="hv_potential_assets_checkpoint",
            range_param="added_date",
            checkpoint_ts_fields=("added_date",),
            id_fields=("value", "asset_type", "status"),
        )
    except Exception as e:
        helper.log_error(f"potential_assets feed failed: {str(e)}")

    # Asset Watch change log: filtered by from_date on detection time.
    try:
        write_asset_feed(
            path="/asset_watch/change_log",
            source_name="asset_watch_changelog",
            list_key="change_logs",
            checkpoint_key="hv_asset_watch_changelog_checkpoint",
            range_param="from_date",
            checkpoint_ts_fields=("detected_at", "last_seen"),
            id_fields=("detected_at", "event", "category", "asset", "attribute", "old_value", "new_value"),
        )
    except Exception as e:
        helper.log_error(f"asset_watch_changelog feed failed: {str(e)}")

    # Light Scan resolved issues / hosts / IPs use the same checkpoint+dedup
    # engine as the asset feeds. The server-side /api_offset value alone is not
    # a reliable duplicate guard, so these feeds keep their own checkpoint and
    # processed-id state. Source names and payload shapes match the original
    # feeds, so existing searches and dashboards keep working.
    try:
        write_asset_feed(
            path="/resolved_issues",
            source_name="resolved_issue",
            list_key="resolved_issues",
            checkpoint_key="hv_resolved_issue_checkpoint",
            range_param="from_date",
            checkpoint_ts_fields=("last_seen", "first_seen"),
            id_fields=("ticket_id",),
        )
    except Exception as e:
        helper.log_error(f"resolved_issue feed failed: {str(e)}")

    try:
        write_asset_feed(
            path="/assets/host",
            source_name="host",
            list_key="host",
            checkpoint_key="hv_host_checkpoint",
            range_param="first_seen",
            checkpoint_ts_fields=("first_seen",),
            id_fields=("value",),
        )
    except Exception as e:
        helper.log_error(f"host feed failed: {str(e)}")

    try:
        write_asset_feed(
            path="/assets/ip_address",
            source_name="ip",
            list_key="ip_address",
            checkpoint_key="hv_ip_checkpoint",
            range_param="first_seen",
            checkpoint_ts_fields=("first_seen",),
            id_fields=("value",),
        )
    except Exception as e:
        helper.log_error(f"ip feed failed: {str(e)}")
