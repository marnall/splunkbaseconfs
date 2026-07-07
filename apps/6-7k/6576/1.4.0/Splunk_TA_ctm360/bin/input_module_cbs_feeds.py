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


class cbs_feed(ctm360_api):
    def __init__(self, helper):
        super().__init__(helper, helper.get_arg("cbs_api_key"))
        self.base_URL = "https://cbs.ctm360.com/api/v2"

    def get_incidents(self):
        """
        Returns:
            incidents: List of Incident objects
        """
        try:
            offset = self.get_offset(self.base_URL + "/api_offset/incidents")
            parameters = {"date_from": offset, "date_field": "incident.last_updated_date"}
            data = self.api_call(self.base_URL + "/incidents", parameters)
            incidents = data["incident_list"]
            return incidents
        except Exception as e:
            self.helper.log_error("Error retrieving CBS Incidents")
            self.helper.log_error(str(e))
            return None

    def event_obj_gen(self, timestamp_str, event):
        """
        Generate event object
        """
        try:
            timestamp = (
                datetime.strptime(timestamp_str, "%d-%m-%Y %I:%M:%S %p")
                .replace(tzinfo=timezone.utc)
                .timestamp()
                * 1000
            )
            cbs_url = "https://cbs.ctm360.com/threat_manager/incidents/" + event.get("id")
            event_obj = OrderedDict({"timestamp": int(timestamp), "cbs_url": cbs_url})
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

        incidents = self.get_incidents()
        if incidents is not None:
            self.helper.log_info(f"Incidents found: {len(incidents)}")
            for incident in incidents:
                try:
                    event_obj = self.event_obj_gen(incident.get("updated_date"), incident)
                    event = self.helper.new_event(
                        data=json.dumps(event_obj),
                        index=index,
                        source="incident",
                        sourcetype=source_type,
                    )
                    event_writer.write_event(event)
                except Exception as e:
                    self.helper.log_error(str(e))


def validate_input(helper, definition):
    """Validate input stanza configuration."""
    params = getattr(definition, "parameters", {}) or {}
    api_key = params.get("cbs_api_key")
    if not api_key:
        raise ValueError("CBS API key (cbs_api_key) is required")

    # Optional retry tuning (non-negative ints)
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
    """Collect CBS events with ThreatCover-style checkpoint method and fixed advancement logic."""
    import time
    import requests

    cbs = cbs_feed(helper)

    index = helper.get_output_index()
    source_type = helper.get_sourcetype()

    # ---- User-configurable timestamp format ----
    ts_format = get_timestamp_format(helper)
    helper.log_info(f"Using timestamp format: {ts_format}")

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

    # ---- Helpers ----
    def log_checkpoint_summary(stage):
        """Log checkpoint summary for all feed types."""
        def fmt(data):
            if isinstance(data, dict):
                last_ts = data.get("last_ts")
                processed_count = len(data.get("processed_ids", {}))
                return f"last_ts={last_ts} | {fmt_date_from(last_ts)} | processed_ids={processed_count}"
            return "None"
        
        ck_inc = helper.get_check_point("cbs_incidents_checkpoint")
        ck_ml = helper.get_check_point("cbs_malware_logs_checkpoint")
        ck_bc = helper.get_check_point("cbs_breached_credentials_checkpoint")
        ck_cl = helper.get_check_point("cbs_card_leaks_checkpoint")
        ck_dp = helper.get_check_point("cbs_domain_protection_checkpoint")
        ck_mm = helper.get_check_point("cbs_money_mules_checkpoint")
        ck_gs = helper.get_check_point("cbs_gambling_sites_checkpoint")
        ck_smf = helper.get_check_point("cbs_social_media_fraud_checkpoint")

        helper.log_info(
            f"checkpoint summary [{stage}] → "
            f"incidents: {fmt(ck_inc)}, malware_logs: {fmt(ck_ml)}, "
            f"breached_credentials: {fmt(ck_bc)}, card_leaks: {fmt(ck_cl)}, "
            f"domain_protection: {fmt(ck_dp)}, money_mules: {fmt(ck_mm)}, "
            f"gambling_sites: {fmt(ck_gs)}, social_media_fraud: {fmt(ck_smf)}"
        )

    def parse_ts(ts_str):
        """
        Try multiple formats:
        - '31-01-2025 11:59:59 PM' (existing)
        - '31-01-2025 23:59:59'   (24h)
        - ISO-8601 like '2025-01-31T23:59:59Z' / '2025-01-31 23:59:59'
        """
        if not ts_str:
            return None
        fmts = [
            "%d-%m-%Y %I:%M:%S %p",
            "%d-%m-%Y %H:%M:%S",
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
        # Last resort: try fromisoformat (handles offsets), after replacing 'Z'
        try:
            ts_str2 = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str2)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except Exception:
            return None

    def to_epoch_ms(ts_str):
        # Keep old behavior for compatibility but delegate to parse_ts
        return parse_ts(ts_str)

    def fmt_date_from(epoch_ms):
        if not epoch_ms:
            return None
        dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        # include seconds to avoid server-side truncation edge cases
        return dt.strftime("%d-%m-%Y %H:%M:%S")

    # Timeout for CBS API calls: (connect=30s, read=120s).
    # The AOB default is (10, 5) which is far too short for large payloads
    # such as 5 000 malware-log records.
    CBS_HTTP_TIMEOUT = (30, 120)

    def http_get(url, request_params):
        """
        GET with retries on transient failures:
          - HTTP 502/503/504
          - Timeouts / Connection errors / generic RequestException
        Uses capped exponential backoff.
        Returns (status_code, text, json_dict) on success.
        Raises on final failure.
        """
        proxy_settings = helper.get_proxy()
        use_proxy = bool(proxy_settings)

        attempt = 0
        while True:
            try:
                resp = helper.send_http_request(
                    url,
                    "GET",
                    headers=cbs.headers,
                    parameters=request_params,
                    timeout=CBS_HTTP_TIMEOUT,
                    use_proxy=use_proxy,
                )
                # Force error handling for non-2xx so we don't treat an error page as data
                resp.raise_for_status()

                status = getattr(resp, "status_code", None)
                text = getattr(resp, "text", "") or ""
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                return status, text, data

            except requests.exceptions.HTTPError as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status in (502, 503, 504) and attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    helper.log_warning(
                        f"Transient HTTP {status} from {url}. "
                        f"Retry in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})."
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
                        f"{type(e).__name__} calling {url}. "
                        f"Retry in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})."
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
                        f"Request error calling {url}. "
                        f"Retry in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                helper.log_error(f"Request error calling {url}: {str(e)}")
                raise

    def get_item_id(item, source_name):
        """
        Extract unique identifier from item based on source type.
        Returns a string identifier or None if not found.
        """
        # Try common ID fields
        for field in ["id", "_id", "uuid", "guid"]:
            if field in item and item[field]:
                return str(item[field])

        # Source-specific explicit identifiers (documented per-feed ID fields)
        if source_name == "money_mules" and item.get("money_mule_id"):
            return str(item["money_mule_id"])
        if source_name == "gambling_sites" and item.get("finding_id"):
            return str(item["finding_id"])

        # For items without explicit ID, create composite key from available fields
        # This ensures we can still track duplicates
        if source_name == "incident":
            # Use incident ID if available
            return item.get("id")
        elif source_name in ["malware_logs", "breached_credentials", "card_leaks", "domain_protection",
                             "money_mules", "gambling_sites", "social_media_fraud"]:
            # Create composite key from multiple fields
            key_parts = []
            for field in ["hash", "email", "domain", "url", "ip", "card_number",
                          "account_identifier", "subject", "platform", "title"]:
                if field in item and item[field]:
                    key_parts.append(f"{field}:{item[field]}")
            
            # Add timestamp to make it more unique
            for ts_field in ["last_seen", "first_seen", "index_time", "created_date"]:
                if ts_field in item and item[ts_field]:
                    key_parts.append(f"{ts_field}:{item[ts_field]}")
                    break
            
            if key_parts:
                return "|".join(key_parts)
        
        return None

    def cleanup_processed_ids(processed_ids, max_size=10000):
        """
        Keep only the most recent max_size entries to prevent unbounded growth.
        This is a safety measure for long-running inputs.
        """
        if len(processed_ids) > max_size:
            # Keep the last max_size entries
            # Note: dict maintains insertion order in Python 3.7+
            items = list(processed_ids.items())
            return dict(items[-max_size:])
        return processed_ids

    # ---------- Generic writer with ThreatCover-style checkpointing and fixed advancement ----------
    def write_events_with_checkpoint(path, params, list_key, source_name, timestamp_fields, checkpoint_key):
        """
        Uses ThreatCover-style checkpoint with:
        1. last_ts - timestamp of most recent item processed
        2. processed_ids - dict of item IDs already processed (prevents duplicates)
        
        Always advances the checkpoint when the API returns data so the input
        cannot loop on the same time window.
        """
        # Load checkpoint (contains both last_ts and processed_ids)
        checkpoint = helper.get_check_point(checkpoint_key) or {}
        last_ts = checkpoint.get("last_ts")
        processed_ids = checkpoint.get("processed_ids", {})
        
        request_params = dict(params or {})
        df = fmt_date_from(last_ts)
        if df:
            request_params["date_from"] = df

        helper.log_info(
            f"{source_name} checkpoint: last_ts={last_ts} | {fmt_date_from(last_ts)} | "
            f"processed_ids={len(processed_ids)} | date_from={request_params.get('date_from')}"
        )
        helper.log_info(f"{source_name} request params: {json.dumps(request_params)}")

        try:
            status, text, data = http_get(cbs.base_URL + path, request_params)
        except Exception as e:
            # Do not advance checkpoint on failures (ThreatCover pattern)
            helper.log_error(f"{source_name} HTTP failure: {str(e)}")
            return

        helper.log_info(f"{source_name} status: {status}")
        if text:
            helper.log_info(f"{source_name} response body (first 1000 chars): {text[:1000]}")

        items = data.get(list_key, []) if isinstance(data, dict) else []
        helper.log_info(f"{source_name} items found: {len(items)}")

        if not items:
            helper.log_info(f"{source_name} returned no items; checkpoint unchanged.")
            return

        max_ts = last_ts or 0
        new_processed_ids = {}
        events_written = 0

        for item in items:
            # Get unique identifier for this item
            item_id = get_item_id(item, source_name)

            # Skip if already processed (ThreatCover duplicate prevention)
            if item_id and item_id in processed_ids:
                helper.log_debug(f"{source_name} skipping duplicate item_id: {item_id}")
                continue

            # Pick first parseable timestamp from preferred fields
            ts_ms = None
            for field in timestamp_fields:
                v = item.get(field)
                ts_ms = to_epoch_ms(v)
                if ts_ms:
                    break

            # Use parsed timestamp or current time for event
            event_ts = ts_ms if ts_ms else int(datetime.now(timezone.utc).timestamp() * 1000)
            event_obj = OrderedDict({
                "timestamp": format_timestamp_ms(event_ts, ts_format),
                "timestamp_epoch_ms": event_ts,
                "source": source_name,
            })
            if item_id:
                event_obj["item_id"] = item_id
            event_obj.update(item)
            
            # Format first_seen and last_seen fields if present
            if "first_seen" in event_obj and event_obj["first_seen"]:
                first_seen_ms = to_epoch_ms(event_obj["first_seen"])
                if first_seen_ms:
                    event_obj["first_seen"] = format_timestamp_ms(first_seen_ms, ts_format)
            if "last_seen" in event_obj and event_obj["last_seen"]:
                last_seen_ms = to_epoch_ms(event_obj["last_seen"])
                if last_seen_ms:
                    event_obj["last_seen"] = format_timestamp_ms(last_seen_ms, ts_format)

            event = helper.new_event(
                data=json.dumps(normalize_event_timestamps(event_obj, ts_format)),
                time=epoch_ms_to_seconds(event_ts),
                index=index,
                source=source_name,
                sourcetype=source_type,
            )
            ew.write_event(event)
            events_written += 1

            # Track this item as processed
            if item_id:
                new_processed_ids[item_id] = True

            # Track max timestamp
            if ts_ms and ts_ms > max_ts:
                max_ts = ts_ms

        # Checkpoint advancement: new events advance to the max timestamp; an
        # all-duplicate batch at an unchanged timestamp advances by 1 second; an
        # empty response leaves the checkpoint untouched (handled above).
        if items:
            # Merge processed IDs (even if all were duplicates)
            processed_ids.update(new_processed_ids)
            processed_ids = cleanup_processed_ids(processed_ids)
            
            # Determine new timestamp
            if events_written > 0:
                # Normal case: new events written, use max timestamp
                new_ts = max_ts if max_ts > (last_ts or 0) else last_ts
                helper.log_info(
                    f"{source_name} wrote {events_written} new events, advancing checkpoint"
                )
            elif max_ts == last_ts and last_ts is not None:
                # Stuck case: API returned items with same timestamp, all were duplicates
                # Add 1 second to move past this timestamp
                new_ts = max_ts + 1000
                helper.log_warning(
                    f"{source_name} all {len(items)} items were duplicates at timestamp {max_ts}, "
                    f"advancing by 1 second to {new_ts} to prevent stuck loop"
                )
            else:
                # Items returned but with newer timestamp, all duplicates
                # This means we're catching up, advance to max_ts
                new_ts = max_ts if max_ts > (last_ts or 0) else last_ts
                helper.log_info(
                    f"{source_name} all {len(items)} items were duplicates, "
                    f"but advancing checkpoint to max_ts={new_ts}"
                )
            
            new_checkpoint = {
                "last_ts": new_ts,
                "processed_ids": processed_ids
            }
            helper.save_check_point(checkpoint_key, new_checkpoint)
            helper.log_info(
                f"{source_name} saved checkpoint: last_ts={new_checkpoint['last_ts']} | "
                f"{fmt_date_from(new_checkpoint['last_ts'])} | "
                f"processed_ids={len(new_checkpoint['processed_ids'])} | events_written={events_written}"
            )
        else:
            helper.log_info(f"{source_name} no items returned; checkpoint unchanged.")

    # ---------- Incidents (special: uses event_obj_gen + known fields) ----------
    def write_incidents():
        checkpoint_key = "cbs_incidents_checkpoint"
        checkpoint = helper.get_check_point(checkpoint_key) or {}
        last_ts = checkpoint.get("last_ts")
        processed_ids = checkpoint.get("processed_ids", {})
        
        params = {"date_field": "incident.last_updated_date"}
        df = fmt_date_from(last_ts)
        if df:
            params["date_from"] = df

        helper.log_info(
            f"incidents checkpoint: last_ts={last_ts} | {fmt_date_from(last_ts)} | "
            f"processed_ids={len(processed_ids)} | date_from={params.get('date_from')}"
        )
        helper.log_info(f"incidents request params: {json.dumps(params)}")

        try:
            status, text, data = http_get(cbs.base_URL + "/incidents", params)
        except Exception as e:
            helper.log_error(f"incidents HTTP failure: {str(e)}")
            return

        helper.log_info(f"incidents status: {status}")
        if text:
            helper.log_info(f"incidents response body (first 1000 chars): {text[:1000]}")

        incidents = data.get("incident_list", []) if isinstance(data, dict) else []
        helper.log_info(f"Incidents found: {len(incidents)}")

        if not incidents:
            helper.log_info("incidents returned no items; checkpoint unchanged.")
            return

        max_ts = last_ts or 0
        new_processed_ids = {}
        events_written = 0

        for incident in incidents:
            try:
                # Get incident ID
                incident_id = incident.get("id")
                
                # Skip if already processed
                if incident_id and incident_id in processed_ids:
                    helper.log_debug(f"incidents skipping duplicate incident_id: {incident_id}")
                    continue
                
                ts_str = incident.get("updated_date") or incident.get("created_date")
                ts_ms = to_epoch_ms(ts_str) if ts_str else None

                # For event body, keep existing shape with cbs_url when possible
                if ts_str:
                    event_ts = parse_ts(ts_str) or int(datetime.now(timezone.utc).timestamp() * 1000)
                    cbs_url = "https://cbs.ctm360.com/threat_manager/incidents/" + (incident.get("id") or "")
                    event_obj = OrderedDict({
                        "timestamp": format_timestamp_ms(event_ts, ts_format),
                        "timestamp_epoch_ms": event_ts,
                        "cbs_url": cbs_url,
                    })
                    event_obj.update(incident)
                else:
                    event_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
                    event_obj = OrderedDict({
                        "timestamp": format_timestamp_ms(event_ts, ts_format),
                        "timestamp_epoch_ms": event_ts,
                    })
                    event_obj.update(incident)

                event = helper.new_event(
                    data=json.dumps(normalize_event_timestamps(event_obj, ts_format)),
                    time=epoch_ms_to_seconds(event_ts),
                    index=index,
                    source="incident",
                    sourcetype=source_type,
                )
                ew.write_event(event)
                events_written += 1

                # Track as processed
                if incident_id:
                    new_processed_ids[incident_id] = True

                # Track max timestamp
                if ts_ms and ts_ms > max_ts:
                    max_ts = ts_ms
            except Exception as inner_e:
                helper.log_error(str(inner_e))

        # Checkpoint advancement (same strategy as the other feeds)
        if incidents:
            processed_ids.update(new_processed_ids)
            processed_ids = cleanup_processed_ids(processed_ids)
            
            # Determine new timestamp
            if events_written > 0:
                new_ts = max_ts if max_ts > (last_ts or 0) else last_ts
                helper.log_info(
                    f"incidents wrote {events_written} new events, advancing checkpoint"
                )
            elif max_ts == last_ts and last_ts is not None:
                # Stuck case: all items were duplicates at same timestamp
                new_ts = max_ts + 1000
                helper.log_warning(
                    f"incidents all {len(incidents)} items were duplicates at timestamp {max_ts}, "
                    f"advancing by 1 second to {new_ts} to prevent stuck loop"
                )
            else:
                new_ts = max_ts if max_ts > (last_ts or 0) else last_ts
                helper.log_info(
                    f"incidents all {len(incidents)} items were duplicates, "
                    f"but advancing checkpoint to max_ts={new_ts}"
                )
            
            new_checkpoint = {
                "last_ts": new_ts,
                "processed_ids": processed_ids
            }
            helper.save_check_point(checkpoint_key, new_checkpoint)
            helper.log_info(
                f"incidents saved checkpoint: last_ts={new_checkpoint['last_ts']} | "
                f"{fmt_date_from(new_checkpoint['last_ts'])} | "
                f"processed_ids={len(new_checkpoint['processed_ids'])} | events_written={events_written}"
            )
        else:
            helper.log_info("incidents no items returned; checkpoint unchanged.")

    # ---------- Typed feeds (multiple types sharing one checkpoint) ----------
    def write_typed_feed(path, source_name, checkpoint_key, types, base_params=None):
        """
        Same checkpoint strategy as write_events_with_checkpoint, but for endpoints
        that take a type parameter (domain_protection, social_media_fraud): each run
        iterates all types against a single shared checkpoint.
        """
        checkpoint = helper.get_check_point(checkpoint_key) or {}
        last_ts = checkpoint.get("last_ts")
        processed_ids = checkpoint.get("processed_ids", {})

        base_params = dict(base_params or {"size": 5000, "risk_score_min": 0, "risk_score_max": 100})
        df = fmt_date_from(last_ts)
        if df:
            base_params["date_from"] = df

        helper.log_info(
            f"{source_name} checkpoint: last_ts={last_ts} | {fmt_date_from(last_ts)} | "
            f"processed_ids={len(processed_ids)} | date_from={base_params.get('date_from')}"
        )

        max_ts = last_ts or 0
        new_processed_ids = {}
        events_written = 0
        total_items = 0

        for feed_type in types:
            request_params = dict(base_params)
            request_params["type"] = feed_type

            helper.log_info(f"{source_name} request params ({feed_type}): {json.dumps(request_params)}")

            try:
                status, text, data = http_get(cbs.base_URL + path, request_params)
            except Exception as e:
                helper.log_error(f"{source_name} HTTP failure ({feed_type}): {str(e)}")
                continue  # try the other types, but don't advance checkpoint

            helper.log_info(f"{source_name} status ({feed_type}): {status}")
            if text:
                helper.log_info(f"{source_name} response body ({feed_type}) (first 1000 chars): {text[:1000]}")

            items = data.get("hits", []) if isinstance(data, dict) else []
            helper.log_info(f"{source_name} items found ({feed_type}): {len(items)}")
            total_items += len(items)

            if not items:
                continue

            for item in items:
                # Get item ID
                item_id = get_item_id(item, source_name)

                # Skip if already processed
                if item_id and item_id in processed_ids:
                    helper.log_debug(f"{source_name} skipping duplicate item_id: {item_id}")
                    continue

                ts_ms = None
                for field in ["last_seen", "first_seen", "index_time", "created_date"]:
                    v = item.get(field)
                    ts_ms = to_epoch_ms(v)
                    if ts_ms:
                        break

                event_ts = ts_ms if ts_ms else int(datetime.now(timezone.utc).timestamp() * 1000)
                event_obj = OrderedDict({
                    "timestamp": format_timestamp_ms(event_ts, ts_format),
                    "timestamp_epoch_ms": event_ts,
                    "source": source_name,
                    "type": feed_type,
                })
                if item_id:
                    event_obj["item_id"] = item_id
                event_obj.update(item)

                event = helper.new_event(
                    data=json.dumps(normalize_event_timestamps(event_obj, ts_format)),
                    time=epoch_ms_to_seconds(event_ts),
                    index=index,
                    source=source_name,
                    sourcetype=source_type,
                )
                ew.write_event(event)
                events_written += 1

                # Track as processed
                if item_id:
                    new_processed_ids[item_id] = True

                if ts_ms and ts_ms > max_ts:
                    max_ts = ts_ms

        # Checkpoint advancement (same strategy as the other feeds)
        if total_items > 0:
            processed_ids.update(new_processed_ids)
            processed_ids = cleanup_processed_ids(processed_ids)

            if events_written > 0:
                new_ts = max_ts if max_ts > (last_ts or 0) else last_ts
                helper.log_info(
                    f"{source_name} wrote {events_written} new events, advancing checkpoint"
                )
            elif max_ts == last_ts and last_ts is not None:
                new_ts = max_ts + 1000
                helper.log_warning(
                    f"{source_name} all {total_items} items were duplicates at timestamp {max_ts}, "
                    f"advancing by 1 second to {new_ts} to prevent stuck loop"
                )
            else:
                new_ts = max_ts if max_ts > (last_ts or 0) else last_ts
                helper.log_info(
                    f"{source_name} all {total_items} items were duplicates, "
                    f"but advancing checkpoint to max_ts={new_ts}"
                )

            new_checkpoint = {
                "last_ts": new_ts,
                "processed_ids": processed_ids
            }
            helper.save_check_point(checkpoint_key, new_checkpoint)
            helper.log_info(
                f"{source_name} saved checkpoint: last_ts={new_checkpoint['last_ts']} | "
                f"{fmt_date_from(new_checkpoint['last_ts'])} | "
                f"processed_ids={len(new_checkpoint['processed_ids'])} | events_written={events_written}"
            )
        else:
            helper.log_info(f"{source_name} no items returned; checkpoint unchanged.")

    # ---------- Run ----------
    log_checkpoint_summary("start")

    write_incidents()

    # Malware Logs
    write_events_with_checkpoint(
        path="/leaks/malware_logs",
        params={"size": 5000},
        list_key="hits",
        source_name="malware_logs",
        timestamp_fields=["last_seen", "first_seen", "index_time", "created_date"],
        checkpoint_key="cbs_malware_logs_checkpoint",
    )

    # Breached Credentials
    write_events_with_checkpoint(
        path="/leaks/breached_credentials",
        params={"size": 5000},
        list_key="hits",
        source_name="breached_credentials",
        timestamp_fields=["last_seen", "index_time", "breach_date", "first_seen", "created_date"],
        checkpoint_key="cbs_breached_credentials_checkpoint",
    )

    # Card Leaks
    write_events_with_checkpoint(
        path="/leaks/card_leaks",
        params={"size": 5000},
        list_key="hits",
        source_name="card_leaks",
        timestamp_fields=["last_seen", "first_seen", "index_time", "created_date"],
        checkpoint_key="cbs_card_leaks_checkpoint",
    )

    # Domain Protection
    write_typed_feed(
        path="/domain_protection",
        source_name="domain_protection",
        checkpoint_key="cbs_domain_protection_checkpoint",
        types=["domain_infringement", "subdomain_infringement"],
    )

    # Money Mules
    write_events_with_checkpoint(
        path="/online_anti_fraud/money_mules",
        params={"size": 5000},
        list_key="hits",
        source_name="money_mules",
        timestamp_fields=["last_seen", "first_seen", "index_time", "created_date"],
        checkpoint_key="cbs_money_mules_checkpoint",
    )

    # Gambling Sites
    write_events_with_checkpoint(
        path="/online_anti_fraud/gambling_sites",
        params={"size": 5000},
        list_key="hits",
        source_name="gambling_sites",
        timestamp_fields=["last_seen", "first_seen", "index_time", "created_date"],
        checkpoint_key="cbs_gambling_sites_checkpoint",
    )

    # Social Media Fraud (the API requires the type parameter)
    write_typed_feed(
        path="/social_media_fraud",
        source_name="social_media_fraud",
        checkpoint_key="cbs_social_media_fraud_checkpoint",
        types=["brand_impersonation", "vip_impersonation"],
    )

    log_checkpoint_summary("end")
