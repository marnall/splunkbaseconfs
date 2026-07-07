import os
import sys
import time
import json 
import hashlib
from datetime import datetime, timezone

# Splunk imports
from splunklib.modularinput import Scheme, Argument

# ===== CONFIGURATION CONSTANTS =====
# Note: The SOCRadar feed API returns the complete feed in a single response.
# Pagination parameters are not supported for this endpoint.

SOCRADAR_API_BASE_URL = "https://platform.socradar.com/api"
API_TIMEOUT_SECONDS = 60

# Recommended collections from SOCRadar
RECOMMENDED_COLLECTIONS = {
    "SOCRadar-APT-Recommended-Block-IP": {
        "feed_id": "4d7a69ce6e7c49ff8c916da5d7343916"
    },
    "SOCRadar-APT-Recommended-Block-Hash": {
        "feed_id": "0cb06558728b4dc296019c93b78360d1"
    },
    "SOCRadar-APT-Recommended-Block-Domain": {
        "feed_id": "9079dcc2f96e4835bb807026d4cdcc86"
    },
    "SOCRadar-Recommended-Block-Hash": {
        "feed_id": "8742cab86cc4414092217f87298e94a1"
    },
    "SOCRadar-Attackers-Recommended-Block-IP": {
        "feed_id": "e89ab3b58e174b8c82767088d8e66cae"
    },
    "SOCRadar-Attackers-Recommended-Block-Domain": {
        "feed_id": "606a83358bbe466d8c3885e37fa595b7"
    },
    "SOCRadar-Recommended-Phishing-Global": {
        "feed_id": "03cc11380b5d4a77a0d0cc2a7c568230"
    }
}

# Checkpoint settings
CHECKPOINT_MAX_SIZE = 1000000     # Maximum signatures to store in checkpoint

# Rate limiting settings
MAX_RATE_LIMIT_RETRIES = 3        # How many times to retry on 429 error
RATE_LIMIT_DELAYS = [30, 60]      # Wait times for retries: 30s first, 60s second

# Processing settings
API_REQUEST_DELAY = 5             # Wait 5 seconds before each API request
COLLECTION_DELAY = 1              # Delay between processing collections


# ===== HELPER FUNCTIONS =====

def parse_boolean_setting(value, default=False):
    """
    Convert various string representations to boolean.
    Handles checkbox values from Splunk UI.
    
    Args:
        value: Boolean or string value from settings
        default: Default value if input is None or invalid
    
    Returns:
        Boolean value
    """
    if value is None:
        return default
    
    # If it's already a boolean, return it directly
    if isinstance(value, bool):
        return value
    
    # Convert to string and lowercase for comparison
    value_str = str(value).lower().strip()
    
    # Empty string means unchecked checkbox
    if value_str == '':
        return False
    
    # Explicitly check for false values
    if value_str in ['false', '0', 'no', 'disable', 'off', 'unchecked']:
        return False
    
    # Check for true values (including checkbox "1")
    if value_str in ['true', '1', 'yes', 'enable', 'on', 'checked']:
        return True
    
    # If we get here, use default
    return default


def parse_comma_separated_list(value):
    """
    Parse a comma-separated string into a list of trimmed values.
    
    Args:
        value: Comma-separated string (e.g., "item1, item2, item3")
    
    Returns:
        List of trimmed strings, or empty list if input is None/empty
    """
    if not value or value.lower() == 'none':
        return []
    
    # Split by comma and remove whitespace from each item
    return [item.strip() for item in value.split(',') if item.strip()]


def create_indicator_signature(indicator_value, collection_uuid):
    """
    Create a unique signature for an indicator within a collection.
    This ensures the same indicator in different collections gets different signatures.
    
    Args:
        indicator_value: The indicator value (IP, domain, etc.)
        collection_uuid: UUID of the collection
    
    Returns:
        MD5 hash string representing the unique signature
    """
    hasher = hashlib.md5()
    
    # Include collection UUID to make signature unique per collection
    if collection_uuid:
        hasher.update(str(collection_uuid).encode('utf-8'))
    
    # Include the indicator value
    if indicator_value:
        hasher.update(str(indicator_value).strip().encode('utf-8'))
    
    return hasher.hexdigest()


def parse_iso_timestamp(iso_date_str, helper, context=""):
    """
    Convert ISO date string to epoch timestamp for Splunk.
    
    Args:
        iso_date_str: ISO format date string (e.g., "2024-01-15T10:30:00Z")
        helper: Splunk helper for logging
        context: Additional context for error messages
    
    Returns:
        Epoch timestamp (float) or None if parsing fails
    """
    if not iso_date_str:
        return None
    
    try:
        # Handle 'Z' timezone indicator
        if iso_date_str.endswith('Z'):
            iso_date_str = iso_date_str[:-1] + "+00:00"
        
        # Parse the datetime
        dt_obj = datetime.fromisoformat(iso_date_str)
        
        # Ensure timezone awareness (default to UTC)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        
        return dt_obj.timestamp()
        
    except Exception as e:
        helper.log_warning(f"Failed to parse timestamp '{iso_date_str}' {context}: {e}")
        return None


# ===== CONFIGURATION FUNCTIONS =====

def load_configuration(helper):
    """
    Load all configuration settings from Splunk.
    
    Args:
        helper: Splunk helper object
    
    Returns:
        Dictionary with all configuration values
    """
    # Debug: List all available global settings
    helper.log_info("=" * 50)
    helper.log_info("ALL AVAILABLE GLOBAL SETTINGS:")
    try:
        # Try to get all settings (this might not work in all Splunk versions)
        import inspect
        for attr in dir(helper):
            if attr.startswith('get_'):
                helper.log_info(f"  Method available: {attr}")
    except:
        pass
    
    # Try to fetch common setting names
    setting_names = [
        "include_recommended",
        "include_recommended_feeds",
        "recommended_feeds",
        "use_recommended",
        "enable_recommended"
    ]
    
    helper.log_info("Checking possible setting names:")
    for name in setting_names:
        try:
            value = helper.get_global_setting(name)
            helper.log_info(f"  {name}: '{value}' (type: {type(value).__name__})")
        except:
            helper.log_info(f"  {name}: [not found]")
    
    # Get raw checkbox value for debugging
    raw_checkbox_value = helper.get_global_setting("include_recommended")
    
    # Log the raw value in detail
    helper.log_info("=" * 50)
    helper.log_info("CHECKBOX DEBUG INFO:")
    helper.log_info(f"  Raw value: '{raw_checkbox_value}'")
    helper.log_info(f"  Type: {type(raw_checkbox_value).__name__}")
    helper.log_info(f"  Is None: {raw_checkbox_value is None}")
    helper.log_info(f"  Is empty string: {raw_checkbox_value == ''}")
    helper.log_info(f"  String representation: '{str(raw_checkbox_value)}'")
    helper.log_info(f"  Length (if string): {len(str(raw_checkbox_value)) if raw_checkbox_value is not None else 'N/A'}")
    
    # Parse the value
    parsed_value = parse_boolean_setting(raw_checkbox_value, default=False)
    helper.log_info(f"  Parsed to boolean: {parsed_value}")
    helper.log_info("=" * 50)
    
    config = {
        'api_key': helper.get_global_setting("socradar_api_key"),
        'include_recommended': parsed_value,
        'custom_collection_ids': parse_comma_separated_list(
            helper.get_global_setting('custom_collection_ids')
        ),
        'custom_collection_names': parse_comma_separated_list(
            helper.get_global_setting('custom_collection_names')
        )
    }
    
    return config


def build_collections_list(config, helper):
    """
    Build the complete list of collections to process based on configuration.
    
    Args:
        config: Configuration dictionary from load_configuration()
        helper: Splunk helper for logging
    
    Returns:
        Dictionary of collections: {name: {"feed_id": uuid}}
    """
    collections = {}
    
    # Add recommended collections if enabled
    if config['include_recommended']:
        collections.update(RECOMMENDED_COLLECTIONS)
        helper.log_info(f"Added {len(RECOMMENDED_COLLECTIONS)} recommended collections")
    
    # Add custom collections
    custom_count = 0
    for idx, feed_id in enumerate(config['custom_collection_ids']):
        # Determine collection name
        if idx < len(config['custom_collection_names']) and config['custom_collection_names'][idx]:
            # Use provided name
            collection_name = config['custom_collection_names'][idx]
        else:
            # Auto-generate name
            collection_name = f"Custom-Feed-{idx+1}-{feed_id[:8]}"
        
        collections[collection_name] = {"feed_id": feed_id}
        custom_count += 1
        
        helper.log_debug(f"Added custom collection: '{collection_name}' -> {feed_id}")
    
    if custom_count > 0:
        helper.log_info(f"Added {custom_count} custom collections")
    
    return collections


# ===== CHECKPOINT FUNCTIONS =====

def load_checkpoint(helper, checkpoint_key):
    """
    Load checkpoint data for a collection.
    
    Args:
        helper: Splunk helper object
        checkpoint_key: Unique key for this checkpoint
    
    Returns:
        Set of processed indicator signatures
    """
    try:
        raw_data = helper.get_check_point(checkpoint_key)
        if raw_data:
            checkpoint_data = json.loads(raw_data)
            signatures = set(checkpoint_data.get("indicator_signatures", []))
            
            helper.log_info(
                f"Loaded checkpoint with {len(signatures)} signatures. "
                f"Last updated: {checkpoint_data.get('last_updated', 'Unknown')}"
            )
            return signatures
            
    except Exception as e:
        helper.log_warning(f"Error loading checkpoint: {e}. Starting fresh.")
    
    return set()


def save_checkpoint(helper, checkpoint_key, signatures, new_count, collection_name, collection_uuid):
    """
    Save updated checkpoint data.
    
    Args:
        helper: Splunk helper object
        checkpoint_key: Unique key for this checkpoint
        signatures: Set of all processed signatures
        new_count: Number of new signatures added this run
        collection_name: Name of the collection
        collection_uuid: UUID of the collection
    
    Returns:
        Boolean indicating success
    """
    try:
        # Convert set to sorted list for JSON serialization
        signature_list = sorted(list(signatures))
        
        # Apply size limit if needed
        if len(signature_list) > CHECKPOINT_MAX_SIZE:
            helper.log_warning(
                f"Checkpoint size ({len(signature_list)}) exceeds limit "
                f"({CHECKPOINT_MAX_SIZE}). Keeping most recent."
            )
            signature_list = signature_list[-CHECKPOINT_MAX_SIZE:]
        
        # Create checkpoint data with metadata
        checkpoint_data = {
            "indicator_signatures": signature_list,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "count_in_checkpoint": len(signature_list),
            "newly_added_this_run": new_count,
            "collection_name": collection_name,
            "collection_uuid": collection_uuid
        }
        
        # Save to Splunk
        helper.save_check_point(checkpoint_key, json.dumps(checkpoint_data))
        
        helper.log_info(
            f"Checkpoint updated: {len(signature_list)} total signatures "
            f"({new_count} new this run)"
        )
        return True
        
    except Exception as e:
        helper.log_error(
            f"Failed to save checkpoint: {e}. "
            f"WARNING: {new_count} events may be duplicated on next run!"
        )
        return False


# ===== API FUNCTIONS =====

def make_api_request(helper, url, collection_name, use_proxy=True):
    """
    Make a single API request with retry logic for rate limiting.
    
    Args:
        helper: Splunk helper object
        url: Complete API URL
        collection_name: Collection name (for logging)
        use_proxy: Whether to use proxy settings (default: True)
    
    Returns:
        Response object or None if all retries failed
    """
    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            # Make the API request
            response = helper.send_http_request(
                url=url,
                method='GET',
                timeout=API_TIMEOUT_SECONDS,
                use_proxy=use_proxy
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                if attempt < len(RATE_LIMIT_DELAYS):
                    delay = RATE_LIMIT_DELAYS[attempt]
                    helper.log_warning(
                        f"{collection_name}: Rate limited (429). "
                        f"Waiting {delay} seconds before retry..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    helper.log_error(f"{collection_name}: Rate limited after all retries")
                    return None
            
            # Raise exception for other HTTP errors
            response.raise_for_status()
            return response
            
        except Exception as e:
            helper.log_error(f"{collection_name}: API request error: {e}")
            return None
    
    return None


def fetch_collection_data(helper, api_key, collection_name, collection_uuid, use_proxy=True):
    """
    Fetch all data for a collection from SOCRadar feed API.
    Note: This API returns the complete feed in a single response.
    
    Args:
        helper: Splunk helper object
        api_key: SOCRadar API key
        collection_name: Name of the collection
        collection_uuid: UUID of the collection
        use_proxy: Whether to use proxy settings (default: True)
    
    Returns:
        List of indicator items
    """
    # Build API URL (no pagination parameters needed)
    api_url = (
        f"{SOCRADAR_API_BASE_URL}/threat/intelligence/feed_list/{collection_uuid}.json"
        f"?key={api_key}&v=2"
    )
    
    # Mask API key for logging
    safe_url = api_url.replace(api_key, "***REDACTED***")
    
    # Wait 5 seconds before making request to SOCRadar
    helper.log_info(f"{collection_name}: Waiting {API_REQUEST_DELAY} seconds before API request...")
    time.sleep(API_REQUEST_DELAY)
    
    helper.log_info(f"{collection_name}: Fetching feed data from {safe_url}")
    
    # Make API request
    response = make_api_request(helper, api_url, collection_name, use_proxy)
    if not response:
        return []
    
    # Parse response
    try:
        items = response.json()
    except Exception as e:
        helper.log_error(f"{collection_name}: Failed to parse JSON response: {e}")
        return []
    
    # Validate response format
    if not isinstance(items, list):
        helper.log_error(
            f"{collection_name}: Expected list response, got {type(items).__name__}"
        )
        return []
    
    # Check response size (for monitoring)
    response_size_mb = len(response.content) / (1024 * 1024)
    helper.log_info(
        f"{collection_name}: Received {len(items)} items "
        f"({response_size_mb:.1f} MB)"
    )
    
    # Filter out invalid items
    valid_items = []
    invalid_count = 0
    
    for item in items:
        if isinstance(item, dict) and item.get("feed"):
            valid_items.append(item)
        else:
            invalid_count += 1
    
    if invalid_count > 0:
        helper.log_warning(
            f"{collection_name}: Filtered out {invalid_count} invalid items"
        )
    
    return valid_items


# ===== EVENT PROCESSING FUNCTIONS =====

def process_and_index_events(helper, ew, items, processed_signatures, collection_name, collection_uuid):
    """
    Process items and index new events to Splunk.
    
    Args:
        helper: Splunk helper object
        ew: Event writer object
        items: List of indicator items from API
        processed_signatures: Set of already processed signatures
        collection_name: Name of the collection
        collection_uuid: UUID of the collection
    
    Returns:
        Tuple of (events_indexed_count, list_of_new_signatures)
    """
    events_indexed = 0
    new_signatures = []
    seen_in_batch = set()  # Track duplicates within this batch
    
    for item in items:
        # Get indicator value
        indicator_value = item.get("feed")
        if not indicator_value:
            continue
        
        # Create signature
        signature = create_indicator_signature(indicator_value, collection_uuid)
        
        # Skip if duplicate within this batch
        if signature in seen_in_batch:
            continue
        seen_in_batch.add(signature)
        
        # Skip if already processed in previous runs
        if signature in processed_signatures:
            continue
        
        # Prepare event data
        event_data = dict(item)  # Copy original data
        event_data["collection_name"] = collection_name
        event_data["collection_uuid"] = collection_uuid
        
        # Get timestamp
        event_time = parse_iso_timestamp(
            item.get("latest_seen_date"),
            helper,
            f"for indicator {indicator_value}"
        )
        
        # Create and write Splunk event
        try:
            splunk_event = helper.new_event(
                data=json.dumps(event_data),
                time=event_time,
                sourcetype=helper.get_sourcetype()
            )
            ew.write_event(splunk_event)
            
            events_indexed += 1
            new_signatures.append(signature)
            
        except Exception as e:
            helper.log_error(f"Failed to index event for '{indicator_value}': {e}")
    
    # Log if we found duplicates within the batch
    duplicates_in_batch = len(items) - len(seen_in_batch)
    if duplicates_in_batch > 0:
        helper.log_warning(
            f"{collection_name}: Found {duplicates_in_batch} duplicates within API response"
        )
    
    return events_indexed, new_signatures


def process_collection(helper, ew, api_key, collection_name, collection_config, checkpoint_prefix, use_proxy=True):
    """
    Process a single collection: fetch data, deduplicate, and index.
    
    Args:
        helper: Splunk helper object
        ew: Event writer object
        api_key: SOCRadar API key
        collection_name: Name of the collection
        collection_config: Configuration dict for the collection
        checkpoint_prefix: Prefix for checkpoint keys
        use_proxy: Whether to use proxy settings (default: True)
    
    Returns:
        Number of events indexed for this collection
    """
    # Get collection UUID
    collection_uuid = collection_config.get("feed_id")
    if not collection_uuid:
        helper.log_warning(f"Skipping collection '{collection_name}': missing feed_id")
        return 0
    
    helper.log_info(f"Collection details: {collection_name} (UUID: {collection_uuid})")
    
    # Load checkpoint
    checkpoint_key = f"{checkpoint_prefix}{collection_uuid}"
    processed_signatures = load_checkpoint(helper, checkpoint_key)
    
    # Fetch data from API
    items = fetch_collection_data(helper, api_key, collection_name, collection_uuid, use_proxy)
    
    if not items:
        helper.log_info(f"{collection_name}: No items retrieved from API")
        return 0
    
    # Process and index new events
    events_indexed, new_signatures = process_and_index_events(
        helper, ew, items, processed_signatures, collection_name, collection_uuid
    )
    
    # Calculate statistics
    unique_in_batch = len(set(create_indicator_signature(item.get("feed", ""), collection_uuid) 
                             for item in items if item.get("feed")))
    already_known = unique_in_batch - events_indexed
    
    helper.log_info(
        f"{collection_name}: Retrieved {len(items)} items from API "
        f"({unique_in_batch} unique), "
        f"{events_indexed} new events indexed, "
        f"{already_known} already in checkpoint"
    )
    
    # Update checkpoint with all signatures (old + new)
    if new_signatures:
        # Add new signatures to the set
        processed_signatures.update(new_signatures)
        
        # Save updated checkpoint
        save_checkpoint(
            helper, checkpoint_key, processed_signatures,
            len(new_signatures), collection_name, collection_uuid
        )
    
    return events_indexed


# ===== MAIN FUNCTIONS =====

def collect_events(helper, ew):
    """
    Main entry point for the Splunk modular input.
    This function is called by Splunk on schedule.
    
    Args:
        helper: Splunk helper object
        ew: Event writer object
    """
    input_name = helper.get_input_stanza_names()
    
    # Log Splunk version for debugging
    try:
        from check_splunk_version import log_version_info
        log_version_info(helper)
    except Exception as e:
        helper.log_debug(f"Could not log Splunk version: {e}")
    
    # Get proxy settings
    proxy_settings = helper.get_proxy()
    use_proxy = False
    
    # Check if proxy is configured and enabled
    if proxy_settings:
        proxy_url = proxy_settings.get('proxy_url')
        proxy_port = proxy_settings.get('proxy_port')
        
        if proxy_url and proxy_port:
            use_proxy = True
            helper.log_info(f"Proxy configured: {proxy_url}:{proxy_port}")
    
    # Start with separator
    helper.log_info("=" * 100)
    helper.log_info(f"SOCRadar integration starting for input: {input_name}")
    
    # Load configuration
    config = load_configuration(helper)
    
    # Validate configuration
    if not config['api_key']:
        helper.log_error("SOCRadar API key not configured. Please set 'socradar_api_key' in global settings.")
        return
    
    # Build list of collections to process
    collections = build_collections_list(config, helper)
    
    if not collections:
        helper.log_info("No collections configured. Enable recommended collections or add custom collections.")
        return
    
    # Calculate and display collection counts
    recommended_count = len(RECOMMENDED_COLLECTIONS) if config['include_recommended'] else 0
    custom_count = len(config['custom_collection_ids'])
    
    helper.log_info(f"Collection Summary:")
    helper.log_info(f"  - Recommended collections: {recommended_count} {'(enabled)' if config['include_recommended'] else '(disabled)'}")
    helper.log_info(f"  - Custom collections: {custom_count}")
    helper.log_info(f"  - Total collections to process: {len(collections)}")
    helper.log_info("=" * 100)
    
    # Process each collection
    checkpoint_prefix = f"{input_name}_socradar_v4_"
    total_events_indexed = 0
    
    for idx, (collection_name, collection_config) in enumerate(collections.items(), 1):
        try:
            # Add separator between collections
            if idx > 1:
                helper.log_info("-" * 100)
            
            helper.log_info(f"[{idx}/{len(collections)}] Processing: {collection_name}")
            
            events_indexed = process_collection(
                helper, ew, config['api_key'], 
                collection_name, collection_config, checkpoint_prefix, use_proxy
            )
            total_events_indexed += events_indexed
            
            # Delay between collections
            if idx < len(collections):  # Don't delay after last collection
                time.sleep(COLLECTION_DELAY)
            
        except Exception as e:
            helper.log_error(f"Error processing collection '{collection_name}': {e}")
            # Continue with next collection
    
    # Final summary
    helper.log_info("=" * 100)
    helper.log_info(
        f"SOCRadar integration complete for input '{input_name}': "
        f"{total_events_indexed} total new events indexed across {len(collections)} collections"
    )
    helper.log_info("=" * 100)


def validate_input(helper, definition):
    """
    Validate input configuration.
    Called by Splunk before creating/updating the input.
    
    Args:
        helper: Splunk helper object
        definition: Input definition
    """
    # Validation is handled by Splunk Add-on Builder
    pass


def get_scheme():
    """
    Define the scheme for this modular input.
    Called by Splunk to understand input parameters.
    
    Returns:
        Scheme object defining the input
    """
    scheme = Scheme("SOCRadar Rich JSON Threat Feed Collector")
    scheme.description = (
        "Collects threat intelligence feeds from SOCRadar API. "
        "Supports both recommended and custom collections with intelligent deduplication. "
        "Configure API key and collections in global settings."
    )
    scheme.use_external_validation = True
    scheme.use_single_instance = False
    
    # Note: All configuration is done via global settings,
    # so no input-specific arguments are needed
    
    return scheme