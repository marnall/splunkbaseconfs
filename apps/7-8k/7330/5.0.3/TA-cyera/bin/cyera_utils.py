import json
import os
import sys
import uuid
import datetime
import time
import hashlib
import ta_cyera.aob_py3.requests as requests


#Remove lines for debugging if not needed.
# import os
# import sys
# sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
# import splunk_debug as dbg
# dbg.enable_debugging(timeout=25)
#End of debugging

MAX_RETRIES = 10
INITIAL_RETRY_DELAY = 60  # seconds
MAX_RETRY_DELAY = 600  # seconds (10 minutes)

DEFAULT_DAYS_TO_LOOK_BACK = 365

def _enable_os_trust_store(helper):
    """
    Best-effort activation of the host's native certificate trust store
    (Windows certificate store, macOS Security framework, OpenSSL defaults on
    Linux) via the vendored truststore library. Requires Python 3.10+; on
    older Splunk runtimes (Python 3.9 and below) truststore raises ImportError
    and the bundled certifi store is used alone. When active, requests still
    loads certifi alongside it, so the effective trust is the union of both.
    """
    try:
        from ta_cyera.aob_py3 import truststore
        # Process-global injection into the ssl module. Safe here: this is the
        # add-on's own input process, and internal splunkd calls do not perform
        # certificate verification, so only Cyera API calls are affected.
        truststore.inject_into_ssl()
        helper.log_info("OS native certificate trust store enabled (truststore) alongside the bundled store.")
        return True
    except Exception as e:
        helper.log_info(
            f"OS native certificate trust store unavailable on Python {sys.version.split()[0]} ({e}); "
            "using the bundled certificate store."
        )
        return False

def get_ssl_verify(helper):
    """
    Resolve the TLS verification value for Cyera API requests from global settings.

    Precedence: explicit disable > custom CA bundle path > OS native trust
    store (default, Python 3.10+) > bundled certifi store. Returns False when
    verification is explicitly disabled, the path to a custom CA bundle (PEM)
    when one is configured (e.g. behind an SSL-inspection proxy), or True
    otherwise. The resolved value is cached on the helper for the lifetime of
    the run so settings are read and logged once.
    """
    if hasattr(helper, '_cyera_ssl_verify'):
        return helper._cyera_ssl_verify

    verify = True
    disable = str(helper.get_global_setting('disable_ssl_verification') or '').strip().lower()
    ca_path = str(helper.get_global_setting('ca_certs_path') or '').strip()

    if disable in ('1', 'true', 'yes'):
        helper.log_warning(
            "SSL certificate verification is DISABLED via add-on settings. "
            "This is insecure; prefer configuring 'ca_certs_path' instead."
        )
        verify = False
    elif ca_path:
        if not os.path.isfile(ca_path):
            helper.log_error(
                f"Configured CA certificate bundle does not exist or is not readable: {ca_path}. "
                "TLS connections will fail until the path is corrected."
            )
        else:
            helper.log_info(f"Using custom CA certificate bundle for Cyera API TLS verification: {ca_path}")
        verify = ca_path
    else:
        use_os_store = str(helper.get_global_setting('use_os_trust_store') or '1').strip().lower()
        if use_os_store not in ('0', 'false', 'no'):
            _enable_os_trust_store(helper)

    helper._cyera_ssl_verify = verify
    return verify

def validate_input(helper, definition):
    """
    Validate client ID and secret as UUIDs.
    Checks for input-specific cyera_account first, then falls back to global account.
    """
    # Check for input-specific account first (new-style), then global account (legacy)
    account = helper.get_arg('cyera_account') or helper.get_arg('account')
    if not account:
        helper.log_error("Validation error: Account is missing. Set cyera_account or account in input settings.")
        return False

    try:
        # cyera_account may resolve to a dict with name/username/password
        if isinstance(account, dict):
            client_id = account.get('username')
            secret = account.get('password')
        else:
            account_details = helper.get_user_credential_by_id(account)
            if not account_details:
                raise Exception(f"Account '{account}' not found")
            client_id = account_details.get('username')
            secret = account_details.get('password')

        if not client_id or not secret:
            helper.log_error("Validation error: Client ID or Secret is missing in the account.")
            return False

        uuid.UUID(client_id, version=4)
        uuid.UUID(secret, version=4)
        return True
    except ValueError:
        helper.log_error("Validation error: Client ID or Secret is not a valid UUID.")
        return False

def get_jwt(helper, client_id, secret):
    """
    Retrieve JWT token using client ID and secret.
    """
    url = "https://api.cyera.io/v1/login"
    payload = json.dumps({"clientId": client_id, "secret": secret})
    headers = {'Content-Type': 'application/json'}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = helper.send_http_request(url, "POST", headers=headers, payload=payload,
                                                verify=get_ssl_verify(helper), use_proxy=True)
            if response.status_code == 429:
                delay = int(response.headers.get("Retry-After", INITIAL_RETRY_DELAY))
                helper.log_info(f"Rate limited. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            response.raise_for_status()
            json_response = response.json()
            token = json_response.get('token') or json_response.get('jwt')
            if not token:
                helper.log_error("Neither 'token' nor 'jwt' found in the response.")
                return None
            return token
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in {401, 403}:
                helper.log_error(f"Authentication failed with status code {e.response.status_code}. Check client ID and secret.")
                return None
            elif e.response.status_code == 500:
                helper.log_warning(f"Internal Server Error (500) encountered. Retrying in {INITIAL_RETRY_DELAY} seconds...")
                time.sleep(INITIAL_RETRY_DELAY)
            else:
                delay = min(INITIAL_RETRY_DELAY + (60 * attempt), MAX_RETRY_DELAY)
                helper.log_warning(f"Error during JWT retrieval (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                helper.log_info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        except requests.exceptions.RequestException as e:
            delay = min(INITIAL_RETRY_DELAY + (60 * attempt), MAX_RETRY_DELAY)
            helper.log_warning(f"Request error during JWT retrieval (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            helper.log_info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    helper.log_error("Failed to retrieve JWT after maximum retries.")
    return None

def rate_limit_sleep(helper, request_count, start_time, limit_count, limit_seconds):
    """
    Handle rate limiting by sleeping if request count exceeds limit.
    """
    current_time = time.time()
    if request_count >= limit_count and (current_time - start_time) < limit_seconds:
        sleep_duration = limit_seconds - (current_time - start_time)
        helper.log_info(f"Rate limit reached, sleeping for {sleep_duration} seconds.")
        time.sleep(sleep_duration)
        return 0, time.time()
    return request_count, start_time

def get_checkpoint(helper, key):
    """
    Retrieve the checkpoint value for a given key.
    """
    return helper.get_check_point(key)

def save_checkpoint(helper, key, value):
    """
    Save the checkpoint value for a given key.
    """
    helper.save_check_point(key, value)

def process_and_send_data(helper, ew, data, sourcetype):
    """
    Process and send data to Splunk.
    """
    helper.log_info(f"Processing {len(data)} items for sourcetype: {sourcetype}")
    
    if not data:
        helper.log_warning(f"No data to process for sourcetype: {sourcetype}")
        return
    
    # Log a sample item for debugging
    if data and 'events' in sourcetype:
        sample_item = data[0]
        helper.log_debug(f"Sample event item: {json.dumps(sample_item, indent=2)}")
    
    for i, item in enumerate(data):
        try:
            event_data = json.dumps(item)
            event = helper.new_event(data=event_data, index=helper.get_output_index(), sourcetype=sourcetype)
            ew.write_event(event)
            
            # Log progress for large datasets
            if (i + 1) % 100 == 0:
                helper.log_info(f"Processed {i + 1}/{len(data)} items for {sourcetype}")
                
        except Exception as e:
            helper.log_error(f"Error processing item {i} for {sourcetype}: {str(e)}")
            helper.log_debug(f"Problematic item: {json.dumps(item)}")
    
    helper.log_info(f"Completed processing {len(data)} items for {sourcetype}")

def hash_string(s):
    """
    Hash a string using MD5.
    """
    return hashlib.md5(s.encode()).hexdigest()

def handle_request(helper, url, headers, params, rate_limits, rate_state=None):
    """
    Handle HTTP requests with rate limiting and retries.
    
    Args:
        rate_state: Optional dict with 'count' and 'start_time' keys for tracking
                    rate limit state across multiple calls (e.g., paginated requests).
                    If None, a fresh state is created for this call only.
    
    Returns:
        Tuple of (response_json, rate_state) where rate_state tracks cumulative request count.
        Returns (None, rate_state) on failure.
    """
    if rate_state is None:
        rate_state = {"count": 0, "start_time": time.time()}

    helper.log_info(f"Making request to URL: {url}")
    helper.log_info(f"Request parameters: {params}")
    
    for attempt in range(MAX_RETRIES):
        rate_state["count"], rate_state["start_time"] = rate_limit_sleep(
            helper, rate_state["count"], rate_state["start_time"],
            rate_limits["count"], rate_limits.get("seconds", 300)
        )
        try:
            response = helper.send_http_request(url, "GET", headers=headers, parameters=params,
                                                verify=get_ssl_verify(helper), use_proxy=True)
            helper.log_info(f"Response status: {response.status_code}")
            
            # Log more details for debugging
            if 'events' in url:
                helper.log_debug(f"Events endpoint response: {response.text}")
                
                # Parse response to check structure
                try:
                    response_json = response.json()
                    helper.log_info(f"Events response structure: keys={list(response_json.keys())}")
                    if 'results' in response_json:
                        helper.log_info(f"Events results count: {len(response_json['results'])}")
                    else:
                        helper.log_warning(f"No 'results' key in events response. Available keys: {list(response_json.keys())}")
                except Exception as e:
                    helper.log_error(f"Error parsing events response: {str(e)}")
            
            if response.status_code == 429:
                delay = int(response.headers.get("Retry-After", INITIAL_RETRY_DELAY))
                helper.log_info(f"Rate limited. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            
            response.raise_for_status()
            rate_state["count"] += 1
            return response.json(), rate_state
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in {401, 403}:
                helper.log_error(f"Authentication failed with status code {e.response.status_code}. Check JWT token.")
                return None, rate_state
            elif e.response.status_code == 500:
                helper.log_warning(f"Internal Server Error (500) encountered. Retrying in {INITIAL_RETRY_DELAY} seconds...")
                time.sleep(INITIAL_RETRY_DELAY)
            else:
                delay = min(INITIAL_RETRY_DELAY + (60 * attempt), MAX_RETRY_DELAY)
                helper.log_warning(f"Error fetching data (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    helper.log_info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    helper.log_error("Failed to fetch data after maximum retries.")
                    return None, rate_state
        except requests.exceptions.RequestException as e:
            delay = min(INITIAL_RETRY_DELAY + (60 * attempt), MAX_RETRY_DELAY)
            helper.log_warning(f"Request error fetching data (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                helper.log_info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                helper.log_error("Failed to fetch data after maximum retries.")
                return None, rate_state
    return None, rate_state

def get_data(helper, endpoint, jwt_token, limit=None, created_date=None, rate_state=None):
    """
    Fetch data from the API with pagination.
    
    Args:
        rate_state: Optional dict for tracking rate limit state across calls.
                    Enables shared rate tracking when used by the orchestrator.
    """
    endpoint_version_map = {
        "datastores": "v2",
        "issues": "v3",
        "classifications": "v1",
        "events": "v1",
    }
    
    # Set endpoint-specific limits
    endpoint_limits = {
        "datastores": 1000,
        "issues": 100,
        "classifications": 100,
        "events": 100,
    }
    
    # Use endpoint-specific limit if not provided
    if limit is None:
        limit = endpoint_limits.get(endpoint, 100)
    
    rate_limits = {
        "default": {"count": 300, "seconds": 300},
    }
    api_version = endpoint_version_map.get(endpoint, "v1")
    all_results = []
    offset = 0

    # Initialize or reuse rate state for cross-page and cross-endpoint tracking
    if rate_state is None:
        rate_state = {"count": 0, "start_time": time.time()}

    query_param_name = None
    if endpoint == "datastores":
        query_param_name = "createdDate"
    elif endpoint == "issues":
        query_param_name = "updatedDate"
    elif endpoint == "events":
        query_param_name = "eventDateGte"

    while True:
        # Base parameters required for all endpoints
        params = {
            'limit': limit,
            'offset': offset
        }
        
        # Add date parameter if applicable
        if query_param_name and created_date:
            params[query_param_name] = created_date
            
        # Log parameters for debugging
        helper.log_info(f"Using parameters for {endpoint} endpoint: {params}")
            
        url = f"https://api.cyera.io/{api_version}/{endpoint}"
        
        headers = {'Authorization': f'Bearer {jwt_token}', 'Content-Type': 'application/json'}
        endpoint_rate_limit = rate_limits.get(endpoint, rate_limits["default"])

        data, rate_state = handle_request(helper, url, headers, params, endpoint_rate_limit, rate_state=rate_state)
        if data is None:
            save_checkpoint(helper, f"{endpoint}_last_run", datetime.datetime.now().isoformat())
            return all_results

        items = data.get('results', [])
        if not items:
            save_checkpoint(helper, f"{endpoint}_last_run", datetime.datetime.now().isoformat())
            break

        for item in items:
            # For events endpoint, we need to parse the ISO 8601 timestamps for comparison
            if endpoint == "events" and query_param_name:
                item_timestamp = item.get("date")  # Events use "date" field, not eventDateGte
                if item_timestamp:
                    # Parse ISO 8601 timestamps for comparison
                    try:
                        item_datetime = datetime.datetime.fromisoformat(item_timestamp.replace('Z', '+00:00'))
                        created_datetime = datetime.datetime.fromisoformat(created_date.replace('Z', '+00:00')) if created_date else None
                        
                        if not created_datetime or item_datetime > created_datetime:
                            all_results.append(item)
                    except (ValueError, TypeError) as e:
                        helper.log_warning(f"Error parsing timestamp: {e}. Including item by default.")
                        all_results.append(item)
                else:
                    # If no timestamp, include the item
                    all_results.append(item)
            else:
                # Original logic for other endpoints
                item_timestamp = item.get(query_param_name) if query_param_name else None
                if item_timestamp and (not created_date or item_timestamp > created_date):
                    all_results.append(item)
                elif not query_param_name:
                    all_results.append(item)

        offset += limit

    save_checkpoint(helper, f"{endpoint}_last_run", datetime.datetime.now().isoformat())
    return all_results

def collect_events_common(helper, ew, endpoint, sourcetype):
    """
    Common logic for collecting events from various endpoints.
    """
    helper.session_key = helper.context_meta['session_key']

    # First, try to get the account from the input configuration
    cyera_account = helper.get_arg('cyera_account')
    
    if cyera_account:
        # Input-specific account
        helper.log_debug("Using input-specific account")
        account_name = cyera_account.get('name')
        client_id = cyera_account.get('username')
        secret = cyera_account.get('password')
    else:
        # Try to get the global account
        account = helper.get_arg('account')
        helper.log_debug(f"Using global account: {account}")
        
        if not account:
            helper.log_error("Neither input-specific nor global account is set. Please configure the account in the input parameters or add-on setup.")
            return
        
        try:
            account_details = helper.get_user_credential_by_id(account)
            account_name = account
            client_id = account_details.get('username')
            secret = account_details.get('password')
        except Exception as e:
            helper.log_error(f"Error retrieving account details: {str(e)}")
            return

    if not account_name or not client_id or not secret:
        helper.log_error("Account name, client ID, or secret is missing in the account details.")
        return

    helper.log_debug(f"Successfully retrieved account details. Account name: {account_name}, Client ID: {client_id}")

    jwt = get_jwt(helper, client_id, secret)
    if not jwt:
        helper.log_error("Failed to authenticate with API.")
        return

    # Rest of the function remains the same
    days_to_look_back = helper.get_global_setting('days_to_look_back')
    helper.log_debug(f"Retrieved days_to_look_back from global settings: {days_to_look_back}")

    if not days_to_look_back:
        helper.log_warning("The 'days_to_look_back' setting is not set in global additional parameters. Using default value of 365 days.")
        days_to_look_back = DEFAULT_DAYS_TO_LOOK_BACK
    else:
        try:
            days_to_look_back = int(days_to_look_back)
        except ValueError:
            helper.log_error(f"Invalid value for 'days_to_look_back': {days_to_look_back}. Using default value of 365 days.")
            days_to_look_back = DEFAULT_DAYS_TO_LOOK_BACK

    helper.log_info(f"Using days_to_look_back: {days_to_look_back}")

    # Check if retrieve_all_data_every_time is enabled for datastores endpoint
    retrieve_all_data = False
    if endpoint == "datastores":
        retrieve_all_data = helper.get_arg('retrieve_all_data_every_time')
        helper.log_info(f"retrieve_all_data_every_time parameter value: {retrieve_all_data} (type: {type(retrieve_all_data)})")
        # Note: Splunk checkbox returns "0" (string) when unchecked, which is truthy in Python
        if str(retrieve_all_data).strip() == '1':
            helper.log_info("Retrieve all data mode enabled - will fetch all datastores regardless of date")

    last_run_timestamp = get_checkpoint(helper, f"{endpoint}_last_run")
    original_days_to_look_back = get_checkpoint(helper, f"{endpoint}_original_days_to_look_back")

    # Format the date based on the endpoint
    date_format = "%Y-%m-%dT%H:%M:%S.000Z" if endpoint == "events" else "%Y-%m-%d"
    
    # If retrieve_all_data is enabled, set created_date to None to fetch all data
    if retrieve_all_data:
        created_date = None
        helper.log_info("Retrieve all data mode: created_date set to None to fetch all datastores")
    elif not last_run_timestamp:
        created_date = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).strftime(date_format)
        helper.log_info(f"No last run timestamp found. Using created_date: {created_date}")
        save_checkpoint(helper, f"{endpoint}_original_days_to_look_back", days_to_look_back)
    else:
        if original_days_to_look_back != days_to_look_back:
            created_date = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).strftime(date_format)
            helper.log_info(f"Days to look back changed. Using created_date: {created_date}")
            save_checkpoint(helper, f"{endpoint}_original_days_to_look_back", days_to_look_back)
        else:
            try:
                # For events endpoint, we need to keep the ISO format
                if endpoint == "events":
                    created_date = last_run_timestamp
                else:
                    created_date = datetime.datetime.fromisoformat(last_run_timestamp).strftime(date_format)
                helper.log_info(f"Using last run timestamp as created_date: {created_date}")
            except ValueError:
                helper.log_error(f"Invalid last run timestamp format: {last_run_timestamp}. Using days_to_look_back.")
                created_date = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).strftime(date_format)
                helper.log_info(f"Using created_date: {created_date}")

    data = get_data(helper, endpoint, jwt, limit=None, created_date=created_date)
    process_and_send_data(helper, ew, data, sourcetype)
    
    if data:
        new_checkpoint = datetime.datetime.now().isoformat()
        save_checkpoint(helper, f"{endpoint}_last_run", new_checkpoint)
        helper.log_info(f"Checkpoint saved for {endpoint}_last_run: {new_checkpoint}")
    else:
        helper.log_info("No data retrieved, checkpoint not updated.")
