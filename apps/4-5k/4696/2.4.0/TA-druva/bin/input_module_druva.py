# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone
from requests_oauthlib import OAuth2Session
import splunk.rest as rest

# Cache TTL constant
_CACHE_TTL = 24 * 60 * 60  # 24 hours

# Constants
EVENT_V3_API_URL = "/platform/eventmanagement/v3/events"

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Validate input parameters."""
    interval = float(definition.parameters.get('interval', None))
    if interval < 0 or interval == 0:
        log_error_msg = "Interval must be greater than 0 seconds."
        helper.log_error(log_error_msg)
        raise ValueError(log_error_msg)

def get_checkpoint(helper, stanza_name):
    """Get checkpoint from helper service."""
    return helper.get_check_point(stanza_name)


def get_apihost(cloud_type):
    """Get API host from Druva API."""
    # Handle backward compatibility for old dropdown values
    if cloud_type in ['apis', 'govcloudapis']:
        # Convert old dropdown values to complete URLs
        return f'https://{cloud_type}.druva.com'
    
    # For new complete URLs, return as-is (just remove trailing slash if present)
    return cloud_type.rstrip('/')

def set_checkpoint(helper, stanza_name, state):
    """Set checkpoint in helper service."""
    return helper.save_check_point(stanza_name, state)

def get_proxies(helper):
    """Get proxies from helper service."""
    proxy_conf = helper.service.confs["ta_druva_settings"]["proxy"]
    proxy_enabled = int(proxy_conf["enable_proxy"])
    if not proxy_enabled:
        return
    protocol = proxy_conf["proxy_type"]
    proxy_host = proxy_conf["proxy_host"]
    proxy_port = proxy_conf["proxy_port"]
    
    # Get proxy_username and proxy_password if they exist, otherwise set to None
    proxy_username = None
    proxy_password = None
    
    # Try to get proxy_username and proxy_password if they exist
    try:
        proxy_username = proxy_conf["proxy_username"]
    except (KeyError, AttributeError, TypeError):
        proxy_username = None
    
    try:
        proxy_password = proxy_conf["proxy_password"]
    except (KeyError, AttributeError, TypeError):
        proxy_password = None
    
    proxy_string = protocol + "://"
    if proxy_username and proxy_password:
        proxy_string += proxy_username + ":" + proxy_password + "@"
    proxy_string += proxy_host + ":" + proxy_port
    
    # Set up proxies dictionary - use both http and https for HTTP proxy type
    if protocol == "http":
        proxies = {
            "http": proxy_string,
            "https": proxy_string
        }
    else:
        proxies = {protocol: proxy_string}
    
    return proxies

def get_token(client_id, client_secret, cloud_type, proxies):
    """Get token from Druva API."""
    auth = HTTPBasicAuth(client_id, client_secret)
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    api_host = get_apihost(cloud_type)
    token = oauth.fetch_token(token_url=api_host + '/token', auth=auth, proxies=proxies)
    return token

def get_splunk_version(helper):
    """Get Splunk server version using the helper service object."""
    try:
        # Use the service object from helper which works for both on-prem and cloud
        service = helper.service
        if service:
            # Get version from service.info which contains server information
            version = service.info.get('version', 'unknown')
            helper.log_debug(f"Retrieved Splunk version: {version}")
            return version
        else:
            helper.log_warning("Service object not available in helper")
            return "unknown"
    except Exception as e:
        helper.log_warning(f"Could not get Splunk version: {str(e)}")
        return "unknown"

def get_splunk_instance_type(helper):
    """Get Splunk instance type (cloud, on-prem, etc.) using checkpoint-based cache with TTL."""
    current_time = time.time()
    cache_key = "splunk_instance_type_cache"
    
    try:
        # Try to get cached value from checkpoint
        cached_data = helper.get_check_point(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            cached_value = cached_data.get('value')
            cached_time = cached_data.get('timestamp')
            
            # Check if cache is still valid (within 24 hours)
            if cached_value and cached_time > 0 and (current_time - cached_time) < _CACHE_TTL:
                helper.log_debug(f"Returning cached Splunk instance type: {cached_value}")
                return cached_value
        
        helper.log_debug("Cache miss or expired, fetching fresh data...")
        
        # Get fresh data
        session_key = helper.service.token
        _, content = rest.simpleRequest(
            '/services/server/info',
            getargs={'output_mode': 'json'},
            sessionKey=session_key
        )
        
        data = json.loads(content)
        instance_type = data['entry'][0]['content'].get('instance_type', 'on-prem')
        
        # Cache the result using checkpoint
        cache_data = {
            'value': instance_type,
            'timestamp': current_time
        }
        helper.save_check_point(cache_key, cache_data)
        
        helper.log_debug(f"Fresh Splunk instance type cached: {instance_type}")
        return instance_type
       
    except Exception as e:
        helper.log_warning(f"Could not get Splunk instance type: {str(e)}")
        return "unknown"

def get_app_version():
    """Get the app version from app.manifest."""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Navigate to the app root directory (1 level up from bin/)
        app_root = os.path.join(script_dir, '..')
        manifest_path = os.path.join(app_root, 'app.manifest')
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            return manifest.get('info', {}).get('id', {}).get('version', 'unknown')
    except Exception:
        return "unknown"

def build_headers(access_token, splunk_version, splunk_instance_type, app_version):
    """Build headers with pre-fetched version information."""
    headers = {
        "Authorization": "Bearer " + access_token,
        "xdrv-integration-name": "Splunk",
        "xdrv-integration-version": splunk_version,
        "xdrv-integration-type": splunk_instance_type,
        "xdrv-integration-app-version": app_version
    }
    
    return headers


def fetch_event_v3_data(client_id, client_secret, uri, nextPageToken, query_params, cloud_type, proxies, splunk_version, splunk_instance_type, app_version):
    """Fetch event data from Druva event v3 API with query parameters and pagination."""
    token = get_token(client_id, client_secret, cloud_type, proxies)
    
    # Build headers using the pre-fetched version information
    headers = build_headers(token["access_token"], splunk_version, splunk_instance_type, app_version)
    
    # Build params dictionary with query parameters
    params = query_params.copy() if query_params else {}
    
    if nextPageToken:
        params["pageToken"] = nextPageToken
    
    response = requests.get(uri, params=params, headers=headers, proxies=proxies)
    return response


def get_uda_event_details(source_eventObj):
    """Get UDA event details."""
    ANOMALY_TYPE_MAP = {
        'Deletion': 'deleted files',
        'Creation': 'new files',
        'Modification': 'updated files',
        'Encryption': 'encrypted files',
    }
    event_details = source_eventObj.get("details", {})
    eventObj_details = "Alert:Unusual Data Activity, Alert Description:We have observed Unusual Data Activity in some of the device(s). You can access the backup trends through the device details page. "
    anomaly_type_list = event_details.get("udaType", [])
    anomaly_detection_string = "Large number of "

    for i in range (0, len(anomaly_type_list)):
        anomaly_type = anomaly_type_list[i]
        if i==len(anomaly_type_list)-1:             # last item in list (don't separate by comma)
            anomaly_detection_string += ANOMALY_TYPE_MAP.get(anomaly_type, "")
        else:
            anomaly_detection_string += ANOMALY_TYPE_MAP.get(anomaly_type, "") +", "

    eventObj_details = eventObj_details + "Source:" + event_details.get("resourceName", "") + ", Anomaly detected:" + anomaly_detection_string + ", Affected Snapshot:" + event_details.get("affectedSnapshot", "") + ", Alert Time:" + str(event_details.get("alertTime", ""))
    return eventObj_details


def is_uda_event(source_eventObj):
    """Check if the event is a UDA event."""
    event_details = source_eventObj.get("details", {})
    return event_details.get("udaType", None) is not None


def is_job_event(event_type):
    """Check if the event type is present in allowed job type list"""
    allowed_job_type_list = ["Job Ended", "Job Started", "Job Triggered"]
    return event_type in allowed_job_type_list

def to_epoch_seconds(ts):
    """
    Convert timestamp to epoch seconds.
    Supports:
      - int/float epoch seconds
      - int/float epoch milliseconds (optional safety)
    """
    if ts is None:
        return time.time()

    if isinstance(ts, (int, float)):
        # optional: if ms ever comes
        if ts > 10**12:
            ts = ts / 1000.0
        return float(ts)

    return time.time()

def epoch_to_iso_utc(ts_epoch):
    return datetime.fromtimestamp(ts_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _get_event_metadata(stanza_values):
    """Get common event metadata."""
    return {
        'event_time': time.time(),
        'index': stanza_values.get("index", "main"),
        'source': "druva",
        'sourcetype': "druva:events"
    }

def _process_all_events_page(events, metadata, helper, ew):
    """Process all events from unified API call without filters.
    
    Routes events based on productID, feature, type, and source fields:
    - Realize UDA events: productID 4097 + specific filters
    - Phoenix events: productID 12289 + feature="Job"
    - All other events: productID 8193 and remaining (InSync + Realize Regular)
    """
    event_count = 0
    uda_count = 0
    phoenix_count = 0
    insync_count = 0
    other_count = 0
    
    for event in events:
        product_id = event.get('productID')
        feature = event.get('feature', '')
        event_type = event.get('type', '')
        category = event.get('category', '')
        
        # 1. Realize UDA events (productID 4097 with specific filters)
        if (product_id == 4097 and 
            feature == "Alerts And Notifications" and 
            event_type == "Alert" and 
            is_uda_event(event)):
            event_details = event.get("details", {})
            # UDA events use alertTime from details, fallback to event timeStamp
            uda_timestamp = event_details.get("alertTime") if event_details else event.get("timeStamp")
            occur_epoch = to_epoch_seconds(uda_timestamp)
            realize_event = {}
            realize_event['severity'] = event.get('syslogSeverity')
            realize_event['eventID'] = event.get('id')
            realize_event['clientOS'] = None
            realize_event['clientVersion'] = None
            realize_event['event_type'] = event.get('type')
            realize_event['facility'] = event.get('syslogFacility')
            realize_event['profileID'] = ''
            realize_event['UserEmail'] = ''
            realize_event['ip'] = ''
            realize_event['initiator'] = ''
            realize_event['UserName'] = None
            realize_event['profileName'] = None
            realize_event['eventState'] = None
            realize_event['UserID'] = None
            realize_event['productID'] = product_id
            realize_event['feature'] = feature
            realize_event['category'] = category
            if event_details:
                realize_event["DataSourceID"] = event_details.get("resourceID", None)
                realize_event["DataSourceName"] = event_details.get("resourceName", None)
            realize_event['timeStamp'] = epoch_to_iso_utc(occur_epoch)
            realize_event['eventDetails'] = get_uda_event_details(event)
            splunk_event = helper.new_event(
                data=json.dumps(realize_event),
                time=occur_epoch,
                host=None,
                index=metadata['index'],
                source=metadata['source'],
                sourcetype=metadata['sourcetype'],
                done=True,
                unbroken=True
            )
            ew.write_event(splunk_event)
            uda_count += 1
            event_count += 1
        
        # 2. Phoenix events (productID 12289 + feature="Job")
        elif product_id == 12289 and feature == "Job" and is_job_event(event_type):
            occur_epoch = to_epoch_seconds(event.get("timeStamp"))
            event_details = event.pop("details")
            event["resourceID"] = event_details["resourceID"]
            event["workloadName"] = event_details["workloadName"]
            event["workloadID"] = event_details["workloadID"]
            event["jobID"] = event_details["jobID"]
            event["jobType"] = event_details["jobType"]
            event["jobStatus"] = event_details.get("jobStatus", "")
            event["initiator"] = event_details["initiator"]
            event["description"] = event_details["description"][0].upper() + event_details["description"][1:]
            event["jobCreateTime"] = event_details["jobCreateTime"]
            event["event_type"] = event["type"]
            eid = str(event["jobID"]) + event["workloadID"] + event["type"]
            event["unique_event_id"] = eid
            event["timeStamp"] = epoch_to_iso_utc(occur_epoch)
            splunk_event = helper.new_event(
                data=json.dumps(event),
                time=occur_epoch,
                host=None,
                index=metadata['index'],
                source=metadata['source'],
                sourcetype=metadata['sourcetype'],
                done=True,
                unbroken=True
            )
            ew.write_event(splunk_event)
            phoenix_count += 1
            event_count += 1

        # 3. InSync events (productID 8193)
        elif product_id == 8193:
            occur_epoch = to_epoch_seconds(event.get("timeStamp"))
            event_details = event.get("details", {})
            if event_details:
                event_details["event_type"] = event_details.pop('eventType')
                event_details["productID"] = product_id
                event_details["category"] = category
                event_details["feature"] = feature
                event_details["severity"] = event.get("syslogSeverity")
                event_details["facility"] = event.get("syslogFacility")
                event_details["timeStamp"] = epoch_to_iso_utc(occur_epoch)
                splunk_event = helper.new_event(
                    data=json.dumps(event_details),
                    time=occur_epoch,
                    host=None,
                    index=metadata['index'],
                    source=metadata['source'],
                    sourcetype=metadata['sourcetype'],
                    done=True,
                    unbroken=True
                )
                ew.write_event(splunk_event)
                insync_count += 1
                event_count += 1
        
        # 4. All other events
        else:
            occur_epoch = to_epoch_seconds(event.get("timeStamp"))
            event["event_type"] = event.pop('type')
            event["timeStamp"] = epoch_to_iso_utc(occur_epoch)
            splunk_event = helper.new_event(
                    data=json.dumps(event),
                    time=occur_epoch,
                    host=None,
                    index=metadata['index'],
                    source=metadata['source'],
                    sourcetype=metadata['sourcetype'],
                    done=True,
                    unbroken=True
            )
            ew.write_event(splunk_event)
            other_count += 1
            event_count += 1
    
    helper.log_info(f"Processed events - UDA: {uda_count}, Phoenix: {phoenix_count}, InSync: {insync_count}, Other (Realize Regular): {other_count}")
    return event_count

def _process_paginated_events(helper, ew, api_config, event_config, process_config):
    """Generic function to process paginated events.
    
    Args:
        helper: Splunk helper object
        ew: Event writer object
        api_config: Dict with keys: url, query_params, client_id, client_secret, 
                   cloud_type, proxies, splunk_version, splunk_instance_type, app_version
        event_config: Dict with keys: stanza_name, stanza_values, checkpoint_key
        process_config: Dict with keys: process_func, event_source_name, debug_msg (optional)
    """
    nextpage = True
    while nextpage:
        checkpoint = get_checkpoint(helper, event_config['stanza_name']) or dict()
        if process_config.get('debug_msg'):
            helper.log_info(process_config['debug_msg'].format(checkpoint))
        
        try:
            response = fetch_event_v3_data(
                api_config['client_id'], api_config['client_secret'], api_config['url'],
                checkpoint.get(event_config['checkpoint_key'], ""),
                api_config['query_params'], api_config['cloud_type'], api_config['proxies'],
                api_config['splunk_version'], api_config['splunk_instance_type'], api_config['app_version']
            ).json()
        except Exception as e:
            raise e
        
        event_count = 0
        if response.get("events", ""):
            metadata = _get_event_metadata(event_config['stanza_values'])
            event_count = process_config['process_func'](response.get("events"), metadata, helper, ew)
            helper.log_info(f"Total indexed {process_config['event_source_name']} events into Splunk: {event_count}")
        
        nextPageToken = response.get("nextPageToken")
        prev_token = checkpoint.get(event_config['checkpoint_key'], "")
        nextpage = prev_token != nextPageToken and nextPageToken is not None
        
        checkpoint[event_config['checkpoint_key']] = nextPageToken
        set_checkpoint(helper, event_config['stanza_name'], checkpoint)

def _process_all_events(helper, ew, stanza_name, stanza_values, api_host, client_id, client_secret,
                       cloud_type, proxies, splunk_version, splunk_instance_type, app_version):
    """Process all events from unified API call without filters."""
    helper.log_info("Processing ALL events (unified approach)")
    url = api_host + EVENT_V3_API_URL
    api_config = {
        'url': url,
        'query_params': {},  # No filters - get all events
        'client_id': client_id,
        'client_secret': client_secret,
        'cloud_type': cloud_type,
        'proxies': proxies,
        'splunk_version': splunk_version,
        'splunk_instance_type': splunk_instance_type,
        'app_version': app_version
    }
    event_config = {
        'stanza_name': stanza_name,
        'stanza_values': stanza_values,
        'checkpoint_key': "all_events_nextPageToken"
    }
    process_config = {
        'process_func': _process_all_events_page,
        'event_source_name': "All events"
    }
    _process_paginated_events(helper, ew, api_config, event_config, process_config)

def collect_events(helper, ew):
    """Collect events from Druva API."""
    input_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza()
    client_id = input_stanza[input_name]['global_account']['username']
    client_secret = input_stanza[input_name]['global_account']['password']
    cloud_type = input_stanza[input_name]['global_account'].get('cloud_type', "apis")
    stanza_name = list(input_stanza.keys())[0]
    stanza_values = list(input_stanza.values())[0]
    start_ti = datetime.now()
    
    helper.log_info("Collecting all events from Druva API")
    api_host = get_apihost(cloud_type)
    proxies = get_proxies(helper)

    # Fetch these static values once at the beginning
    splunk_version = get_splunk_version(helper)
    splunk_instance_type = get_splunk_instance_type(helper)
    app_version = get_app_version()

    helper.log_info(f"Splunk version: {splunk_version}, Splunk instance type: {splunk_instance_type}, App version: {app_version}")

    # Use unified approach - get all events in a single API call
    _process_all_events(helper, ew, stanza_name, stanza_values, api_host, client_id, client_secret,
                       cloud_type, proxies, splunk_version, splunk_instance_type, app_version)
    
    helper.log_info("Total processing time (seconds): %f" %
                    (datetime.now() - start_ti).total_seconds())
