#!/usr/bin/env python3
import os
import sys
import json
import requests
import xml.etree.ElementTree as ET
import logging
import time
from datetime import datetime

# Add local lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def get_session_key():
    try:
        input_str = sys.stdin.read()
        logger.debug(f"Input received: {input_str}")
        return input_str.strip()
    except Exception as e:
        logger.error(f"Failed to get session key: {e}")
        return None


# Constants
SPLUNKD_PORT = os.environ.get('SPLUNKD_PORT', '8089')
APP_NAME = 'api-data-input'
COLLECTION = 'api-data-input_config'
URL = f'https://localhost:{SPLUNKD_PORT}/servicesNS/nobody/{APP_NAME}/storage/collections/data/{COLLECTION}'
SESSION_KEY = get_session_key()
# Disable SSL warnings for self-signed certs
requests.packages.urllib3.disable_warnings()


def call_api(method, url, data=None, headers=None, suppress_error_log=False, **kwargs):
    """
    Helper to call an API with proper headers and error handling.
    method: 'get', 'post', etc.
    url: full URL to call
    data: dict or JSON string for POST/PUT
    headers: additional headers
    kwargs: passed to requests.request
    """
    if headers is None:
        headers = {}
    headers.setdefault('Content-Type', 'application/json')
    try:
        resp = requests.request(
            method,
            url,
            headers=headers,
            data=json.dumps(data) if data is not None and not isinstance(data, str) else data,
            verify=False,
            **kwargs
        )
        resp.raise_for_status()
        logger.debug(f"response {resp} for {method} {url}")
        if resp.content:
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                try:
                    return resp.json()
                except Exception as json_err:
                    logger.warning(f"Failed to parse JSON response: {json_err}. Raw content: {resp.content}")
                    return resp.content
            else:
                return resp.content
        return None
    except Exception as e:
        msg = f"API {method.upper()} {url} failed: {e}"
        if data is not None:
            msg += f" with data {data}"
        if not suppress_error_log:
            logger.error(msg)
        return None

def call_splunk_api(method, url, session_key=None, data=None, headers=None, suppress_error_log=False, **kwargs):
    """
    Helper to call Splunk API with session key for Authorization header.
    """
    if headers is None:
        headers = {}
    if session_key:
        headers['Authorization'] = f'Splunk {session_key}'
    return call_api(method, url, data=data, headers=headers, suppress_error_log=suppress_error_log, **kwargs)

def parse_headers(header_list):
    """
    Converts a list of header strings in the format '<name>: value'
    to a dictionary suitable for requests.
    """
    headers = {}
    for header in header_list:
        if ':' in header:
            name, value = header.split(':', 1)
            headers[name.strip()] = value.strip()
    return headers

def rename_keys_by_jsonpath(data, key_mappings):
    """
    Renames keys in a JSON object based on JSONPath mappings.
    
    Args:
        data: The JSON object to modify (will be modified in place)
        key_mappings: Dictionary mapping JSONPath expressions to new key names
        
    Returns:
        The modified data with renamed keys
    """
    if not key_mappings:
        return data
    
    try:
        from jsonpath_ng import parse
    except ImportError:
        logger.warning("jsonpath-ng is required for key renaming. Skipping key mappings.")
        return data
    
    import copy
    result = copy.deepcopy(data)
    
    for old_path, new_key_name in key_mappings.items():
        if not new_key_name:
            continue
        
        try:
            jsonpath_expr = parse(old_path)
            matches = list(jsonpath_expr.find(result))
            
            for match in matches:
                # Get the parent object and the old key name
                if match.context is None:
                    continue
                    
                parent = match.context.value
                if not isinstance(parent, dict):
                    continue
                
                # Get the old key from the path
                old_key = str(match.path).split('.')[-1] if hasattr(match.path, '__str__') else None
                if old_key and old_key in parent:
                    # Preserve key order by rebuilding the dictionary
                    items = list(parent.items())
                    new_items = []
                    for k, v in items:
                        if k == old_key:
                            new_items.append((new_key_name, v))
                        else:
                            new_items.append((k, v))
                    
                    # Clear and rebuild parent to preserve order
                    parent.clear()
                    parent.update(new_items)
                    
        except Exception as e:
            logger.warning(f"Failed to rename key at path '{old_path}': {e}")
    
    return result

def get_api_data(config):
    url = config.get('url')
    excluded_paths = config.get('excluded_json_paths', [])
    
    try:
        headers = parse_headers(config.get('http_headers', []))
        data = call_api('get', url, headers=headers)
        if data is None:
            raise Exception('No data returned from API')
        # Apply JSONPath exclusions if any
        if excluded_paths:
            try:
                from jsonpath_ng import parse
            except ImportError:
                logger.error(
                    "jsonpath-ng is required for exclusions. Please install it.")
                return data
            for path in excluded_paths:
                jsonpath_expr = parse(path)
                for match in jsonpath_expr.find(data):
                    context = match.context.value
                    if isinstance(context, dict):
                        context.pop(match.path.fields[0], None)
                    elif isinstance(context, list) and isinstance(match.path.index, int):
                        if 0 <= match.path.index < len(context):
                            context.pop(match.path.index)
            
        return data
    except Exception as e:
        logger.error(f"Failed to fetch or process API data: {e}")
        return None

def write_to_kvstore(app, collection, data):
    logger.info(f"Writing to KV Store collection: {collection} in app: {app}")
    url = f"https://localhost:{SPLUNKD_PORT}/servicesNS/nobody/{app}/storage/collections/data/{collection}"
    
    if isinstance(data, list):
        # Use batch insert for better performance and reliability
        batch_url = f"{url}/batch_save"
        logger.info(f"Batch writing {len(data)} items to KV Store at {batch_url}")
        logger.debug(f"Sample data (first item): {json.dumps(data[0]) if data else 'empty'}")
        result = call_splunk_api('post', batch_url, session_key=SESSION_KEY, data=data)
        if result:
            logger.info(f"Successfully wrote {len(data)} items to KV Store")
        else:
            logger.error(f"Failed to write to KV Store - no result returned")
        return result
    else:
        logger.info(f"Writing single item to KV Store at {url}")
        logger.debug(f"Data: {json.dumps(data)}")
        result = call_splunk_api('post', url, session_key=SESSION_KEY, data=data)
        if result:
            logger.info(f"Successfully wrote 1 item to KV Store")
        else:
            logger.error(f"Failed to write to KV Store - no result returned")
        return result

def empty_kvstore(app, collection):
    logger.info(f"Emptying KV Store collection: {collection}")
    url = f"https://localhost:{SPLUNKD_PORT}/servicesNS/nobody/{app}/storage/collections/data/{collection}/"
    call_splunk_api('delete', url, session_key=SESSION_KEY)
    logger.info(f"Successfully emptied KV Store collection: {collection}")
    return True


def write_to_index(index_name, data):
    """
    Write data to a Splunk index using the HTTP Event Collector (HEC).
    Uses the receivers/simple endpoint which accepts raw data via session key auth.
    """
    logger.info(f"Writing to index: {index_name}")
    url = f"https://localhost:{SPLUNKD_PORT}/services/receivers/simple?index={index_name}&sourcetype=_json"

    try:
        if isinstance(data, list):
            # Send each item as a separate event
            for item in data:
                event_data = json.dumps(item)
                result = call_splunk_api('post', url, session_key=SESSION_KEY, data=event_data)
                if result is None:
                    logger.error(f"Failed to write event to index {index_name}")
        else:
            # Single event
            event_data = json.dumps(data)
            result = call_splunk_api('post', url, session_key=SESSION_KEY, data=event_data)
            if result is None:
                logger.error(f"Failed to write event to index {index_name}")

        logger.info(f"Successfully wrote data to index: {index_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to write to index {index_name}: {e}")
        return False


def get_kvstore_details_from_config(config):
    return config.get('selected_output_location', "/").split('/')


def get_value_at_path(data, path):
    """
    Get value at a JSONPath from an object.
    Supports simple paths like $.products or $.data.items
    """
    if path == '$':
        return data

    # Remove leading $. if present
    path = path.lstrip('$').lstrip('.')
    if not path:
        return data

    parts = path.split('.')
    current = data

    for part in parts:
        if current is None:
            return None
        if not isinstance(current, dict):
            return None
        current = current.get(part)

    return current


def separate_arrays_into_events(data, separate_array_paths):
    """
    Generate separate events from data based on selected array paths.
    Each array item becomes its own event with metadata about its source.
    """
    if not separate_array_paths:
        # No separation configured, return as single item list
        return [data] if not isinstance(data, list) else data

    events = []

    for array_path in separate_array_paths:
        array_data = get_value_at_path(data, array_path)
        if isinstance(array_data, list):
            # Get the field name from the path (e.g., "products" from "$.products")
            field_name = array_path.split('.')[-1] if '.' in array_path else array_path.lstrip('$')

            for item in array_data:
                if isinstance(item, dict):
                    event = {
                        '_source_array': field_name,
                        '_array_path': array_path,
                        **item
                    }
                else:
                    event = {
                        '_source_array': field_name,
                        '_array_path': array_path,
                        'value': item
                    }
                events.append(event)

    # If no events were generated from arrays, return original data
    if not events:
        return [data] if not isinstance(data, list) else data

    logger.info(f"Separated {len(events)} events from {len(separate_array_paths)} array path(s)")
    return events


def should_run_now(cron_expression):
    """
    Check if the current time matches the given cron expression.
    Returns (should_run: bool, error_message: str|None)
    """
    if not cron_expression:
        # No cron expression means always run
        return True, None
    
    try:
        from croniter import croniter
    except ImportError:
        logger.warning("croniter is not installed. Cron expressions will be ignored. Install with: pip install croniter")
        return True, None
    
    try:
        now = datetime.now()
        cron = croniter(cron_expression, now)
        
        # Get the previous scheduled time
        prev_time = cron.get_prev(datetime)
        
        # Check if we're within a reasonable window (1 minute) of a scheduled run
        # This accounts for the fact that the script might not run at the exact second
        time_diff = (now - prev_time).total_seconds()
        
        # If the previous scheduled time was within the last 90 seconds, we should run
        should_run = 0 <= time_diff <= 90
        
        if should_run:
            logger.info(f"Cron expression '{cron_expression}' matched. Last scheduled: {prev_time}, Current: {now}")
        else:
            logger.debug(f"Cron expression '{cron_expression}' did not match. Last scheduled: {prev_time}, Current: {now}, Diff: {time_diff}s")
        
        return should_run, None
        
    except Exception as e:
        error_msg = f"Invalid cron expression '{cron_expression}': {e}"
        return False, error_msg


def main():
    if not SESSION_KEY:
        logger.error("No session key found, exiting.")
        return
    try:
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            suppress_error_log = attempt <= 2
            app_config = call_splunk_api('get', URL, session_key=SESSION_KEY, suppress_error_log=suppress_error_log)
            if app_config is not None:
                break
            if attempt < max_retries:
                logger.info(f"App config fetch failed (attempt {attempt}), possibly because KV Store hasn't started yet. Retrying in 10 seconds...")
                time.sleep(10)
        else:
            logger.error(f"Failed to fetch app config after {max_retries} attempts.")
            return
        logger.debug(f"App config: {json.dumps(app_config)}")
        for item in app_config:
            # Check if input is enabled
            if not item.get('enabled', False):
                logger.info(f"Skipping disabled input: {item.get('name')}")
                continue
            
            # Check if current time matches cron expression
            cron_expression = item.get('cron_expression')
            should_run, cron_error = should_run_now(cron_expression)
            
            if cron_error:
                logger.error(f"Skipping input '{item.get('name')}' due to invalid cron expression: {cron_error}")
                continue
            
            if not should_run:
                logger.debug(f"Skipping input '{item.get('name')}' - not scheduled to run now (cron: {cron_expression})")
                continue
            
            input_type = item.get('input_type')
            output_name = item.get('selected_output_location')
            if not output_name:
                logger.info(f"Skipping item with no output location: {item}")
                continue
            if input_type == 'kvstore':
                logger.info(f"Processing KV Store input: {item.get('name')}")
                api_data = get_api_data(item)
                if api_data is None:
                    logger.error(f"Failed to fetch API data for kvstore input: {item.get('name')}")
                    continue
                logger.info(f"Fetched API data, type: {type(api_data)}, length: {len(api_data) if isinstance(api_data, (list, dict)) else 'N/A'}")
                # Apply array separation if configured
                separate_paths = item.get('separate_array_paths', [])
                if separate_paths:
                    logger.info(f"Applying array separation for paths: {separate_paths}")
                    api_data = separate_arrays_into_events(api_data, separate_paths)
                    logger.info(f"After separation: {len(api_data)} events")
                
                # Apply key renaming to each event after separation
                key_mappings = item.get('key_mappings', {})
                if key_mappings:
                    logger.info(f"Applying key mappings: {key_mappings}")
                    if isinstance(api_data, list):
                        api_data = [rename_keys_by_jsonpath(event, key_mappings) for event in api_data]
                    else:
                        api_data = rename_keys_by_jsonpath(api_data, key_mappings)
                
                app, collection = get_kvstore_details_from_config(item)
                logger.info(f"Target: app={app}, collection={collection}")
                mode = item.get('mode', 'overwrite')
                logger.info(f"Mode: {mode}")
                if mode == 'overwrite':
                    empty_kvstore(app, collection)
                result = write_to_kvstore(app, collection, api_data)
                if result:
                    event_count = len(api_data) if isinstance(api_data, list) else 1
                    logger.info(f"{event_count} events ingested to KV Store {app}/{collection}")
            elif input_type == 'index':
                api_data = get_api_data(item)
                if api_data is None:
                    logger.error(f"Failed to fetch API data for index input: {item.get('name')}")
                    continue
                # Apply array separation if configured
                separate_paths = item.get('separate_array_paths', [])
                if separate_paths:
                    api_data = separate_arrays_into_events(api_data, separate_paths)
                
                # Apply key renaming to each event after separation
                key_mappings = item.get('key_mappings', {})
                if key_mappings:
                    logger.info(f"Applying key mappings: {key_mappings}")
                    if isinstance(api_data, list):
                        api_data = [rename_keys_by_jsonpath(event, key_mappings) for event in api_data]
                    else:
                        api_data = rename_keys_by_jsonpath(api_data, key_mappings)
                
                index_name = output_name  # For index, selected_output_location is just the index name
                result = write_to_index(index_name, api_data)
                if result:
                    event_count = len(api_data) if isinstance(api_data, list) else 1
                    logger.info(f"{event_count} events ingested to index {index_name}")
    except Exception as e:
        logger.error(f"ERROR: {e}")

if __name__ == '__main__':
    main()
