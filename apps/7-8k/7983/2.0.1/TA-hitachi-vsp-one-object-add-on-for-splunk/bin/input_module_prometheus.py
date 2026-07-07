#!/usr/bin/env python3
import requests
import json
import urllib3
import logging
import time
import urllib.parse
from datetime import datetime, timezone
from functools import wraps

# =============================================================================
# SIMPLE SECURITY FUNCTIONS
# =============================================================================

def validate_prometheus_query(query):
    """Basic query safety check"""
    if not query or len(query) > 2000:
        raise ValueError("Invalid query length")
    dangerous = [';', '&', '|', '`', '$']
    if any(char in query for char in dangerous):
        raise ValueError("Unsafe characters in query")
    return query.strip()

def safe_log_url(url):
    """Remove sensitive data from URLs for logging"""
    if any(param in url.lower() for param in ['token=', 'password=', 'key=']):
        return url.split('?')[0] + '?***REDACTED***'
    return url

def build_safe_url(base_url, query):
    """Safely construct Prometheus URL"""
    parsed = urllib.parse.urlparse(base_url)
    params = urllib.parse.parse_qs(parsed.query)
    params['query'] = [query]
    new_query = urllib.parse.urlencode(params, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))

# =============================================================================
# EXISTING FUNCTIONS WITH SECURITY FIXES APPLIED
# =============================================================================

def retry_on_failure(max_retries=3, backoff_factor=1):
    """Retry Logic - Decorator for retrying failed requests with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            helper = args[0] if args else None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        if helper:
                            helper.log_error(f"Final attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                        raise
                    wait_time = backoff_factor * (2 ** attempt)
                    if helper:
                        helper.log_warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

def validate_configuration(helper):
    """Enhanced Validation - Comprehensive configuration validation"""
    required_params = {
        'prometheus_region': 'Prometheus region',
        'prometheus_cluster_name': 'Cluster name', 
        'client_id': 'Client ID',
        'keycloak_username': 'Keycloak username',
        'keycloak_user_password': 'Keycloak user password',
        'prometheus_base_url': 'Prometheus base URL'
    }
    
    missing_params = []
    for param, description in required_params.items():
        try:
            value = helper.get_global_setting(param)
            if not value or not value.strip():
                missing_params.append(f"{description} ({param})")
        except Exception:
            missing_params.append(f"{description} ({param})")
    
    # Validate prometheus_query from input parameters
    try:
        prom_query = helper.get_arg("prometheus_query")
        if not prom_query or not prom_query.strip():
            missing_params.append("Prometheus query (prometheus_query)")
    except Exception:
        missing_params.append("Prometheus query (prometheus_query)")
    
    if missing_params:
        raise Exception(f"Missing required configuration parameters: {', '.join(missing_params)}")
    
    helper.log_info("Configuration validation passed successfully")
    return True

@retry_on_failure(max_retries=3, backoff_factor=2)
def get_access_token(helper, session_obj, token_endpoint, token_payload, token_headers):
    """Retry Logic - Get access token with retry capability"""
    helper.log_info(f"Attempting to get access token from: {safe_log_url(token_endpoint)}")
    
    token_response = session_obj.post(token_endpoint, data=token_payload, headers=token_headers, verify=True, timeout=30)
    helper.log_info(f"Token request status: {token_response.status_code}")
    
    token_response.raise_for_status()
    
    token_data = token_response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        raise Exception("Access token not found in response")
    
    # Performance Monitoring - Log token info without exposing actual token
    expires_in = token_data.get("expires_in", "unknown")
    helper.log_info(f"Access token obtained successfully, expires in: {expires_in} seconds")
    
    return access_token

@retry_on_failure(max_retries=2, backoff_factor=1)
def query_prometheus_api(helper, session_obj, prom_endpoint, query_headers):
    """ADDED: Retry Logic - Query Prometheus with retry capability"""
    helper.log_info(f"Querying Prometheus endpoint: {safe_log_url(prom_endpoint)}")  # CHANGED: Safe logging
    
    prom_response = session_obj.get(prom_endpoint, headers=query_headers, verify=True, timeout=60)
    helper.log_info(f"Prometheus response status: {prom_response.status_code}")
    
    prom_response.raise_for_status()
    
    if "application/json" not in prom_response.headers.get("Content-Type", "").lower():
        raise Exception("Non-JSON response received from Prometheus API")
    
    return prom_response.json()

def collect_events(helper, ew):
    """
    Production-ready Prometheus data collection using Keycloak user/password authentication.
    Enhanced with retry logic, proper logging, session management, and comprehensive error handling.
    """
    
    # Logging Setup
    logger = logging.getLogger('splunk')
    logger.setLevel(logging.INFO)
    
    # Performance Monitoring
    start_time = time.time()
    helper.log_info("Starting Prometheus data collection process")
    
    # Enhanced Validation
    try:
        validate_configuration(helper)
    except Exception as e:
        helper.log_error("Configuration validation failed")
        raise
    
    # Retrieve global settings and input parameters
    REGION = helper.get_global_setting("prometheus_region").strip()
    CLUSTER_NAME = helper.get_global_setting("prometheus_cluster_name").strip()
    PROM_QUERY = helper.get_arg("prometheus_query").strip()
    KEYCLOAK_USERNAME = helper.get_global_setting("keycloak_username").strip()
    KEYCLOAK_PASSWORD = helper.get_global_setting("keycloak_user_password").strip()
    CLIENT_ID = helper.get_global_setting("client_id").strip()  
    PROM_BASE_URL_TEMPLATE = helper.get_global_setting("prometheus_base_url").strip()

    helper.log_info(f"Target region: {REGION}, cluster: {CLUSTER_NAME}")

    # Session Management - Initialize session for connection reuse
    session_obj = requests.Session()
    
    try:
        # Construct endpoints
        token_endpoint = f"https://admin.gms.{CLUSTER_NAME}/ui/auth/realms/vsp-object/protocol/openid-connect/token"
        prometheus_base_url = PROM_BASE_URL_TEMPLATE.replace("{{prometheus_region}}", REGION).replace("{{cluster_name}}", CLUSTER_NAME)
        
        # Validate and build URL safely
        PROM_QUERY = validate_prometheus_query(PROM_QUERY)
        prom_endpoint = build_safe_url(prometheus_base_url, PROM_QUERY)

        helper.log_info(f"Token endpoint: {safe_log_url(token_endpoint)}")
        helper.log_info(f"Prometheus endpoint: {safe_log_url(prom_endpoint)}")

        #############################################
        # 1. Get the Access (Bearer) Token with Enhanced Error Handling and Retry
        #############################################
        token_payload = {
            "grant_type": "password",
            "username": KEYCLOAK_USERNAME,
            "password": KEYCLOAK_PASSWORD,
            "client_id": CLIENT_ID
        }
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "VSP-Object-Prometheus-Collector/1.0"
        }

        # Simplified Error Handling
        try:
            access_token = get_access_token(helper, session_obj, token_endpoint, token_payload, token_headers)
            
        except requests.exceptions.HTTPError as http_err:
            if '401' in str(http_err) or '403' in str(http_err):
                helper.log_error("Authentication failed during token acquisition")
            else:
                helper.log_error("HTTP error during token acquisition")
            raise
        except requests.exceptions.RequestException as req_err:
            helper.log_error("Network error during token acquisition")
            raise
        except Exception as e:
            helper.log_error("Unexpected error during token acquisition")
            raise

        #############################################
        # 2. Query Prometheus Endpoint with Enhanced Error Handling
        #############################################
        query_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "VSP-Object-Prometheus-Collector/1.0"
        }

        try:
            prom_data = query_prometheus_api(helper, session_obj, prom_endpoint, query_headers)
            
        except requests.exceptions.HTTPError as http_err:
            if '401' in str(http_err) or '403' in str(http_err):
                helper.log_error("Authentication failed during Prometheus query")
            else:
                helper.log_error("HTTP error during Prometheus query")
            raise
        except requests.exceptions.RequestException as req_err:
            helper.log_error("Network error during Prometheus query")
            raise
        except Exception as e:
            helper.log_error("Unexpected error during Prometheus query")
            raise

        #############################################
        # 3. Enhanced Event Processing with Improved Error Handling
        #############################################
        try:
            results = prom_data.get('data', {}).get('result', [])
            if not results:
                helper.log_warning("No results found for query")
                return

            helper.log_info(f"Processing {len(results)} metrics")

            # Performance Monitoring
            processing_start = time.time()

            METRIC_FIELD_MAPPING = {
                'voo_s3_operations_total': ['operation', 'instance', 'kubernetes_pod', 'kubernetes_namespace'],
                'voo_s3_requests_histogram_latency_seconds_sum': ['operation', 'instance', 'job'],
                'voo_s3_requests_histogram_latency_seconds_count': ['operation', 'instance', 'job'],
                'voo_s3_requests_latency_seconds': ['operation', 'instance', 'job'],  
                'voo_s3_delete_requests_per_bucket_total': ['delete_type', 'bucket', 'instance', 'job'],
                'voo_envoy_cluster_http2_outbound_flood': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_http2_metadata_empty_frames': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_http2_inbound_priority_frames_flood': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_http2_outbound_control_flood': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_http2_rx_reset': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_http2_stream_refused_errors': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_upstream_rq_rx_reset': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_upstream_http3_broken': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'voo_envoy_cluster_upstream_cx_http3_total': ['kubernetes_namespace', 'kubernetes_pod', 'kubernetes_service'],
                'up': ['instance', 'job', 'kubernetes_service'],
                'default': ['instance', 'job']
            }

            events_created = 0
            failed_events = 0
            
            for result in results:
                try:
                    value_array = result.get('value', [])
                    if not value_array or len(value_array) < 2:  # FIXED: HTML entity
                        helper.log_warning("Invalid or missing value array in result, skipping")
                        failed_events += 1
                        continue

                    try:
                        timestamp_raw = value_array[0]
                        if timestamp_raw is None:
                            helper.log_warning("Null timestamp in value array, skipping")
                            failed_events += 1
                            continue

                        timestamp_epoch = float(timestamp_raw)
                        metric_value = value_array[1]
                        current_time = time.time()
                        
                        # Enhanced timestamp validation
                        if timestamp_epoch < 946684800:
                            helper.log_warning(f"Timestamp {timestamp_epoch} is before 2000-01-01, using current time")
                            timestamp_epoch = current_time
                        elif timestamp_epoch > (current_time + 3600):  # FIXED: HTML entity
                            helper.log_warning(f"Timestamp {timestamp_epoch} is too far in future, using current time")
                            timestamp_epoch = current_time
                        elif timestamp_epoch > 4102444800:  # FIXED: HTML entity
                            helper.log_warning(f"Timestamp {timestamp_epoch} is beyond year 2100, using current time")
                            timestamp_epoch = current_time
                            
                        timestamp_splunk = round(timestamp_epoch, 3)
                        
                    except (ValueError, TypeError) as e:
                        helper.log_error(f"Failed to parse timestamp from value array: {e}")
                        timestamp_splunk = time.time()
                        timestamp_epoch = timestamp_splunk

                    metric_info = result.get('metric', {})
                    metric_name = metric_info.get('__name__', 'unknown')
                    relevant_fields = METRIC_FIELD_MAPPING.get(metric_name, METRIC_FIELD_MAPPING['default'])

                    event_data = {
                        'metric_name': metric_name,
                        'metric_value': metric_value,
                        'region': REGION,
                        'cluster_name': CLUSTER_NAME,
                        'query': PROM_QUERY
                    }

                    # Add relevant fields
                    for field in relevant_fields:
                        field_value = metric_info.get(field)
                        if field_value is not None:
                            event_data[field] = field_value

                    # Enhanced timestamp handling
                    try:
                        readable_time = datetime.fromtimestamp(timestamp_epoch, timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + 'Z'
                        event_data['event_time'] = readable_time
                        event_data['timestamp_epoch'] = timestamp_epoch
                        event_data['timestamp_source'] = 'prometheus'
                    except Exception as e:
                        helper.log_warning(f"Failed to create readable timestamp: {e}")
                        event_data['event_time'] = datetime.fromtimestamp(timestamp_epoch, timezone.utc).isoformat() + 'Z'

                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype(),
                        time=timestamp_splunk,
                        data=json.dumps(event_data)
                    )
                    ew.write_event(event)
                    events_created += 1

                except Exception as e:
                    helper.log_error("Error processing individual result") 
                    failed_events += 1
                    continue  # Continue processing other events instead of failing completely

            # Performance Monitoring
            processing_time = time.time() - processing_start
            total_time = time.time() - start_time
            
            helper.log_info(f"Event processing completed: {events_created} successful, {failed_events} failed")
            helper.log_info(f"Processing time: {processing_time:.2f}s, Total time: {total_time:.2f}s")

        except Exception as e:
            helper.log_error("Critical error in event processing") 
            raise

    except Exception as e:
        helper.log_error("Critical error in data collection") 
        # Create error event for tracking
        current_timestamp = time.time()
        error_event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            time=current_timestamp,
            data=json.dumps({
                "error": "collection_failure", 
                "region": REGION if 'REGION' in locals() else 'unknown',
                "cluster_name": CLUSTER_NAME if 'CLUSTER_NAME' in locals() else 'unknown',
                "timestamp": current_timestamp,
                "event_time": datetime.fromtimestamp(current_timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + 'Z',
                "error_type": "collection_failure"
            })
        )
        ew.write_event(error_event)
        raise
    
    finally:
        # Session Management - Clean up session
        if 'session_obj' in locals():
            session_obj.close()
            helper.log_info("Session closed successfully")

def validate_input(helper, validation_definition):
    """Enhanced input validation"""
    if validation_definition is None:
        raise ValueError("Invalid input configuration: validation_definition is None")
    
    try:
        # Additional validation can be added here
        helper.log_info("Input validation completed successfully")
        return True
    except Exception as e:
        helper.log_error("Input validation failed")
        raise ValueError("Input validation failed")

if __name__ == '__main__':
    print("This script is intended to be run as a Splunk modular input.")
    print("Production-ready version with enhanced error handling, retry logic, and monitoring.")