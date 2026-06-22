# encoding = utf-8
"""
Nexthink NQL Input Helper for Splunk v1.0.0

This module collects data from Nexthink using the NQL API v2.
It handles OAuth2 authentication and queries the execute endpoint.
CIM field mappings are handled at search-time via props.conf (managed by cim_rest_handler.py).

API Endpoints:
- Token URL: https://{instance}-login.{region}.nexthink.cloud/oauth2/default/v1/token
- API URL: https://{instance}.api.{region}.nexthink.cloud/api/v2/nql/execute
"""

import json
import logging
import time

import import_declare_test
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi


ADDON_NAME = "TA-Nexthink"
OAUTH_SCOPE = "service:integration"
DEFAULT_TIMEOUT = 120
SOURCETYPE_PREFIX = "nexthink:"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


def logger_for_input(input_name: str) -> logging.Logger:
    """Get a logger instance for the specified input."""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_credentials(session_key: str, account_name: str, logger: logging.Logger) -> dict:
    """Retrieve account credentials from Splunk's encrypted credential store."""
    logger.debug(f"Retrieving credentials for account: {account_name}")
    
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_nexthink_account",
    )
    account_conf_file = cfm.get_conf("ta_nexthink_account")
    account = account_conf_file.get(account_name)
    
    if not account:
        raise ValueError(f"Account '{account_name}' not found in configuration")
    
    return {
        "instance_name": account.get("instance_name"),
        "region": account.get("region"),
        "client_id": account.get("client_id"),
        "client_secret": account.get("client_secret")
    }


def get_oauth_token(credentials: dict, logger: logging.Logger) -> str:
    """Obtain OAuth2 access token from Nexthink with retry logic."""
    instance = credentials["instance_name"]
    region = credentials["region"]
    
    token_url = f"https://{instance}-login.{region}.nexthink.cloud/oauth2/default/v1/token"
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": credentials["client_id"],
        "client_secret": credentials["client_secret"],
        "scope": OAUTH_SCOPE
    }
    
    logger.info(f"Requesting OAuth token from: {token_url}")
    
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(token_url, data=payload, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise ValueError("No access_token in OAuth response")
            
            logger.info("Successfully obtained OAuth token")
            return access_token
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"OAuth token request failed (attempt {attempt}/{MAX_RETRIES}), "
                             f"retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            if status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"OAuth token request returned {status_code} (attempt {attempt}/{MAX_RETRIES}), "
                             f"retrying in {wait}s")
                time.sleep(wait)
                last_exception = e
            else:
                raise


def execute_nql_query(credentials: dict, token: str, query_id: str, logger: logging.Logger) -> list:
    """Execute an NQL query using the v2 API with retry logic."""
    instance = credentials["instance_name"]
    region = credentials["region"]
    
    api_url = f"https://{instance}.api.{region}.nexthink.cloud/api/v2/nql/execute"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {"queryId": query_id}
    
    logger.info(f"Executing NQL query: {query_id} at {api_url}")
    
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            data = result.get("data", [])
            
            logger.info(f"Query '{query_id}' returned {len(data)} records")
            return data
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"NQL query failed (attempt {attempt}/{MAX_RETRIES}), "
                             f"retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            if status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"NQL query returned {status_code} (attempt {attempt}/{MAX_RETRIES}), "
                             f"retrying in {wait}s")
                time.sleep(wait)
                last_exception = e
            else:
                raise


def validate_input(definition: smi.ValidationDefinition):
    """Validate input configuration before saving."""
    params = definition.parameters
    
    # Validate query_id starts with #
    query_id = params.get("query_id", "")
    if not query_id.startswith("#"):
        raise ValueError("Query ID must start with '#' (e.g., '#splunk_alerts')")
    
    # Validate interval (may be provided as string from UI)
    interval = params.get("interval", "300")
    if interval:
        try:
            interval_int = int(interval)
            if interval_int < 1:
                raise ValueError("Interval must be at least 1 second")
        except (TypeError,):
            raise ValueError("Interval must be a valid number (minimum 1 second)")
        except ValueError:
            raise ValueError("Interval must be a valid number (minimum 1 second)")
    
    # Validate sourcetype_suffix
    sourcetype_suffix = params.get("sourcetype_suffix", "")
    if not sourcetype_suffix:
        raise ValueError("Sourcetype suffix is required")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    """
    Main collection function called by Splunk's modular input framework.
    
    Data is ingested as raw JSON. CIM field mappings are applied at search-time
    via FIELDALIAS definitions in props.conf (managed by cim_rest_handler.py).
    """
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="ta_nexthink_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
            
            # Get input parameters
            account_name = input_item.get("account")
            query_id = input_item.get("query_id")
            index = input_item.get("index", "main")
            
            # Build sourcetype from prefix + suffix
            sourcetype_suffix = input_item.get("sourcetype_suffix", "nql")
            sourcetype = f"{SOURCETYPE_PREFIX}{sourcetype_suffix}"
            
            # CIM info for logging
            enable_cim = input_item.get("enable_cim", "false")
            cim_status = "enabled" if enable_cim.lower() == "true" or enable_cim == "1" else "disabled"
            
            logger.info(f"Processing input '{normalized_input_name}' - Account: {account_name}, "
                       f"Query: {query_id}, Sourcetype: {sourcetype}, CIM: {cim_status}")
            
            # Step 1: Get account credentials
            credentials = get_account_credentials(session_key, account_name, logger)
            
            # Step 2: Get OAuth token
            token = get_oauth_token(credentials, logger)
            
            # Step 3: Execute NQL query
            data = execute_nql_query(credentials, token, query_id, logger)
            
            # Step 4: Write events to Splunk (raw JSON - CIM mapping happens at search time)
            # Do not set time= so Splunk extracts timestamps from the JSON data
            # using TIME_FORMAT defined in props.conf. Falls back to index time
            # if no matching timestamp is found in the event.
            events_written = 0
            
            for record in data:
                # Write raw JSON - field mappings are applied via props.conf at search time
                event = smi.Event(
                    data=json.dumps(record, ensure_ascii=False, default=str),
                    index=index,
                    sourcetype=sourcetype,
                    source=f"nexthink:nql:{query_id}",
                )
                event_writer.write_event(event)
                events_written += 1
            
            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                events_written,
                index,
                account=account_name,
            )
            log.modular_input_end(logger, normalized_input_name)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" - Response: {e.response.text[:500]}"
            logger.error(error_msg)
            log.log_exception(logger, e, "nexthink_api_error", 
                            msg_before=f"Failed to collect data for input '{normalized_input_name}': ")
            
        except Exception as e:
            logger.error(f"Unexpected error processing input '{normalized_input_name}': {e}")
            log.log_exception(logger, e, "collection_error", 
                            msg_before=f"Exception raised for input '{normalized_input_name}': ")
