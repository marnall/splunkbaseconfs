"""Input module for Cyware Threat Intelligence Exchange (CTIX).

This module provides validation and collection logic for the Cyware CTIX threat intelligence
exchange Splunk modular input.
"""

import re
import json
import time
import traceback
from datetime import datetime, timedelta

import requests

from ta_cyware_ctix import logging_helper, proxy_helper
from ta_cyware_ctix.ctix_connector import CTIXConnector
from ta_cyware_ctix.kvstore_helper import KvStoreWriter, get_conf_file
from ta_cyware_ctix.constants import (
    BULK_INDICATOR_BATCH_SIZE,
    API_SAVE_RESULT_SET_PATH,
    API_BULK_LOOKUP_PATH,
    API_INDICATOR_URL_PATH,
    INDICATOR_PAGE_SIZE,
    ENRICHEMENT_PAGE_SIZE,
    USER_AGENT,
    PAGE_NUMBER_KEY_TEMPLATE,
    LAST_RUN_DATE_KEY_TEMPLATE,
    ENRICHMENT_FIELDS,
    KV_BATCH_WRITE_THRESHOLD,
    BULK_INDICATOR_MAX_INDICATOR_LENGTH,
    DEBUG_LOG_SOURCETYPE
)

from solnlib.utils import is_true

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''

logger = logging_helper.get_logger("threat_intelligence_exchange")


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def validate_input_params(helper, input_name, interval):
    """Implement your own validation logic to validate the input stanza configurations."""
    # get account configuration
    message = None
    account = helper.get_arg('account')
    account_details = {}

    if not account:
        message = f"No account selected for this input={input_name}"
        logger.error(message)
        return False, message, None

    try:
        account_details["base_url"] = account.get('base_url')
        account_details["access_id"] = account.get('access_id')
        account_details["secret_key"] = account.get('secret_key')
    except Exception as e:
        message = f"Failed to retrieve account '{account}' for input={input_name}. Error={e}"
        logger.error(message)
        return False, message, None

    if str(account_details["base_url"]).startswith("http://"):
        message = "Insecure Connection is not allowed. Base URL must use HTTPS Protocol for secure connections"
        logger.error(message)
        return False, message, None

    # Validate ctixapi path
    ctixapi_pattern = r"^https://[^/]+(?:/[^/]+)*/ctixapi/?$"
    if not re.match(ctixapi_pattern, str(account_details["base_url"]).rstrip("/") + "/"):
        message = "Base URL must end with /ctixapi. Example: https://your-domain.com/ctixapi"
        logger.error(message)
        return False, message, None

    if int(interval) < 5:
        message = "Interval must be a number (integer) greater than or equal to 5."
        logger.error(message)
        return False, message, None
    return True, message, account_details


def get_page_number(helper, input_name, tag):
    """Retrieve the current page number from the checkpoint or start at 1."""
    page_checkpoint_key = PAGE_NUMBER_KEY_TEMPLATE.format(input_name, tag)
    page_number = helper.get_check_point(page_checkpoint_key)

    if not page_number:
        page_number = 1
        logger.info(f"No checkpoint found for {page_checkpoint_key}, starting from page: {page_number}")
    else:
        log_message = f"Checkpoint found using checkpoint [{page_checkpoint_key} : {page_number}]"
        logger.info(log_message)
    return page_number


def get_iteration_threshold(interval):
    """Calculate iteration threshold."""
    if interval >= 300:
        return 25
    elif interval < 60:
        return 5
    return 10


def get_last_run_date(helper, input_name, tag, debug_logs):
    """
    Get the last run date from checkpoint, or use lookback_days for first run.

    Args:
        helper: The helper object.
        input_name: The name of the input.
        tag: The tag.
        debug_logs: The debug logs list.

    Returns:
        int: The last run date in epoch seconds.
    """
    last_run_date = helper.get_check_point(LAST_RUN_DATE_KEY_TEMPLATE.format(input_name, tag))

    if not last_run_date:
        # No checkpoint exists - check for lookback_days
        logger.info("No checkpoint found. Using lookback_days for first run.")
        lookback_days = helper.get_arg('lookback_days')
        if lookback_days:
            lookback_days = int(lookback_days)
            try:
                last_run_date = int((datetime.now() - timedelta(days=lookback_days)).timestamp())
                log_message = f"First run: Collecting data from past {lookback_days} days"
                logger.info(log_message)
                debug_logs.append(log_message)
            except ValueError as e:
                log_message = f"Invalid lookback_days format '{lookback_days}': {e}. Using 30-day default."
                logger.error(log_message)
                debug_logs.append(log_message)
                last_run_date = int((datetime.now() - timedelta(days=30)).timestamp())
        else:
            logger.info("No checkpoint found and lookback_days is not provided. Using 30-day default.")
            # No lookback_days provided - use 30-day default
            last_run_date = int((datetime.now() - timedelta(days=30)).timestamp())
            log_message = f"No checkpoint or lookback_days found. Using 30-day default: {last_run_date}"
            logger.debug(log_message)
            debug_logs.append(log_message)
    else:
        # Checkpoint exists - use it (ignore lookback_days)
        checkpoint_key = LAST_RUN_DATE_KEY_TEMPLATE.format(input_name, tag)
        log_message = f"Checkpoint found. Using checkpoint [{checkpoint_key} : {last_run_date}]"
        logger.info(log_message)
        debug_logs.append(log_message)

    return last_run_date


def regenerate_auth_params(access_id, secret_key, debug_logs):
    """Regenerate authentication parameters for subsequent API calls."""
    expires = int(time.time() + 25)
    try:
        connector = CTIXConnector("", access_id, secret_key, "")
        signature = connector.signature(expires)
    except Exception as e:
        log_message = (
            f"Fatal Error: Caught an exception while generating Authentication Signature: {e}"
        )
        logger.error(log_message)
        debug_logs.append(log_message)
        raise

    log_message = "Authentication Signature Generated Successfully"
    logger.debug(log_message)
    debug_logs.append(log_message)

    return {
        "Expires": expires,
        "Signature": signature,
    }


def fetch_single_page(url, params, access_id, secret_key, helper, debug_logs, proxy_config, ssl_verify):
    """
    Fetch a single page of data from CTIX API.

    Args:
        url: API endpoint URL
        params: Request parameters
        access_id: API access ID
        secret_key: API secret key
        helper: Splunk helper object
        debug_logs: List to append debug messages
        proxy_config: Proxy configuration

    Returns:
        tuple: (page_data, has_more_pages, next_page_params, debug_info) or (None, False, None, None) on error
    """
    try:
        # Regenerate authentication for each request
        expires = int(time.time() + 25)
        connector = CTIXConnector("", access_id, secret_key, "")
        signature = connector.signature(expires)
        params.update({
            "AccessID": access_id,
            "Expires": expires,
            "Signature": signature
        })

        # Make request
        response = requests.get(
            url, params=params, timeout=180, proxies=proxy_config, verify=ssl_verify, headers={'User-Agent': USER_AGENT}
        )
        status_code = response.status_code

        if status_code != 200:
            log_message = (
                "Fatal Error: Encountered Error while fetching data from CTIX.\n"
                f"Status Code: {status_code}, Message: {response.text}"
            )
            logger.error(log_message)
            debug_logs.append(log_message)
            return None, False, None, None

        # Process response
        res = response.json()
        results = res["results"]
        next_page_val = res.get("next")

        logger.info(
            f"Successfully retrieved {len(results)} results from page {params.get('page', 1)}"
        )

        # Determine if there are more pages
        has_more = next_page_val is not None

        # Prepare params for next page if needed
        next_page_params = None
        if has_more:
            next_page_params = params.copy()
            next_page_params["page"] = params.get("page", 1) + 1

        # Create debug info
        debug_info = {
            "initial_url": url,
            "request_parameters": params.copy(),
            "response_status_code": status_code,
            "length_of_dataset_received": len(results),
            "page_number": params.get('page', 1),
            "last_successfully_polled_url": next_page_val if has_more else url,
        }

        return results, has_more, next_page_params, debug_info

    except Exception as e:
        log_message = f"Fatal Error: Exception while fetching page: {e}\n{traceback.format_exc()}"
        logger.error(log_message)
        debug_logs.append(log_message)
        return None, False, None, None


def extract_base_indicator_fields(indicator, base_url):
    """
    Extract base fields from indicator.

    Returns:
        dict: Base indicator data
    """
    # Extract ALL fields from the indicator - no filtering
    indicator_data = {}
    for key, value in indicator.items():
        indicator_data[key] = value

    # Perform field name conversions for base fields
    if "id" in indicator_data:
        indicator_data["ctix_id"] = indicator_data.pop("id")

    indicator_value = indicator_data.pop("sdo_name", None)
    indicator_data["indicator"] = indicator_value  # Primary indicator value
    indicator_data["_key"] = indicator_value       # KV store key field

    # Add constructed indicator_url if ctix_id exists
    ctix_id = indicator_data.get("ctix_id")
    if ctix_id:
        updated_base_url = base_url.replace("ctixapi", "ctix")
        indicator_url = f"{updated_base_url.rstrip('/')}/{API_INDICATOR_URL_PATH.format(ctix_id)}"
        indicator_data["indicator_url"] = indicator_url

    return indicator_data


def extract_indicator_type_fields(indicator, indicator_data):
    """Extract indicator type and subtype fields."""
    indicator_type = indicator.pop("indicator_type", {})
    indicator_type_value = indicator_type.get("type", None)

    indicator_data["indicator_subtype"] = (
            indicator_type.get("attribute_field", None) if indicator_type_value == "file"
            else indicator_type_value
        )
    indicator_data["indicator_type"] = indicator_type_value


def extract_timestamp_fields(indicator, indicator_data):
    """Extract timestamp-related fields."""
    indicator_data["created_timestamp"] = indicator.pop("ctix_created", None)
    indicator_data["modified_timestamp"] = indicator.pop("ctix_modified", None)
    indicator_data["score"] = indicator.pop("ctix_score", None)
    # Splunk ingest time for _time
    now_epoch = int(time.time())
    indicator_data["splunk_ingest_time"] = now_epoch


def normalize_indicator_type(indicator_type):
    """
    Normalize indicator type for collection naming.

    Args:
        indicator_type: Raw indicator type from API

    Returns:
        str: Normalized indicator type safe for collection names
    """
    if not indicator_type or str(indicator_type).strip() == "":
        return "unknown"

    # Convert to string and normalize
    normalized = str(indicator_type).strip().lower()

    # Remove/replace special characters that aren't allowed in collection names
    # Splunk collection names should be alphanumeric with underscores
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", normalized)  # NOSONAR

    # Remove multiple consecutive underscores
    normalized = re.sub(r"_+", "_", normalized)

    # Remove leading/trailing underscores
    normalized = normalized.strip("_")

    # Ensure it's not empty after normalization
    if not normalized:
        return "unknown"

    return normalized


def transform_indicators(ioc_data_set, base_url, debug_logs):
    """
    Transform raw indicators without distributing to lists.

    Args:
        ioc_data_set: Raw data from API
        base_url: Base URL for indicator links
        debug_logs: List to append debug messages

    Returns:
        list: Transformed indicators ready for enrichment
    """
    indicators = []

    for record in ioc_data_set:
        ctix_bundle_timestamp = record.get("timestamp")
        ctix_tag_list = [tag["name"] for tag in record.get("ctix_tags", []) if tag.get("name")]

        for indicator in record["data"]:
            try:
                if indicator.get("sdo_type", None) != "indicator":
                    continue

                # Transform the indicator
                indicator_data = extract_base_indicator_fields(indicator, base_url)
                extract_indicator_type_fields(indicator, indicator_data)
                extract_timestamp_fields(indicator, indicator_data)

                indicator_data["ctix_bundle_timestamp"] = ctix_bundle_timestamp

                indicator_tags = indicator.pop('tags', [])
                if isinstance(indicator_tags, str):
                    indicator_tags = [indicator_tags] if indicator_tags else []
                elif not isinstance(indicator_tags, list):
                    indicator_tags = []

                indicator_data['cyware_tags'] = list(set(indicator_tags + (ctix_tag_list or [])))

                indicators.append(indicator_data)

            except Exception as e:
                log_message = (
                    "Fatal Error: Encountered Error while parsing data received from "
                    "CTIX for Indicator:{}.\nException Encountered: {}".format(
                        indicator.get("sdo_name", "<indicator could not be extracted>"), e
                    )
                )
                logger.error(log_message)
                debug_logs.append(log_message)

    return indicators


def distribute_indicators_by_type(indicators, indicator_lists):
    """
    Distribute enriched indicators to type-specific lists.

    Args:
        indicators: List of enriched indicators
        indicator_lists: Dictionary to accumulate indicators by type
        debug_logs: List to append debug messages

    Returns:
        int: Number of indicators processed
    """
    processed_count = 0

    for indicator_data in indicators:
        indicator_type = indicator_data.get('indicator_type')
        normalized_type = normalize_indicator_type(indicator_type)

        if normalized_type not in indicator_lists:
            indicator_lists[normalized_type] = []

        indicator_lists[normalized_type].append(indicator_data)
        processed_count += 1

    if processed_count > 0:
        logger.info(f"Distributed {processed_count} indicators into {len(indicator_lists)} lists by type.")
    else:
        logger.info("No indicators to distribute.")

    return processed_count


def process_kv_batches(helper, indicator_lists, failed_types, debug_logs):
    """Process KV writes for types that have reached batch size or need retry."""
    kv_writer = KvStoreWriter(
        session_key=helper.context_meta.get('session_key'),
        app_name=helper.get_app_name()
    )

    types_to_write = []

    for indicator_type, indicators in indicator_lists.items():
        if len(indicators) >= KV_BATCH_WRITE_THRESHOLD or indicator_type in failed_types:
            types_to_write.append(indicator_type)

    for indicator_type in types_to_write:
        success = write_type_to_kv(
            kv_writer, indicator_type, indicator_lists[indicator_type], debug_logs
        )

        logger.info(f"Successfully wrote {len(indicator_lists[indicator_type])} indicators of type '{indicator_type}'")

        if success:
            # Clear the list only on successful write
            indicator_lists[indicator_type] = []
            failed_types.discard(indicator_type)
        else:
            # Keep the data for retry
            failed_types.add(indicator_type)


def write_type_to_kv(kv_writer, indicator_type, indicators, debug_logs):
    """Write indicators of a specific type to KV store."""
    if not indicators:
        return True

    try:
        from ta_cyware_ctix.constants import COLLECTION_BASE_NAME
        collection_name = f"{COLLECTION_BASE_NAME}_{indicator_type}"

        # Write using the KV writer (single type)
        error, error_message = kv_writer.write_single_type_to_kv(
            collection_name, indicators
        )

        if error:
            logger.error(f"Failed to write {len(indicators)} indicators of type '{indicator_type}': {error_message}")
            return False

        return True

    except Exception as e:
        log_message = f"Exception writing indicators of type '{indicator_type}': {e}\n{traceback.format_exc()}"
        logger.error(log_message)
        debug_logs.append(log_message)
        return False


def flush_remaining_data(helper, indicator_lists, debug_logs):
    """Flush all remaining data at the end, regardless of list size."""
    logger.info("Performing final flush of remaining indicator data.")

    kv_writer = KvStoreWriter(
        session_key=helper.context_meta.get('session_key'),
        app_name=helper.get_app_name()
    )

    total_flushed = 0

    for indicator_type, indicators in indicator_lists.items():
        if indicators:
            logger.info(f"Flushing {len(indicators)} remaining indicators of type '{indicator_type}'")

            success = write_type_to_kv(kv_writer, indicator_type, indicators, debug_logs)
            if success:
                total_flushed += len(indicators)
            else:
                logger.error(f"Failed to flush remaining indicators of type '{indicator_type}'")

    logger.info(f"Final flush completed. Total indicators flushed: {total_flushed}")


def _serialize_indicator(indicator):
    """Serialize indicator to JSON format."""
    if "custom_attributes" in indicator and isinstance(indicator["custom_attributes"], (dict, list)):
        indicator["custom_attributes"] = json.dumps(
            indicator["custom_attributes"],
            indent=2,
            ensure_ascii=False
        )

    if "published_collections" in indicator and isinstance(indicator["published_collections"], (dict, list)):
        indicator["published_collections"] = json.dumps(
            indicator["published_collections"],
            indent=2,
            ensure_ascii=False
        )

    if "enrichment_data" in indicator and isinstance(indicator["enrichment_data"], (dict, list)):
        indicator["enrichment_data"] = json.dumps(
            indicator["enrichment_data"],
            indent=2,
            ensure_ascii=False
        )
    return indicator


def _process_enrichment_batch(
    ioc_batch, batch_index, total_batches, base_url, access_id, secret_key, proxy_config, ssl_verify, debug_logs
):
    """Process a single batch of IOC enrichment requests."""
    logger.debug(f"Processing batch {batch_index + 1}/{total_batches} with {len(ioc_batch)} IOC values")

    # Generate authentication signature
    expires = int(time.time() + 25)
    connector = CTIXConnector("", access_id, secret_key, "")
    signature = connector.signature(expires)

    # Prepare enrichment request
    url = f"{base_url.rstrip('/')}/{API_BULK_LOOKUP_PATH}"
    auth_params = {
        "AccessID": access_id,
        "Expires": expires,
        "Signature": signature,
        "fields": ENRICHMENT_FIELDS,
        "page_size": ENRICHEMENT_PAGE_SIZE,
    }
    headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}
    payload = {"value": ioc_batch}

    # Make enrichment request
    response = requests.post(
        url=url,
        params=auth_params,
        headers=headers,
        data=json.dumps(payload),
        proxies=proxy_config,
        verify=ssl_verify,
        timeout=180
    )

    enrichment_map = {}

    if response.status_code == 200:
        enrichment_data = response.json()
        found_iocs = enrichment_data.get("results", [])

        # Use dict comprehension to reduce nesting
        enrichment_map.update({
            ioc["name"]: ioc
            for ioc in found_iocs
            if ioc.get("name")
        })
    else:
        log_message = (
            f"Batch {batch_index + 1}: Enrichment API call failed with status "
            f"{response.status_code}: {response.text}"
        )
        logger.error(log_message)
        debug_logs.append(log_message)

    return enrichment_map


def enrich_indicators(indicators, base_url, access_id, secret_key, helper, debug_logs, proxy_config, ssl_verify):
    """
    Enrich indicators with additional threat intelligence data from CTIX.

    Args:
        indicators: List of formatted indicators
        base_url: CTIX base URL
        access_id: API access ID
        secret_key: API secret key
        helper: Splunk helper object
        debug_logs: List to append debug messages
        proxy_config: Proxy configuration
        ssl_verify: SSL certificate verification setting

    Returns:
        list: List of enriched indicators
    """
    if not indicators:
        return indicators

    logger.debug(f"Enriching {len(indicators)} indicators")

    # Extract IOC values from indicators
    ioc_values = []
    for indicator in indicators:
        ioc_value = indicator.get('indicator')
        if ioc_value and len(ioc_value) < BULK_INDICATOR_MAX_INDICATOR_LENGTH:
            ioc_values.append(ioc_value)

    if not ioc_values:
        logger.debug("No IOC values found for enrichment")
        return indicators

    try:
        # Split IOC values into batches
        ioc_batches = [
            ioc_values[i:i + BULK_INDICATOR_BATCH_SIZE]
            for i in range(0, len(ioc_values), BULK_INDICATOR_BATCH_SIZE)
        ]

        logger.debug(f"Processing {len(ioc_values)} IOC values in {len(ioc_batches)} batch(es)")

        # Aggregate enrichment data from all batches
        enrichment_map = {}

        for batch_index, ioc_batch in enumerate(ioc_batches):
            batch_enrichment = _process_enrichment_batch(
                ioc_batch, batch_index, len(ioc_batches),
                base_url, access_id, secret_key, proxy_config, ssl_verify, debug_logs
            )
            enrichment_map.update(batch_enrichment)

        # Merge enrichment data with indicators (in-place update)
        enriched_count = 0
        for indicator in indicators:
            ioc_value = indicator.get('indicator')
            if ioc_value and ioc_value in enrichment_map:
                indicator.update(enrichment_map[ioc_value])

                # Serialize custom_attributes to JSON string to prevent flattening in kvstore
                indicator = _serialize_indicator(indicator)
                enriched_count += 1

        log_message = f"Successfully enriched {enriched_count} indicators out of {len(indicators)}"
        logger.info(log_message)
        debug_logs.append(log_message)

        return indicators

    except Exception as e:
        log_message = f"Error during enrichment: {e}\n{traceback.format_exc()}"
        logger.error(log_message)
        debug_logs.append(log_message)
        return indicators


def _process_single_page(
    page_data, base_url, access_id, secret_key, helper,
    debug_logs, proxy_config, ssl_verify, enrich_data, ingest_to_index,
    indicator_lists, failed_types, ew
):
    """Process a single page of indicators: transform, enrich, distribute, and write."""
    if not page_data:
        return 0

    # Step 1: Transform only
    transformed_indicators = transform_indicators(page_data, base_url, debug_logs)

    # Step 2: Enrich transformed indicators
    if enrich_data:
        enriched_indicators = enrich_indicators(
            transformed_indicators, base_url, access_id, secret_key, helper, debug_logs, proxy_config, ssl_verify
        )
    else:
        enriched_indicators = transformed_indicators

    # Step 3: Distribute to lists
    page_indicators_count = distribute_indicators_by_type(enriched_indicators, indicator_lists)

    # Write to index immediately if enabled
    if ingest_to_index:
        write_to_index(enriched_indicators, helper, ew, debug_logs)

    # Check and write batches to KV store
    process_kv_batches(helper, indicator_lists, failed_types, debug_logs)

    return page_indicators_count


def write_to_index(indicators, helper, ew, debug_logs):
    """
    Write indicators to Splunk index.

    Args:
        indicators: List of formatted indicators
        helper: Splunk helper object
        ew: Event writer object
        debug_logs: List to append debug messages
    """
    logger.debug(f"Writing {len(indicators)} indicators to index")

    if len(indicators) > 0:
        for i in range(0, len(indicators)):
            indicator_string = json.dumps(indicators[i])
            try:
                event = helper.new_event(
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype(),
                    data=indicator_string
                )
                ew.write_event(event)
            except Exception as e:
                log_message = f"Error writing event to index: {e}"
                logger.error(f"Error writing event to index: {e}\n{traceback.format_exc()}")
                debug_logs.append(log_message)


def collect_events(helper, ew):
    """Collect events from Cyware Threat Intelligence Exchange and write them to Splunk."""
    # get input specific parameters.
    logger.info("Data collection started for input: {}".format(helper.get_input_stanza_names()))
    saved_result_set_tag = helper.get_arg('saved_result_set_tag')
    interval = int(helper.get_arg('interval'))

    # get debug setting from configuration
    logging_conf = get_conf_file(
        file="ta_cyware_ctix_settings",
        stanza="logging",
        session_key=helper.context_meta.get('session_key')
    )
    debug = logging_conf.get('debug', 'false')
    input_name = helper.get_input_stanza_names()

    # Check if index ingestion is enabled
    ingest_to_index = is_true(helper.get_arg('ingest_to_index'))

    # Check if data enrichment is enabled
    enrich_data = is_true(helper.get_arg('enrich_data'))
    logger.info(f"Fetching of enriched data is {enrich_data}")

    # Get proxy configuration
    proxy_config = proxy_helper.get_proxy_config(helper.context_meta.get('session_key'), logger)

    # Get SSL verification setting
    from ta_cyware_ctix import ssl_helper
    ssl_verify = ssl_helper.get_ssl_verify(helper.context_meta.get('session_key'), logger)

    data = {"LOGS": []}
    debug_logs = data["LOGS"]

    # Validate input parameters
    validate, log_message, account_details = validate_input_params(helper, input_name, interval)
    if not validate:
        debug_logs.append(log_message)
        return

    base_url = account_details.get("base_url", "")
    access_id = account_details.get("access_id", "")
    secret_key = account_details.get("secret_key", "")

    total_indicators = 0
    to_timestamp = int(time.time())

    for tag in saved_result_set_tag.split(","):
        logger.info(f"Collection indicator data for tag: {tag}")
        # Get last run date and page number
        last_run_date = get_last_run_date(helper, input_name, tag, debug_logs)
        page_number = get_page_number(helper, input_name, tag)

        # Initialize type-specific indicator lists and failed types tracking
        indicator_lists = {}  # {'domain': [indicators], 'url': [indicators], ...}
        failed_types = set()  # Types that failed KV write and need retry

        # Prepare initial request parameters
        url = f"{base_url.rstrip('/')}/{API_SAVE_RESULT_SET_PATH}"
        current_params = {
            "version": "v3",
            "page_size": INDICATOR_PAGE_SIZE,
            "from_timestamp": last_run_date,
            "page": page_number if page_number else 1,
            "to_timestamp": to_timestamp
        }
        current_params["label_name"] = tag.strip()

        try:
            logger.debug(f"Polling Endpoint: {url}")

            iteration_threshold = get_iteration_threshold(interval)
            pages_processed = 0
            total_indicators_processed = 0
            all_debug_info = []  # Store debug information for all pages

            # Stream through pages one by one
            while pages_processed < iteration_threshold:
                try:
                    # Fetch single page
                    page_data, has_more, next_params, debug_info = fetch_single_page(
                        url, current_params, access_id, secret_key, helper, debug_logs, proxy_config, ssl_verify
                    )

                    if page_data is None:
                        # Error occurred, stop processing
                        break

                    # Store debug information
                    all_debug_info.append(debug_info)

                    pages_processed += 1
                    page_indicators_count = 0

                    # Process the page data
                    page_indicators_count = _process_single_page(
                        page_data, base_url, access_id, secret_key, helper,
                        debug_logs, proxy_config, ssl_verify, enrich_data, ingest_to_index,
                        indicator_lists, failed_types, ew
                    )
                    total_indicators_processed += page_indicators_count
                    debug_info["total_indicators_processed"] = total_indicators_processed

                    log_message = f"Processed page {pages_processed}: {page_indicators_count} indicators"
                    logger.info(log_message)

                    # Check if there are more pages
                    if not has_more:
                        logger.info("No more pages to process.")
                        break

                    # Prepare for next page
                    current_params = next_params
                except Exception as e:
                    logger_message = f"Error processing page: {e}"
                    logger.error(logger_message)
                    debug_logs.append(logger_message)
                    break

            # Final flush of remaining data
            flush_remaining_data(helper, indicator_lists, debug_logs)

            total_indicators += total_indicators_processed
            logger.info(f"Total indicator collected for tag: {tag} : {total_indicators_processed}")
            if pages_processed > 0:
                page_checkpoint_key = PAGE_NUMBER_KEY_TEMPLATE.format(input_name, tag)
                date_checkpoint_key = LAST_RUN_DATE_KEY_TEMPLATE.format(input_name, tag)
                # Data collection completed successfully. So, next interation should start from page 1
                page_checkpoint_value = 1
                date_checkpoint_value = to_timestamp

                logger.info(
                    f"Updating checkpoint for tag: {tag} : [{date_checkpoint_key} : {date_checkpoint_value}, "
                    f"{page_checkpoint_key} : {page_checkpoint_value}]"
                )
                helper.save_check_point(page_checkpoint_key, page_checkpoint_value)
                helper.save_check_point(date_checkpoint_key, date_checkpoint_value)
        except Exception as e:
            error_message = "Error in main processing loop: "
            logger.error(f"{error_message}{e}\n{traceback.format_exc()}")
            debug_logs.append(f"{error_message}{e}")

            page_checkpoint_key = PAGE_NUMBER_KEY_TEMPLATE.format(input_name, tag)
            date_checkpoint_key = LAST_RUN_DATE_KEY_TEMPLATE.format(input_name, tag)
            page_checkpoint_value = current_params.get("page", 1)
            date_checkpoint_value = last_run_date

            logger.info(
                f"Updating checkpoint for tag: {tag} : [{date_checkpoint_key} : {date_checkpoint_value}, "
                f"{page_checkpoint_key} : {page_checkpoint_value}]"
            )
            helper.save_check_point(page_checkpoint_key, page_checkpoint_value)
            helper.save_check_point(date_checkpoint_key, date_checkpoint_value)

        # Prepare final status data
        data.update({
            "input_name": input_name,
            "tag": tag,
            "pages_processed": pages_processed,
            "total_indicators_processed": total_indicators_processed,
            "indicator_types_processed": list(indicator_lists.keys()),
            "failed_types": list(failed_types),
            "debug": debug,
            "enrich_data": enrich_data,
        })

        debug_logs.append(f"Data collection completed. Total indicators: {total_indicators}")

        # Write debug logs if enabled
        try:
            if is_true(debug):
                # Add comprehensive debug information if available
                if all_debug_info:
                    data.update({
                        "page_details": all_debug_info,  # Array of per-page debug info
                        "last_page_processed": all_debug_info[-1] if all_debug_info else None,
                        "total_pages_processed": len(all_debug_info)
                    })
                event = helper.new_event(
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=DEBUG_LOG_SOURCETYPE,
                    data=json.dumps(data)
                )
                ew.write_event(event)
                logger.info("Debug logs written to index successfully")
        except Exception as e:
            logger.error(f"Failed to write debug logs to Splunk. Exception: {e}")

        # Clean up debug info in error path to prevent memory leak
        all_debug_info.clear()
        debug_logs.clear()

    # Final status message
    logger.info(f"Data Ingestion Completed. Total count of indicators: {total_indicators}")
