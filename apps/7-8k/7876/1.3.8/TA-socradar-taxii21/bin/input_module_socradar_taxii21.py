import os
import sys
import time
import json 
import hashlib
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone
import re

# Splunk Add-on SDK objects (helper, ew) are injected by Splunk when the script runs.

# --- SOCRadar TAXII 2.1 Configuration ---
TAXII_BASE_URL = "https://taxii2.socradar.com"
API_TIMEOUT_SECONDS = 60
TAXII_HEADERS = {"Accept": "application/taxii+json;version=2.1"}

# Default API Root - can be overridden in global settings
DEFAULT_API_ROOT = "api"

# TAXII 2.1 pagination
MAX_OBJECTS_PER_REQUEST = 1000
MAX_REQUESTS_PER_COLLECTION = 100  # Safety limit

# Incremental indexing - index after every page for immediate visibility
BATCH_INDEX_PAGES = 1

# --- Helper Functions ---
def validate_input(helper, definition):
    """Validation for modular input configurations"""
    pass  # Global settings validated elsewhere

def _parse_collection_ids(collections_str, helper):
    """
    Parses collection IDs from comma-separated string.
    
    Args:
        collections_str: Comma-separated collection IDs
        helper: Splunk helper object for logging
    
    Returns:
        List of collection IDs
    """
    if not collections_str or not collections_str.strip() or collections_str.lower() == 'none':
        return []
    
    # Parse collection IDs
    collection_ids = [cid.strip() for cid in collections_str.split(",") if cid.strip()]
    
    helper.log_info(f"Parsed {len(collection_ids)} collection IDs")
    return collection_ids

def _get_epoch_from_stix_timestamp(timestamp_str, helper, object_id=""):
    """
    Convert STIX timestamp string to epoch timestamp.
    Handles variable-length microseconds properly.
    
    Args:
        timestamp_str: ISO 8601 timestamp string
        helper: Splunk helper object for logging
        object_id: Object ID for error logging
    
    Returns:
        float: Epoch timestamp or None if parsing fails
    """
    if not timestamp_str:
        return None
    
    try:
        # Clean up the timestamp string
        clean_timestamp = timestamp_str.strip()
        
        # Handle microseconds normalization - Python requires exactly 6 digits
        if '.' in clean_timestamp:
            # Split into main part and fractional seconds + timezone
            parts = clean_timestamp.split('.')
            if len(parts) == 2:
                # Extract the fractional seconds and timezone
                frac_and_tz = parts[1]
                
                # Find where timezone starts (+ or - or Z)
                tz_start = None
                for i, char in enumerate(frac_and_tz):
                    if char in ['+', '-', 'Z']:
                        tz_start = i
                        break
                
                if tz_start is not None:
                    # Extract fractional seconds and timezone separately
                    frac_seconds = frac_and_tz[:tz_start]
                    timezone_part = frac_and_tz[tz_start:]
                    
                    # Normalize fractional seconds to exactly 6 digits
                    if len(frac_seconds) < 6:
                        frac_seconds = frac_seconds.ljust(6, '0')
                    elif len(frac_seconds) > 6:
                        frac_seconds = frac_seconds[:6]
                    
                    # Reconstruct the timestamp
                    clean_timestamp = f"{parts[0]}.{frac_seconds}{timezone_part}"
        
        # Handle Z suffix (Zulu time) after microsecond normalization
        if clean_timestamp.endswith('Z'):
            clean_timestamp = clean_timestamp[:-1] + '+00:00'
        
        # Parse ISO 8601 timestamp
        dt_obj = datetime.fromisoformat(clean_timestamp)
        
        # Ensure timezone is set (assume UTC if none)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        
        epoch_time = dt_obj.timestamp()
        helper.log_debug(f"Parsed timestamp '{timestamp_str}' -> {epoch_time} for object '{object_id}'")
        return epoch_time
        
    except Exception as e:
        helper.log_error(f"Failed to parse timestamp '{timestamp_str}' for object '{object_id}': {e}")
        return None

def _extract_event_timestamp(stix_object, helper):
    """
    Extract the best timestamp for the event from STIX object.
    Prioritizes 'created' field as requested.
    
    Args:
        stix_object: STIX object dictionary
        helper: Splunk helper object for logging
    
    Returns:
        float: Epoch timestamp or None
    """
    object_id = stix_object.get("id", "unknown")
    
    # Priority order: created first (as requested), then fallbacks
    timestamp_fields = ["created", "modified", "date_added", "first_seen", "last_seen", "valid_from"]
    
    for field in timestamp_fields:
        if field in stix_object:
            timestamp_str = stix_object.get(field)
            if timestamp_str:
                epoch_time = _get_epoch_from_stix_timestamp(timestamp_str, helper, object_id)
                if epoch_time:
                    helper.log_debug(f"Using timestamp field '{field}' = '{timestamp_str}' for object '{object_id}'")
                    return epoch_time
    
    helper.log_warning(f"No valid timestamp found for object '{object_id}'. Available fields: {list(stix_object.keys())}")
    return None

def _extract_checkpoint_timestamp(stix_object, helper):
    """
    Extract timestamp for checkpoint tracking.
    Uses different priority than event timestamp.
    
    Args:
        stix_object: STIX object dictionary
        helper: Splunk helper object for logging
    
    Returns:
        str: ISO timestamp string or None
    """
    # For checkpoint, prioritize when the object was added to the collection
    checkpoint_fields = ["date_added", "x_added_time", "modified", "created"]
    
    for field in checkpoint_fields:
        if field in stix_object:
            timestamp_str = stix_object.get(field)
            if timestamp_str:
                return timestamp_str
    
    return None

# --- Main Collection Logic ---
def collect_events(helper, ew):
    input_name = helper.get_input_stanza_names()
    helper.log_info(f"SOCRadar TAXII 2.1 SCRIPT_START: Input='{input_name}'")

    # --- Proxy Configuration ---
    proxy_settings = helper.get_proxy()
    proxies = None
    
    if proxy_settings:
        proxy_url = proxy_settings.get('proxy_url')
        proxy_port = proxy_settings.get('proxy_port')
        proxy_username = proxy_settings.get('proxy_username')
        proxy_password = proxy_settings.get('proxy_password')
        
        if proxy_url and proxy_port:
            if proxy_username and proxy_password:
                proxy = f"http://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}"
            else:
                proxy = f"http://{proxy_url}:{proxy_port}"
            
            proxies = {'http': proxy, 'https': proxy}
            helper.log_info(f"Proxy configured: {proxy_url}:{proxy_port}")
    else:
        helper.log_info("Proxy is not enabled!")

    # --- Configuration Retrieval (Global Settings) ---
    username = helper.get_global_setting("taxii_username")
    password = helper.get_global_setting("taxii_password")
    api_root = helper.get_arg("api_root") or DEFAULT_API_ROOT
    collection_ids_str = helper.get_arg('collection_ids')

    helper.log_debug(f"Input '{input_name}' - Config: Username Set: {bool(username)}, "
                     f"API Root: {api_root}, "
                     f"Collections: '{collection_ids_str}'")

    if not username or not password:
        helper.log_error(f"Input '{input_name}': TAXII username/password not configured. Exiting.")
        return

    # Parse collection IDs
    collection_ids = _parse_collection_ids(collection_ids_str, helper)
    
    if not collection_ids:
        helper.log_info(f"Input '{input_name}': No TAXII collections configured. Exiting.")
        return
    
    helper.log_info(f"Input '{input_name}': Processing {len(collection_ids)} TAXII collections")

    # Setup authentication
    auth = HTTPBasicAuth(username, password)
    
    checkpoint_key_prefix = f"{input_name}_socradar_taxii21_v4_"  # v4: timestamp-based, no object_ids
    total_events_indexed_this_run = 0
    
    # Process each collection
    for collection_id in collection_ids:
        if not collection_id:
            continue

        helper.log_info(f"Input '{input_name}': Processing TAXII Collection ID: '{collection_id}'")
        
        # Load checkpoint for this collection (v5: timestamp-based, no object_ids)
        collection_checkpoint_key = f"{checkpoint_key_prefix}{collection_id}"
        processed_object_ids = set()  # In-memory dedup for current run only
        last_checkpoint_timestamp = None

        try:
            raw_checkpoint_data = helper.get_check_point(collection_checkpoint_key)
            if raw_checkpoint_data:
                checkpoint_data = json.loads(raw_checkpoint_data)
                last_checkpoint_timestamp = checkpoint_data.get("last_checkpoint_timestamp")
                prev_total = checkpoint_data.get("total_indexed", 0)
                helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                              f"Loaded checkpoint. Previously indexed: {prev_total}. "
                              f"Last timestamp: {last_checkpoint_timestamp}")
        except Exception as e:
            helper.log_warning(f"Input '{input_name}', Collection '{collection_id}': "
                             f"Error loading checkpoint: {e}. Starting fresh.")
            last_checkpoint_timestamp = None

        # --- TAXII API Fetching with Incremental Indexing ---
        page_buffer = []  # Buffer for current batch
        request_count = 0
        total_duplicates_found = 0
        total_events_indexed_this_collection = 0
        pages_since_last_index = 0
        
        # Build URL and initial params
        url = f"{TAXII_BASE_URL}/{api_root}/collections/{collection_id}/objects/"
        params = {"limit": str(MAX_OBJECTS_PER_REQUEST)}
        
        # If we have a checkpoint timestamp, use it for incremental collection
        if last_checkpoint_timestamp:
            params["added_after"] = last_checkpoint_timestamp
            helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                          f"Using incremental collection from {last_checkpoint_timestamp}")
        
        next_id = None
        latest_checkpoint_timestamp = last_checkpoint_timestamp
        
        while request_count < MAX_REQUESTS_PER_COLLECTION:
            # Add next parameter if we have it
            if next_id:
                params['next'] = next_id
            else:
                # Remove next param for first request
                params.pop('next', None)
            
            helper.log_debug(f"Input '{input_name}', Collection '{collection_id}': "
                           f"Request {request_count + 1} with params: {params}")
            
            try:
                # Make TAXII request
                response = requests.get(
                    url,
                    headers=TAXII_HEADERS,
                    params=params,
                    auth=auth,
                    timeout=API_TIMEOUT_SECONDS,
                    proxies=proxies
                )
                request_count += 1
                
                # Handle rate limiting
                retry_count = 0
                max_retries = 2
                while response.status_code == 429 and retry_count < max_retries:
                    retry_delay = 10 * (retry_count + 1)
                    helper.log_warning(f"Input '{input_name}', Collection '{collection_id}': "
                                     f"Rate limited (429). Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    response = requests.get(
                        url,
                        headers=TAXII_HEADERS,
                        params=params,
                        auth=auth,
                        timeout=API_TIMEOUT_SECONDS,
                        proxies=proxies
                    )
                    retry_count += 1
                
                if response.status_code != 200:
                    helper.log_error(f"Input '{input_name}', Collection '{collection_id}': "
                                   f"API Error {response.status_code}: {response.text}")
                    break
                
                # Parse STIX bundle
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    helper.log_error(f"Input '{input_name}', Collection '{collection_id}': "
                                   f"JSON decode error: {e}")
                    break
                
                # Extract objects from bundle
                stix_objects = data.get("objects", [])
                
                if not stix_objects:
                    helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                                  f"No objects in response. End of data.")
                    break
                
                # Process objects and check for duplicates
                page_new_count = 0
                page_duplicate_count = 0
                
                for obj in stix_objects:
                    if not isinstance(obj, dict):
                        continue
                    
                    obj_id = obj.get("id")
                    if not obj_id:
                        continue
                    
                    # Track latest checkpoint timestamp
                    obj_checkpoint_time = _extract_checkpoint_timestamp(obj, helper)
                    if obj_checkpoint_time and (not latest_checkpoint_timestamp or obj_checkpoint_time > latest_checkpoint_timestamp):
                        latest_checkpoint_timestamp = obj_checkpoint_time
                    
                    # Check if we've seen this object before (in-memory dedup for current run)
                    if obj_id not in processed_object_ids:
                        page_buffer.append(obj)
                        processed_object_ids.add(obj_id)
                        page_new_count += 1
                    else:
                        page_duplicate_count += 1
                        total_duplicates_found += 1

                pages_since_last_index += 1
                helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                              f"Page {request_count}: {len(stix_objects)} objects, "
                              f"{page_new_count} new, {page_duplicate_count} duplicates. "
                              f"Buffer: {len(page_buffer)} objects")

                # --- Incremental Indexing: Index after every BATCH_INDEX_PAGES pages ---
                if pages_since_last_index >= BATCH_INDEX_PAGES and page_buffer:
                    batch_indexed_count = 0
                    for stix_object in page_buffer:
                        obj_id = stix_object.get("id", "unknown")
                        event_data = dict(stix_object)
                        event_data["_taxii_collection_id"] = collection_id
                        event_data["_taxii_source"] = "socradar"
                        event_time_epoch = _extract_event_timestamp(stix_object, helper)

                        try:
                            splunk_event = helper.new_event(
                                data=json.dumps(event_data),
                                time=event_time_epoch,
                                sourcetype=helper.get_sourcetype()
                            )
                            ew.write_event(splunk_event)
                            batch_indexed_count += 1
                        except Exception as e:
                            helper.log_error(f"Error writing event for '{obj_id}': {e}")

                    total_events_indexed_this_collection += batch_indexed_count
                    helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                                  f"BATCH INDEXED: {batch_indexed_count} objects. "
                                  f"Total: {total_events_indexed_this_collection}")

                    # Save lightweight checkpoint (timestamp only, no object_ids)
                    try:
                        checkpoint_data = {
                            "last_checkpoint_timestamp": latest_checkpoint_timestamp,
                            "last_updated": datetime.now(timezone.utc).isoformat(),
                            "total_indexed": total_events_indexed_this_collection,
                            "checkpoint_version": "v5"
                        }
                        helper.save_check_point(collection_checkpoint_key, json.dumps(checkpoint_data))
                    except Exception as e:
                        helper.log_warning(f"Checkpoint save error: {e}")

                    # Clear buffer
                    page_buffer = []
                    pages_since_last_index = 0
                
                # Check if there are more pages
                if data.get('more', False):
                    next_id = data.get('next')
                    if not next_id:
                        helper.log_warning(f"Input '{input_name}', Collection '{collection_id}': "
                                         f"'more' is True but 'next' is missing. Stopping pagination.")
                        break
                else:
                    helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                                  f"No more pages available.")
                    break
                
                # Small delay between requests
                time.sleep(0.5)
                
            except requests.exceptions.RequestException as e:
                helper.log_error(f"Input '{input_name}', Collection '{collection_id}': "
                               f"Request Error: {e}")
                break
            except Exception as e:
                helper.log_error(f"Input '{input_name}', Collection '{collection_id}': "
                               f"Unexpected Error: {e}")
                break

        if request_count >= MAX_REQUESTS_PER_COLLECTION:
            helper.log_warning(f"Input '{input_name}', Collection '{collection_id}': "
                             f"Reached MAX_REQUESTS_PER_COLLECTION ({MAX_REQUESTS_PER_COLLECTION}).")

        # --- Index any remaining objects in buffer ---
        if page_buffer:
            batch_indexed_count = 0
            for stix_object in page_buffer:
                obj_id = stix_object.get("id", "unknown")
                event_data = dict(stix_object)
                event_data["_taxii_collection_id"] = collection_id
                event_data["_taxii_source"] = "socradar"
                event_time_epoch = _extract_event_timestamp(stix_object, helper)

                try:
                    splunk_event = helper.new_event(
                        data=json.dumps(event_data),
                        time=event_time_epoch,
                        sourcetype=helper.get_sourcetype()
                    )
                    ew.write_event(splunk_event)
                    batch_indexed_count += 1
                except Exception as e:
                    helper.log_error(f"Error writing event for '{obj_id}': {e}")

            total_events_indexed_this_collection += batch_indexed_count
            helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                          f"FINAL BATCH INDEXED: {batch_indexed_count} objects. "
                          f"Total: {total_events_indexed_this_collection}")

        # --- Save final checkpoint ---
        try:
            checkpoint_data = {
                "last_checkpoint_timestamp": latest_checkpoint_timestamp,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_indexed": total_events_indexed_this_collection,
                "checkpoint_version": "v5"
            }
            helper.save_check_point(collection_checkpoint_key, json.dumps(checkpoint_data))
            helper.log_info(f"Input '{input_name}', Collection '{collection_id}': "
                          f"Collection complete. Indexed {total_events_indexed_this_collection} objects. "
                          f"Checkpoint saved.")
        except Exception as e:
            helper.log_error(f"Checkpoint save error: {e}")

        total_events_indexed_this_run += total_events_indexed_this_collection
        time.sleep(1)

    helper.log_info(f"SOCRadar TAXII 2.1 SCRIPT_END: Input='{input_name}'. "
                  f"Total new STIX objects indexed: {total_events_indexed_this_run}.")

# --- Splunk Boilerplate ---
from splunklib.modularinput import Scheme, Argument

def get_scheme():
    """Returns scheme for Splunk modular input"""
    scheme = Scheme("SOCRadar TAXII 2.1 Collector")
    scheme.description = ("Collects STIX 2.1 threat intelligence from SOCRadar TAXII server. "
                         "Supports incremental collection with proper pagination and handles deduplication. "
                         "Configure username, password, and collection IDs in global settings. "
                         "Uses 'created' field as primary timestamp for events.")
    scheme.use_external_validation = True
    scheme.use_single_instance = False

    # No per-input arguments needed since we use global settings
    return scheme