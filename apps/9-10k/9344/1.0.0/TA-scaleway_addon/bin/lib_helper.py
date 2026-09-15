import calendar
import datetime
import json
import logging
import time
from typing import Optional

import requests
from solnlib import conf_manager, credentials, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from configs import (
    ACCOUNT_CONF_FILE_NAME,
    ADDON_NAME,
    API_BASE_URL,
    API_CALL_DELAY_WINDOW_IN_SECONDS,
    API_CALL_MAX_RETRIES,
    API_CALL_PARAMS,
    API_CALL_RETRY_BACKOFF_BASE_IN_SECONDS,
    API_CALL_TIMEOUT_IN_SECONDS,
    API_RESPONSE_LIST_NAME_ALTERNATIVES,
    API_RESPONSE_NEXT_PAGE_TOKEN_FIELD,
    COLLECTION_NAME,
    DEFAULT_CHECKPOINT_TIME,
    LOG_DEBUG_TAG,
    LOG_ERROR_TAG,
    SETTINGS_CONF_FILE_NAME,
    USER_AGENT,
)

# ==============================================================================
# UTILITIES
# ==============================================================================


def _get_log_level(session_key: str, logger: logging.Logger) -> str:
    return str(
        conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=ADDON_NAME,
            conf_name=SETTINGS_CONF_FILE_NAME,
        )
    )


def _reconstruct_endpoint(endpoint: str, region: Optional[str], zone: Optional[str]) -> str:
    return endpoint.replace("{region}", region or "").replace("{zone}", zone or "")


def _get_conf_manager(session_key: str, conf_file_name: str) -> conf_manager.ConfManager:
    return conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{conf_file_name}",
    )


def _get_credential_manager(session_key: str, conf_file_name: str) -> credentials.CredentialManager:
    return credentials.CredentialManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{conf_file_name}",
    )


def _get_checkpointer(session_key: str, collection_name: str) -> checkpointer.KVStoreCheckpointer:
    return checkpointer.KVStoreCheckpointer(
        collection_name,
        session_key,
        ADDON_NAME,
    )


def _build_proxies(proxy_settings: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
    if not proxy_settings or proxy_settings.get("proxy_enabled") != "1":
        return None

    proxy_type = proxy_settings.get("proxy_type")
    host = proxy_settings.get("proxy_host")
    port = proxy_settings.get("proxy_port")
    user = proxy_settings.get("proxy_username")
    password = proxy_settings.get("proxy_password")
    rdns = proxy_settings.get("proxy_rdns")

    if proxy_type == "socks5":
        scheme = "socks5h" if rdns == "1" else "socks5"
    elif proxy_type == "socks4":
        scheme = "socks4a" if rdns == "1" else "socks4"
        user = None
        password = None
    else:
        scheme = "http"

    auth_part = f"{user}:{password}@" if user and password else ""
    proxy_url = f"{scheme}://{auth_part}{host}:{port}"

    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def _convert_time_from_epoch_to_string(epoch: int) -> str:
    precision = 9 if epoch >= 10**18 else 6
    seconds, fraction = divmod(epoch, 10**precision)
    return f"{time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(seconds))}.{fraction:0{precision}d}Z"


def _convert_time_from_string_to_epoch(timestamp: str) -> int:
    date_part, fraction = timestamp.rstrip("Z").split(".")
    precision = len(fraction)
    return int(calendar.timegm(time.strptime(date_part, "%Y-%m-%dT%H:%M:%S")) * (10**precision) + int(fraction))


def validate_input(definition: smi.ValidationDefinition) -> None:
    params = definition.parameters
    start_date = (params.get("start_date") or "").strip()

    if not start_date:
        return

    try:
        start_date_parsed = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError as err:
        raise ValueError(f"Start date '{start_date}' is not in the correct format (YYYY-MM-DD).") from err

    if start_date_parsed > datetime.date.today():
        raise ValueError(f"Start date '{start_date}' cannot be in the future.")


# ==============================================================================
# API HELPERS
# ==============================================================================


def _get_component_from_endpoint(endpoint: str) -> str:
    return endpoint.lstrip("/").split("/", 1)[0]


def _initialize_page_selector(endpoint: str) -> Optional[str]:
    component = _get_component_from_endpoint(endpoint)
    page_keyword = API_CALL_PARAMS[component]["page_keyword"]
    if page_keyword == "page":
        return "1"
    return None


def _get_query_parameters(
    endpoint: str,
    organization_id: str,
    checkpoint: Optional[str],
    project_id: Optional[str],
    product_name: Optional[str],
) -> dict:
    component = _get_component_from_endpoint(endpoint)
    reference_params = API_CALL_PARAMS[component]
    initial_page = _initialize_page_selector(endpoint)
    timerange_end = (
        _convert_time_from_epoch_to_string((int(time.time()) - API_CALL_DELAY_WINDOW_IN_SECONDS) * 1_000_000_000)
        if checkpoint
        else None
    )

    query_parameters = {
        reference_params["organization_keyword"]: organization_id,
        reference_params["order_keyword"]: reference_params["order_value"],
        reference_params["timerange_start_keyword"]: checkpoint,
        reference_params["timerange_end_keyword"]: timerange_end,
        "project_id": project_id,
        "product_name": product_name,
        reference_params["page_keyword"]: initial_page,
        reference_params["page_size_keyword"]: reference_params["page_size_value"],
    }
    return query_parameters


def _get_api_keywords(endpoint: str) -> tuple[str, str, str, str]:
    component = _get_component_from_endpoint(endpoint)
    timerange_start_keyword = API_CALL_PARAMS[component]["timerange_start_keyword"]
    timerange_end_keyword = API_CALL_PARAMS[component]["timerange_end_keyword"]
    page_keyword = API_CALL_PARAMS[component]["page_keyword"]
    timestamp_keyword = API_CALL_PARAMS[component]["timestamp_keyword"]
    return timerange_start_keyword, timerange_end_keyword, page_keyword, timestamp_keyword


def _get_api_results_from_data(data: dict, logger: logging.Logger) -> list[dict]:
    for response_name_field in API_RESPONSE_LIST_NAME_ALTERNATIVES:
        if response_name_field in data:
            results: list[dict] = data[response_name_field]
            return results

    logger.debug(
        f"{LOG_DEBUG_TAG} No matching API response field from {API_RESPONSE_LIST_NAME_ALTERNATIVES} found in payload keys: {list(data.keys())}. Returning empty results."
    )
    return []


def _update_last_checkpoint(
    events: list[dict],
    timestamp_keyword: str,
    last_checkpoint: Optional[str],
    timerange_end: Optional[str],
    logger: logging.Logger,
) -> Optional[str]:
    if events and last_checkpoint:
        latest_event = events[-1]
        raw_timestamp = latest_event.get(timestamp_keyword)

        if not raw_timestamp:
            logger.error(f"{LOG_ERROR_TAG} Latest event is missing expected timestamp keyword '{timestamp_keyword}'")
            return last_checkpoint

        last_checkpoint = _convert_time_from_epoch_to_string(_convert_time_from_string_to_epoch(raw_timestamp) + 1)
        logger.debug(
            f"{LOG_DEBUG_TAG} New events received, updating checkpoint to last event timestamp: {last_checkpoint}"
        )
    elif last_checkpoint:
        logger.debug(f"{LOG_DEBUG_TAG} No new events received. Preserving existing checkpoint {last_checkpoint}.")
    return last_checkpoint


def _update_page_selector(
    data: dict, current_page_selector: Optional[str], len_results_current_page: int, logger: logging.Logger
) -> Optional[str]:
    next_page_token: Optional[str] = data.get(API_RESPONSE_NEXT_PAGE_TOKEN_FIELD, None)
    if next_page_token is not None:
        logger.debug(f"{LOG_DEBUG_TAG} API returned next_page_token; continuing with token-based pagination.")
        return next_page_token

    if current_page_selector is None:
        logger.debug(f"{LOG_DEBUG_TAG} API returned single page with token-based pagination; pagination finished.")
        return None

    try:
        current_page_int = int(current_page_selector)
    except ValueError:
        logger.debug(
            f"{LOG_DEBUG_TAG} API returned no next_page_token with token-based pagination; pagination finished."
        )
        return None

    if len_results_current_page == 0:
        logger.debug(f"{LOG_DEBUG_TAG} Current page returned no results; stopping numeric pagination.")
        return None

    logger.debug(
        f"{LOG_DEBUG_TAG} Advancing numeric pagination from page {current_page_int} to page {current_page_int + 1}."
    )
    return str(current_page_int + 1)


# ==============================================================================
# MAJOR METHODS
# ==============================================================================


def logger_for_input(input_name: Optional[str] = None) -> logging.Logger:
    logger_name = f"{ADDON_NAME.lower()}_{input_name}" if input_name else f"{ADDON_NAME.lower()}"
    logger: logging.Logger = log.Logs().get_logger(logger_name)
    return logger


def get_account_settings(
    session_key: str, account_name: str, logger: logging.Logger
) -> tuple[Optional[str], Optional[str]]:

    organization_id = None
    scw_secret_key = None

    try:
        cfm = _get_conf_manager(session_key, ACCOUNT_CONF_FILE_NAME)
        account_conf_file = cfm.get_conf(ACCOUNT_CONF_FILE_NAME)
        account_data = account_conf_file.get(account_name)
        organization_id = account_data.get("organization_id") if account_data else None
        logger.debug(
            f"{LOG_DEBUG_TAG} Retrieved account settings for account: {account_name}, organization_id: {organization_id}"
        )

        cm = _get_credential_manager(session_key, ACCOUNT_CONF_FILE_NAME)
        credential_data = cm.get_password(account_name)
        scw_secret_key = json.loads(credential_data).get("scw_secret_key") if credential_data else None
        logger.debug(f"{LOG_DEBUG_TAG} Retrieved secret key for account: {account_name}")
    except Exception as err:
        organization_id = organization_id or None
        scw_secret_key = scw_secret_key or None
        logger.error(f"{LOG_ERROR_TAG} Failed to retrieve account settings for {account_name}, error: {err}")

    return organization_id, scw_secret_key


def get_proxy_settings(session_key: str, logger: logging.Logger) -> Optional[dict[str, str]]:

    proxy_settings: Optional[dict[str, str]] = None

    try:
        cfm = _get_conf_manager(session_key, SETTINGS_CONF_FILE_NAME)
        settings_conf_file = cfm.get_conf(SETTINGS_CONF_FILE_NAME)
        proxy_settings = settings_conf_file.get("proxy")
        logger.debug(f"{LOG_DEBUG_TAG} Retrieved proxy settings")

        if not (proxy_settings and proxy_settings.get("proxy_username") and proxy_settings.get("proxy_password")):
            return proxy_settings

        cm = _get_credential_manager(session_key, SETTINGS_CONF_FILE_NAME)
        credential_data = cm.get_password("proxy")
        if credential_data:
            proxy_settings["proxy_password"] = json.loads(credential_data).get("proxy_password")
        logger.debug(f"{LOG_DEBUG_TAG} Retrieved proxy credentials")
    except Exception as err:
        proxy_settings = proxy_settings or None
        logger.error(f"{LOG_ERROR_TAG} Failed to retrieve proxy settings, error: {err}")

    return proxy_settings


def load_checkpoint(
    collection_name: str, checkpoint_key: str, start_date: str, session_key: str, logger: logging.Logger
) -> Optional[str]:

    if not start_date:
        logger.debug(f"{LOG_DEBUG_TAG} No checkpoint required for key: {checkpoint_key}")
        return None

    checkpoint = f"{start_date}T{DEFAULT_CHECKPOINT_TIME}Z"

    try:
        checkpointer = _get_checkpointer(session_key, collection_name)
        checkpoint_data = checkpointer.get(checkpoint_key)

        if checkpoint_data and "timestamp" in checkpoint_data:
            last_timestamp = checkpoint_data["timestamp"]
            checkpoint = _convert_time_from_epoch_to_string(last_timestamp)

        logger.debug(f"{LOG_DEBUG_TAG} Loaded checkpoint for key: {checkpoint_key}, checkpoint: {checkpoint}")
    except Exception as err:
        logger.error(f"{LOG_ERROR_TAG} Failed to load checkpoint for key: {checkpoint_key}, error: {err}")

    return checkpoint


def get_data_from_api(
    endpoint: str,
    scw_secret_key: str,
    query_parameters: dict[str, str],
    proxy_settings: Optional[dict[str, str]],
    logger: logging.Logger,
) -> tuple[list[dict], Optional[str]]:

    results = []
    timerange_start_keyword, timerange_end_keyword, page_keyword, timestamp_keyword = _get_api_keywords(endpoint)
    last_checkpoint = query_parameters.get(timerange_start_keyword, None)
    timerange_end = query_parameters.get(timerange_end_keyword, None)
    page_selector = query_parameters.get(page_keyword, None)

    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "X-Auth-Token": scw_secret_key,
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    params = {key: value for key, value in query_parameters.items() if value}
    proxies = _build_proxies(proxy_settings)
    logger.debug(f"{LOG_DEBUG_TAG} Making API call to {url} with params: {params} and proxies: {proxies}")

    try:
        while True:
            number_of_tries = 0
            while number_of_tries < API_CALL_MAX_RETRIES:
                try:
                    response = requests.get(
                        url, headers=headers, params=params, proxies=proxies, timeout=API_CALL_TIMEOUT_IN_SECONDS
                    )
                    response.raise_for_status()
                    break

                except Exception as err:
                    number_of_tries += 1
                    logger.error(
                        f"{LOG_ERROR_TAG} API call failed for endpoint: {endpoint}, attempt {number_of_tries}/{API_CALL_MAX_RETRIES}, error: {err}"
                    )
                    if number_of_tries >= API_CALL_MAX_RETRIES:
                        raise

                    time.sleep(API_CALL_RETRY_BACKOFF_BASE_IN_SECONDS ** (number_of_tries - 1))

            data = response.json()
            results_current_page = _get_api_results_from_data(data, logger)
            results += results_current_page
            logger.debug(f"{LOG_DEBUG_TAG} API response received with {len(results_current_page)} results")

            last_checkpoint = _update_last_checkpoint(
                results, timestamp_keyword, last_checkpoint, timerange_end, logger
            )

            page_selector = _update_page_selector(data, page_selector, len(results_current_page), logger)

            if page_selector is not None:
                params[page_keyword] = page_selector
            else:
                logger.debug(f"{LOG_DEBUG_TAG} No more pages to fetch, exiting API call loop")
                break

    except Exception as err:
        logger.error(f"{LOG_ERROR_TAG} API call failed for endpoint: {endpoint}, error: {err}")

    return results, last_checkpoint


def write_events(
    index: str,
    sourcetype: str,
    events: list[dict],
    input_name: str,
    account_name: str,
    event_writer: smi.EventWriter,
    logger: logging.Logger,
) -> None:

    for event in events:
        try:
            event_writer.write_event(
                smi.Event(
                    data=json.dumps(event, ensure_ascii=False, default=str),
                    index=index,
                    sourcetype=sourcetype,
                )
            )
        except Exception as err:
            logger.error(f"{LOG_ERROR_TAG} Failed to write event for input: {input_name}, error: {err}")
    log.events_ingested(
        logger,
        input_name,
        sourcetype,
        len(events),
        index,
        account=account_name,
    )


def save_checkpoint(
    new_checkpoint: Optional[str], collection_name: str, checkpoint_key: str, session_key: str, logger: logging.Logger
) -> None:

    if not new_checkpoint:
        logger.debug(f"{LOG_DEBUG_TAG} No checkpoint required to save for key: {checkpoint_key}")
        return

    try:
        checkpointer = _get_checkpointer(session_key, collection_name)
        checkpointer.update(checkpoint_key, {"timestamp": _convert_time_from_string_to_epoch(new_checkpoint)})
        logger.debug(f"{LOG_DEBUG_TAG} Checkpoint saved for key: {checkpoint_key}, new checkpoint: {new_checkpoint}")
    except Exception as err:
        logger.error(f"{LOG_ERROR_TAG} Failed to save checkpoint for key: {checkpoint_key}, error: {err}")


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            # Initialize logging
            session_key = inputs.metadata["session_key"]
            log_level = _get_log_level(session_key, logger)
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            # Get input parameters
            account_name = input_item.get("account")
            endpoint = input_item.get("endpoint")
            region = input_item.get("region")
            zone = input_item.get("zone")
            start_date = input_item.get("start_date")
            project_id = input_item.get("project_id")
            product_name = input_item.get("product_name")
            index = input_item.get("index")
            sourcetype = input_item.get("sourcetype")

            # Setup additional elements
            collection_name = COLLECTION_NAME
            endpoint = _reconstruct_endpoint(endpoint, region, zone)

            logger.debug(
                f"{LOG_DEBUG_TAG} Input parameters: account_name={account_name}, endpoint={endpoint}, region={region}, zone={zone}, start_date={start_date}, project_id={project_id}, product_name={product_name}, index={index}, sourcetype={sourcetype}"
            )

            # Recover data from splunk conf and kvstore
            organization_id, scw_secret_key = get_account_settings(session_key, account_name, logger)
            proxy_settings = get_proxy_settings(session_key, logger)
            checkpoint = load_checkpoint(collection_name, normalized_input_name, start_date, session_key, logger)

            # if account not setup properly -> exit
            if not organization_id or not scw_secret_key:
                logger.error(f"{LOG_ERROR_TAG} Invalid account settings for input: {normalized_input_name}")
                continue

            # API call
            query_parameters = _get_query_parameters(endpoint, organization_id, checkpoint, project_id, product_name)
            events, new_checkpoint = get_data_from_api(
                endpoint, scw_secret_key, query_parameters, proxy_settings, logger
            )

            # Write and save data
            write_events(index, sourcetype, events, input_name, account_name, event_writer, logger)
            save_checkpoint(new_checkpoint, collection_name, normalized_input_name, session_key, logger)

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                LOG_ERROR_TAG,
                msg_before=f"Exception raised while ingesting data for {normalized_input_name}: {e}",
            )
