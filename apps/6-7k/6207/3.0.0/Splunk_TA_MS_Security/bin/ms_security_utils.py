##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import datetime
import json
import logging
import socket
import time
import sys
import re
import traceback
from base64 import b64decode
from collections import namedtuple
from functools import lru_cache
from json.decoder import JSONDecodeError
from typing import Optional, Tuple, TypeVar, Dict, Any, List, Generator
import import_declare_test  # isort: skip
import requests
import splunk.rest as rest
import splunklib.client as client
from requests import HTTPError, RequestException
from solnlib import conf_manager, log, utils
from solnlib.modular_input import checkpointer
from Splunk_TA_MS_Security.api_specific_content import ApiSpecificContent
from ta_execution_exception import TaExecutionException
import splunk_ta_ms_security_constants
from splunklib import modularinput as smi

APP_NAME = import_declare_test.ta_name
CHECKPOINTER = splunk_ta_ms_security_constants.CHECKPOINTER
SETTINGS_CONF_NAME = splunk_ta_ms_security_constants.SETTINGS_CONF_NAME
ALERTS_INPUT_TYPE = splunk_ta_ms_security_constants.ALERTS_INPUT_TYPE
MACHINES_INPUT_TYPE = splunk_ta_ms_security_constants.MACHINES_INPUT_TYPE
INCIDENTS_INPUT_TYPE = splunk_ta_ms_security_constants.INCIDENTS_INPUT_TYPE
SIMULATIONS_INPUT_TYPE = splunk_ta_ms_security_constants.SIMULATIONS_INPUT_TYPE
ACCOUNT_CONF_NAME = splunk_ta_ms_security_constants.ACCOUNT_CONF_NAME

# Constants for chunked processing
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_SIZE_SIMULATIONS = (
    50  # Smaller for simulations due to additional API calls
)
DEFAULT_REQUEST_TIMEOUT = 60
MAX_RETRY_ATTEMPTS = 6
RATE_LIMIT_BASE_WAIT = 20
RATE_LIMIT_BACKOFF_FACTOR = 2.6
RETRY_WAIT_TIME = 5
DEFAULT_LOOKBACK_DAYS = 30

# FIXME: remove sys.exit(): none of the utility functions may decide to close the program

api_urls = namedtuple(
    "api_urls",
    "authorization, resource, alerts, incidents, advanced_hunting, machines, simulations, simulation_report, api",
)


def get_account_details(
    logger: logging.Logger, session_key: str, account_name: str
) -> Optional[Dict[str, str]]:
    """
    Returns username and password of the account configured
    :param logger: a logger object
    :param session_key: a session key
    :param account_name: name of the account of which username and password are fetched
    :returns dict: dictionary containing username, password and tenant_id(if provided) of the account
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONF_NAME}",
        )
        account_conf_file = cfm.get_conf(ACCOUNT_CONF_NAME)
        logger.debug(
            f"Reading username, password from splunk_ta_ms_security_account.conf for account_name={account_name}"
        )
        return {
            "username": account_conf_file.get(account_name).get("username"),
            "password": account_conf_file.get(account_name).get("password"),
            "tenant_id": account_conf_file.get(account_name).get("tenant_id"),
        }
    except Exception as e:
        logger.error(
            f"Failed to fetch the account details from splunk_ta_ms_security_account.conf "
            f"file for the AccountName={account_name}. Reason={e}"
        )
        sys.exit("Error while fetching account details. Terminating modular input.")


def get_start_date(
    logger: logging.Logger,
    session_key: str,
    check_point_key: str,
    input_item: dict,
    input_stanza_name: str,
) -> str:
    """
    Gets the start date of the modinput configured
    :param logger: a logger object
    :param session_key: a session key
    :param check_point_key: checkpoint object
    :param input_item: an input item
    :param input_stanza_name: stanza name from which start_date is fetched
    :returns str: start date as a JSON string
    """
    logger.debug(f"Trying to get date from checkpoint. InputName={check_point_key}")
    checkpoint_collection = checkpointer.KVStoreCheckpointer(
        CHECKPOINTER, session_key, APP_NAME
    )
    date_from_checkpoint = checkpoint_collection.get(check_point_key)
    if date_from_checkpoint:
        logger.info(
            f"action=date_from_ckpt, Start date found from checkpoint : ckpt_date={date_from_checkpoint}"
        )
        return date_from_checkpoint
    else:
        logger.info(
            "action=date_from_config, Start date not found from checkpoint, trying to get from the input configuration"
        )
        start_date = input_item.get("start_date")
        if start_date not in [None, ""]:
            if not start_date.endswith("Z"):
                start_date = f"{start_date}Z"
            return start_date
        else:
            logger.info(
                f'action=date_use_default, No start_date specified in InputName={input_item.get("name")}, setting default start_date'
            )
            cfm = conf_manager.ConfManager(session_key, APP_NAME)
            conf = cfm.get_conf("inputs")
            default_start_date = (
                datetime.datetime.utcnow()
                - datetime.timedelta(days=DEFAULT_LOOKBACK_DAYS)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            conf.update(input_stanza_name, {"start_date": default_start_date})
            logger.debug("Setting default start_date (30 days ago) in inputs.conf")
            return default_start_date


def get_access_token(
    client_id: str,
    client_secret: str,
    urls: api_urls,
    logger: logging.Logger,
    session_key: str,
) -> str:
    """
    Gets access token
    :param client_id: client id of the account configured
    :param client_secret: client secret of the account configured
    :param ulrs: urls to be used to communicate with microsoft API
    :param logger: logger object
    :param session_key: a session key
    :raises Exception: if access token is not obtained
    :returns: access token
    """
    payload = ApiSpecificContent.get_login_payload(
        urls.api, client_id, urls.resource, client_secret
    )
    try:
        proxies = get_proxy(logger, session_key)
        response = requests.post(  # nosemgrep
            urls.authorization,
            data=payload,
            proxies=proxies,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        ).json()
        if response.get("error_description"):
            logger.error(
                f'action=fetch_token_failure, reason={response["error_description"]}'
            )
            sys.exit(1)
        # INFO is 20, so we don't want to decode the access token redundantly unless the DEBUG logs are enabled
        if logger.level < logging.INFO:
            logger.debug(
                splunk_ta_ms_security_constants.TOKEN_ROLES_MESSAGE.format(
                    roles=decode_access_token(response["access_token"], logger=logger)
                )
            )
        return response["access_token"]
    except Exception as e:
        logger.error(
            f"Splunk Exception occurred while retrieving access token, reason={e}"
        )
        raise e


@lru_cache(maxsize=8)
def get_proxy(logger: logging.Logger, session_key: str) -> Optional[Dict[str, str]]:
    """
    Gets the proxy setting if proxy is configured
    :param logger: a logger object
    :param session_key: a session key
    :returns None: if proxy is disabled
    :returns dict: dictionary with proxy parameter details
    """
    proxies = None
    logger.debug("Checking proxy configuration settings")
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{SETTINGS_CONF_NAME}",
        )

        proxy = cfm.get_conf(SETTINGS_CONF_NAME).get("proxy")
    except Exception as e:
        log.log_exception(
            logger,
            e,
            exc_label="Proxy",
            msg_before=f"Failed to fetch proxy details from configuration. Traceback={traceback.format_exc()}",
        )
        sys.exit(1)

    if proxy:
        if utils.is_false(proxy.get("proxy_enabled", 0)):
            logger.info("Proxy is not enabled.")
        else:
            proxy_address = f"{proxy.get('proxy_url')}:{proxy.get('proxy_port')}"

            logger.debug(f"Proxy is enabled: proxy_address={proxy_address}")

            if proxy.get("proxy_username") and proxy.get("proxy_password"):
                proxy_url = f"http://{requests.compat.quote_plus(proxy.get('proxy_username'))}:{requests.compat.quote_plus(proxy.get('proxy_password'))}@{proxy_address}"
            else:
                proxy_url = f"http://{proxy_address}"

            proxies = {"http": proxy_url, "https": proxy_url}
    return proxies


def _handle_rate_limit_retry(
    logger: logging.Logger, retry_count: int, max_retries: int
) -> None:
    """
    Handle rate limit (429) responses with exponential backoff.

    :param logger: logger object
    :param retry_count: current retry attempt number
    :param max_retries: maximum number of retries allowed
    """
    wait_time = RATE_LIMIT_BASE_WAIT * (RATE_LIMIT_BACKOFF_FACTOR**retry_count)
    logger.warning(
        f"Rate limit encountered (HTTP 429). Retry attempt {retry_count + 1}/{max_retries}, "
        f"waiting {wait_time:.1f} seconds before retry"
    )
    time.sleep(wait_time)


def _make_api_request_with_retry(
    url: str,
    headers: Dict[str, str],
    proxies: Optional[Dict[str, str]],
    timeout: int,
    max_retries: int,
    logger: logging.Logger,
) -> Optional[Dict[str, Any]]:
    """
    Make API request with retry logic for rate limiting and errors.

    :param url: API endpoint URL
    :param headers: request headers
    :param proxies: proxy configuration
    :param timeout: request timeout in seconds
    :param max_retries: maximum retry attempts
    :param logger: logger object
    :returns: JSON response data or None if all retries failed
    """
    for retry in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        except HTTPError as e:
            if response.status_code == 429 and retry < max_retries:
                wait_seconds = None
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", "")
                    # Extract seconds from message like "You can send requests again in 52 seconds."
                    match = re.search(r"in (\d+) seconds", error_message)
                    if match:
                        wait_seconds = int(match.group(1))
                        logger.warning(
                            f"Rate limit encountered (HTTP 429). Server says wait {wait_seconds} seconds. "
                            f"Retry attempt {retry + 1}/{max_retries}"
                        )
                        time.sleep(wait_seconds)
                    else:
                        # Fallback to standard exponential backoff
                        _handle_rate_limit_retry(logger, retry, max_retries)
                except (JSONDecodeError, KeyError, ValueError, AttributeError):
                    # If we can't parse the response, use standard logic
                    _handle_rate_limit_retry(logger, retry, max_retries)
                continue
            else:
                log.log_exception(
                    logger,
                    e,
                    exc_label="API Request Failed",
                    msg_before=f"HTTP error after {retry} retry attempts: {e}",
                )
                raise e

        except Exception as e:
            logger.error(f"Request failed on attempt {retry + 1}: {e}")
            if retry == max_retries:
                raise e
            time.sleep(RETRY_WAIT_TIME)

    return None


def get_atp_alerts_odata(
    logger: logging.Logger,
    session_key: str,
    access_token: str,
    url: str,
    user_agent: Optional[str] = None,
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    max_retries: int = MAX_RETRY_ATTEMPTS,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Generator[Tuple[List[Dict[str, Any]], Dict[str, Any]], None, None]:
    """
    Iteratively gets events using OData pagination with chunked processing.
    Yields batches of events for streaming processing and memory efficiency.

    :param logger: logger object
    :param session_key: session key
    :param access_token: access token for authorization header
    :param url: initial URL to request data from
    :param user_agent: user-agent for header. Defaults to None
    :param request_timeout timeout for API calls
    :param max_retries: maximum number of retries for rate limiting. Defaults to 6
    :param chunk_size: chunk size for API calls
    :yields: tuple of (batch_events: list, batch_metadata: dict)
    :raises ValueError: if URL is not HTTPS
    :raises Exception: if request fails after retries
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-type": "application/json",
    }
    if user_agent:
        headers["User-Agent"] = user_agent

    proxies = get_proxy(logger, session_key)
    current_url = url
    total_processed = 0
    batch_number = 1
    current_batch = []

    logger.info(
        f"Starting OData pagination collection with chunk_size={chunk_size} from {url.split('?')[0]}"
    )

    while current_url:
        if not is_https(current_url):
            e = ValueError(f"URL scheme is not HTTPS: {current_url}")
            log.log_exception(logger, e, exc_label="URL Validation")
            raise e

        logger.debug(f"Fetching page from: {current_url.split('?')[0]}...")

        response_data = _make_api_request_with_retry(
            url=current_url,
            headers=headers,
            proxies=proxies,
            timeout=request_timeout,
            max_retries=max_retries,
            logger=logger,
        )

        if not response_data:
            logger.error("Failed to retrieve response data after all retry attempts")
            break

        page_events = response_data.get("value", [])
        logger.debug(f"Retrieved {len(page_events)} items from current page")

        for event in page_events:
            current_batch.append(event)
            total_processed += 1

            if len(current_batch) >= chunk_size:
                batch_metadata = {
                    "batch_number": batch_number,
                    "batch_size": len(current_batch),
                    "total_processed": total_processed,
                    "has_more": "@odata.nextLink" in response_data,
                }
                logger.debug(
                    f"Yielding batch #{batch_number}: {len(current_batch)} items, total processed: {total_processed}"
                )
                yield current_batch, batch_metadata
                current_batch = []
                batch_number += 1

        current_url = response_data.get("@odata.nextLink")
        if current_url:
            logger.debug(f"Next page available: {current_url}")

    if current_batch:
        batch_metadata = {
            "batch_number": batch_number,
            "batch_size": len(current_batch),
            "total_processed": total_processed,
            "has_more": False,
            "is_final_batch": True,
        }
        logger.debug(
            f"Yielding final batch #{batch_number}: {len(current_batch)} items"
        )
        yield current_batch, batch_metadata

    logger.info(
        f"OData pagination complete. Total items collected: {total_processed}, batches yielded: {batch_number}"
    )


def process_events_chunked(
    logger: logging.Logger,
    session_key: str,
    access_token: str,
    url: str,
    input_item: Dict[str, Any],
    input_stanza_name: str,
    check_point_key: str,
    event_writer: smi.EventWriter,
    source: str,
    sourcetype: str,
    query_date: str,
    user_agent: Optional[str] = None,
    date_field_names: list = None,
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
) -> int:
    """
    Process events using chunked streaming with incremental checkpointing.

    :param logger: logger object
    :param session_key: session key
    :param access_token: access token
    :param url: API URL to fetch data from
    :param input_item: input configuration
    :param input_stanza_name: input stanza name
    :param check_point_key: checkpoint key
    :param event_writer: Splunk EventWriter
    :param source: Splunk event source
    :param sourcetype: Splunk event sourcetype
    :param query_date: date string to filter events updated after this date
    :param user_agent: user-agent for header. Defaults to None
    :param date_field_names: list of field names to check for date
    :param request_timeout: request timeout for Defender API
    :returns: total number of events processed
    """
    logger.info(f"Starting alerts processing for source={source}")
    max_event_date = query_date
    total_ingested = 0

    try:
        for batch_events, batch_metadata in get_atp_alerts_odata(
            logger=logger,
            session_key=session_key,
            access_token=access_token,
            url=url,
            user_agent=user_agent,
            request_timeout=request_timeout,
        ):
            batch_events_written = 0

            for event_data in batch_events:
                last_update_time = next(
                    (event_data.get(k) for k in date_field_names if k in event_data), ""
                )

                required(
                    last_update_time,
                    "Field denoting last update not found in the API response",
                )

                if last_update_time > max_event_date:
                    max_event_date = last_update_time

                event = smi.Event(
                    data=json.dumps(event_data, ensure_ascii=False),
                    index=input_item["index"],
                    source=source,
                    sourcetype=sourcetype,
                )
                event_writer.write_event(event)
                batch_events_written += 1

            total_ingested += batch_events_written

            logger.info(
                f"Event batch #{batch_metadata['batch_number']} processed: "
                f"events_written={batch_events_written}, "
                f"total_processed={total_ingested}"
            )

            if max_event_date > query_date:
                checkpoint_handler(
                    logger,
                    session_key,
                    max_event_date,
                    check_point_key,
                    input_stanza_name,
                )
                logger.debug(
                    f"Checkpoint updated to {max_event_date} after batch {batch_metadata['batch_number']}"
                )

    except Exception as e:
        logger.error(f"Error during event processing for {source}: {e}")
        if max_event_date > query_date:
            logger.info(f"Saving checkpoint on error: {max_event_date}")
            try:
                checkpoint_handler(
                    logger,
                    session_key,
                    max_event_date,
                    check_point_key,
                    input_stanza_name,
                )
            except Exception as checkpoint_error:
                logger.error(f"Failed to save checkpoint on error: {checkpoint_error}")
        raise e

    log.events_ingested(
        logger=logger,
        modular_input_name=f"{sourcetype}://{input_item['name']}",
        sourcetype=sourcetype,
        n_events=total_ingested,
        index=input_item["index"],
    )

    logger.info(
        f"Event processing complete for {source}. "
        f"Total events ingested: {total_ingested}"
    )

    return total_ingested


def process_incidents_chunked(
    logger: logging.Logger,
    session_key: str,
    access_token: str,
    url: str,
    input_item: Dict[str, Any],
    input_stanza_name: str,
    check_point_key: str,
    event_writer: smi.EventWriter,
    user_agent: Optional[str] = None,
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
) -> Tuple[int, int]:
    """
    Chunked processing for incidents which contain nested alerts.

    :param logger: logger object
    :param session_key: session key
    :param access_token: access token
    :param url: API URL to fetch data from
    :param input_item: input configuration
    :param input_stanza_name: input stanza name
    :param check_point_key: checkpoint key
    :param event_writer: Splunk EventWriter
    :param user_agent: HTTP user agent
    :param request_timeout: request timeout for Defender API
    :returns: tuple of (incidents_ingested, alerts_ingested)
    """
    logger.info(f"Starting incident processing for input={input_item.get('name')}")

    query_date = get_start_date(
        logger, session_key, check_point_key, input_item, input_stanza_name
    )
    max_incident_date = query_date

    total_incidents = 0
    total_alerts = 0

    try:
        for batch_incidents, batch_metadata in get_atp_alerts_odata(
            logger=logger,
            session_key=session_key,
            access_token=access_token,
            url=url,
            user_agent=user_agent,
            request_timeout=request_timeout,
        ):
            batch_incidents_written = 0
            batch_alerts_written = 0

            for incident in batch_incidents:
                last_update_time = (
                    incident.get("lastUpdateDateTime")
                    or incident.get("lastUpdateTime")
                    or ""
                )
                required(
                    last_update_time,
                    "Field denoting last update not found in the API response",
                )

                if last_update_time > max_incident_date:
                    max_incident_date = last_update_time

                alerts = incident.get("alerts", [])
                incident_source = f"microsoft_365_defender_endpoint_incidents:{input_item['tenant_id']}"

                for alert in alerts:
                    event = smi.Event(
                        data=json.dumps(alert, ensure_ascii=False),
                        index=input_item["index"],
                        source=incident_source,
                        sourcetype=f"{input_item['sourcetype']}:alerts",
                    )
                    event_writer.write_event(event)
                    batch_alerts_written += 1

                incident_copy = incident.copy()
                if "alerts" in incident_copy:
                    del incident_copy["alerts"]

                event = smi.Event(
                    data=json.dumps(incident_copy, ensure_ascii=False),
                    index=input_item["index"],
                    source=incident_source,
                    sourcetype=input_item["sourcetype"],
                )
                event_writer.write_event(event)
                batch_incidents_written += 1

            total_incidents += batch_incidents_written
            total_alerts += batch_alerts_written

            logger.info(
                f"Incident batch #{batch_metadata['batch_number']} processed: "
                f"incidents_written={batch_incidents_written}, "
                f"alerts_written={batch_alerts_written}, "
                f"total_incidents={total_incidents}, "
                f"total_alerts={total_alerts}"
            )

            if max_incident_date > query_date:
                checkpoint_handler(
                    logger,
                    session_key,
                    max_incident_date,
                    check_point_key,
                    input_stanza_name,
                )
                logger.debug(
                    f"Checkpoint updated to {max_incident_date} after batch {batch_metadata['batch_number']}"
                )

    except Exception as e:
        log.log_exception(logger, e, exc_label="Incident Processing Error")
        if max_incident_date > query_date:
            logger.info(f"Saving checkpoint on error: {e}")
            checkpoint_handler(
                logger,
                session_key,
                max_incident_date,
                check_point_key,
                input_stanza_name,
            )
        raise e

    log.events_ingested(
        logger=logger,
        modular_input_name=f"microsoft_365_defender_endpoint_incidents://{input_item['name']}",
        sourcetype=input_item["sourcetype"],
        n_events=total_incidents,
        index=input_item["index"],
    )
    log.events_ingested(
        logger=logger,
        modular_input_name=f"microsoft_365_defender_endpoint_incidents://{input_item['name']}",
        sourcetype=f"{input_item['sourcetype']}:alerts",
        n_events=total_alerts,
        index=input_item["index"],
    )

    logger.info(
        f"Incident processing complete for {input_item.get('name')}. "
        f"Total incidents: {total_incidents}, Total alerts: {total_alerts}"
    )

    return total_incidents, total_alerts


def process_simulations_chunked(
    logger: logging.Logger,
    session_key: str,
    access_token: str,
    url: str,
    input_item: Dict[str, Any],
    input_stanza_name: str,
    check_point_key: str,
    event_writer: smi.EventWriter,
    simulation_report_url_template: str,
    user_agent: Optional[str] = None,
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
) -> int:
    """
    Special chunked processing for simulations which require additional API calls for reports.

    :param logger: logger object
    :param session_key: session key
    :param access_token: access token
    :param url: API URL to fetch simulations from
    :param input_item: input configuration
    :param input_stanza_name: input stanza name
    :param check_point_key: checkpoint key
    :param event_writer: Splunk EventWriter
    :param simulation_report_url_template: URL template for simulation reports with {simulation_id} placeholder
    :param user_agent: HTTP user agent
    :param request_timeout: request timeout for Defender API
    :returns: total number of simulations processed
    """
    logger.info(f"Starting simulation processing for input={input_item.get('name')}")

    query_date = get_start_date(
        logger, session_key, check_point_key, input_item, input_stanza_name
    )
    max_simulation_date = query_date

    total_simulations = 0

    try:
        for batch_simulations, batch_metadata in get_atp_alerts_odata(
            logger=logger,
            session_key=session_key,
            access_token=access_token,
            url=url,
            user_agent=user_agent,
            request_timeout=request_timeout,
            chunk_size=DEFAULT_CHUNK_SIZE_SIMULATIONS,
        ):
            batch_simulations_written = 0

            for simulation in batch_simulations:
                simulation_id = simulation.get("id")
                if not simulation_id:
                    logger.warning("Simulation data missing ID field, skipping")
                    continue

                try:
                    simulation_report_url = simulation_report_url_template.format(
                        simulation_id
                    )
                    simulation_report = get_simulation_report(
                        logger=logger,
                        session_key=session_key,
                        access_token=access_token,
                        url=simulation_report_url,
                        user_agent=user_agent,
                    )

                    if simulation_report:
                        simulation.update(simulation_report)
                        logger.debug(
                            f"Enriched simulation {simulation_id} with report data"
                        )

                except Exception as e:
                    logger.warning(
                        f"Could not fetch report for simulation {simulation_id}: {e}"
                    )

                completion_date = simulation.get("completionDateTime")
                required(
                    completion_date,
                    "Field denoting completion date not found in the API response",
                )

                if completion_date > max_simulation_date:
                    max_simulation_date = completion_date

                simulation_source = (
                    f"microsoft_defender_endpoint_simulations:{input_item['tenant_id']}"
                )
                event = smi.Event(
                    data=json.dumps(simulation, ensure_ascii=False, default=str),
                    index=input_item["index"],
                    source=simulation_source,
                    sourcetype=input_item["sourcetype"],
                )
                event_writer.write_event(event)
                batch_simulations_written += 1

            total_simulations += batch_simulations_written

            logger.info(
                f"Simulation batch #{batch_metadata['batch_number']} processed: "
                f"simulations_written={batch_simulations_written}, "
                f"total_processed={total_simulations}"
            )

            if max_simulation_date > query_date:
                checkpoint_handler(
                    logger,
                    session_key,
                    max_simulation_date,
                    check_point_key,
                    input_stanza_name,
                )
                logger.debug(
                    f"Checkpoint updated to {max_simulation_date} after batch {batch_metadata['batch_number']}"
                )

    except Exception as e:
        log.log_exception(logger, e, exc_label="Simulation Processing Error")
        if max_simulation_date > query_date:
            logger.info(f"Saving checkpoint on error: {e}")
            checkpoint_handler(
                logger,
                session_key,
                max_simulation_date,
                check_point_key,
                input_stanza_name,
            )
        raise e

    log.events_ingested(
        logger=logger,
        modular_input_name=f"microsoft_defender_endpoint_simulations://{input_item['name']}",
        sourcetype=input_item["sourcetype"],
        n_events=total_simulations,
        index=input_item["index"],
    )

    logger.info(
        f"Simulation processing complete for {input_item.get('name')}. "
        f"Total simulations processed: {total_simulations}"
    )

    return total_simulations


def is_https(url: str) -> bool:
    """
    Check if the url is HTTPS or not
    :param url: a url to be checked
    :returns boolean: True if url is HTTPS else False
    """
    return url.startswith("https://")


def checkpoint_handler(
    logger: logging.Logger,
    session_key: str,
    max_date: str,
    check_point_key: str,
    input_stanza_name: str,
) -> None:
    """
    Handles checkpoint update
    """
    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            CHECKPOINTER, session_key, APP_NAME
        )
        logger.debug(f"Trying to get checkpoint for the InputName={input_stanza_name}")
        _ = checkpoint_collection.get(check_point_key)
    except Exception as e:
        log.log_exception(logger, e, exc_label="Checkpoint Error")
    else:
        try:
            logger.info(f"Updating {max_date} as checkpoint date")
            checkpoint_collection.update(check_point_key, max_date)
        except Exception as e:
            log.log_exception(logger, e, exc_label="Checkpoint Update Error")


def get_config(session_key: str, logger: logging.Logger) -> Any:
    try:
        logger.debug("Connect to Splunk client")
        service = client.connect(token=session_key)

        logger.debug(f"Getting conf_file={ACCOUNT_CONF_NAME}")
        return service.confs[ACCOUNT_CONF_NAME]
    except Exception as e:
        log.log_configuration_error(
            logger,
            e,
            exc_label="Configuration Error",
        )
        raise TaExecutionException(e, 1) from e


def get_credentials(
    self, session_key: str, logger: logging.Logger
) -> Tuple[str, str, Optional[str]]:
    conf = get_config(session_key, logger)
    # we check whether the account name is provided for
    # either Update Incident(account) or Advanced Hunting(account_name)
    account_name = self.get_param("account") or self.get_param("account_name")
    credentials_tuple: tuple
    if account_name:
        logger.info(f"Splunk Defender AccountName={account_name}")

        credentials_tuple = get_credentials_with_account_name(
            self, logger, conf, session_key
        )
    else:
        logger.info("Splunk No defender account name given")
        credentials_tuple = get_credentials_without_account_name(
            logger, conf, session_key
        )
    if len(credentials_tuple) == 3:
        return credentials_tuple
    if len(credentials_tuple) == 2:
        return credentials_tuple[0], credentials_tuple[1], None

    e = TaExecutionException(
        f"Unexpected number of credentials returned: {len(credentials_tuple)}"
    )
    log.log_exception(
        logger,
        e,
        exc_label="Credentials Error",
    )
    raise e


def get_credentials_with_account_name(
    self: Any, logger: logging.Logger, conf: Any, session_key: str
) -> Tuple[str, str, str]:
    """
    Gets the client_id and client_secret
    :param: logger: logger object
    :param conf: conf file object
    :param session_key: a session key
    :returns: tuple: client_id and client_secret
    """
    client_id = client_secret = tenant_id = ""  # nosemgrep
    account = None

    # For Update Incident, parameter name is 'account'
    # For Advanced Hunting, parameter name is 'account_name'
    if self.get_param("account"):
        global_account_name = self.get_param("account")
    else:
        global_account_name = self.get_param("account_name")
    logger.info(
        f"action=cred_with_account, Retrieving credentials with AccountName={global_account_name}"
    )
    stanza = None
    for stanza in conf:
        if stanza.name == global_account_name:
            for key, value in stanza.content.items():
                # If there's a username in the key, that will be the client ID
                if key == "username":
                    try:
                        account = get_account_details(logger, session_key, stanza.name)
                        client_id = account.get("username", "")
                        client_secret = account.get("password", "")
                        tenant_id = account.get("tenant_id", "")
                        break
                    except Exception as e:  # noqa: F841
                        logger.error(
                            "get_credentials_with_account_name() - Type 3 - Exception occurred during accessing conf file values."
                        )

            if client_id != "" and client_secret != "":
                # Found the client id and secret. No need to iterate anymore.
                break

    if not account:
        stanza_name = stanza.name if stanza else "<no stanza in config>"
        logger.error(
            f"get_credentials_with_account_name() - Type 3 - The stanza name {global_account_name} specified is not in the global account "
            f"configuration. Tested with stanza name : {stanza_name}. Retrying ..."
        )
    if client_id == "" or client_secret == "":  # nosemgrep
        logger.error(
            "get_credentials_with_account_name() - Type 3 - Exception occurred. The global account name specified has not been configured. Please re-configure them or re-enter the right stanza name."
            # noqa: E501
        )
        sys.exit(1)
    else:
        return client_id, client_secret, tenant_id


def get_credentials_without_account_name(
    logger: logging.Logger, conf: Any, session_key: str
) -> Tuple[str, str]:
    """
    Gets the client_id and client_secret
    :param: logger: logger object
    :param conf: conf file object
    :param session_key: a session key
    :returns: tuple: client_id and client_secret
    """
    client_id = ""
    client_secret = ""  # nosemgrep
    logger.info(
        "action=cred_without_account, Retrieving credentials without account name"
    )

    for stanza in conf:
        for key, value in stanza.content.items():
            # If there's a username in the key, that will be the client ID
            if key == "username":
                try:
                    account = get_account_details(logger, session_key, stanza.name)
                    client_id = account.get("username")
                    client_secret = account.get("password")
                    break
                except Exception as e:  # noqa: F841
                    logger.error(
                        "get_credentials_without_account_name() - Type 3 - "
                        "Exception occurred during accessing conf file values."
                    )

        if client_id != "" and client_secret != "":
            # Found the client id and secret. No need to iterate anymore.
            break

    if client_id == "" or client_secret == "":  # nosemgrep
        logger.error(
            "get_credentials_without_account_name() - Type 3 - Exception occurred. "
            "The global account name specified has not been configured. Please re-configure "
            "them or re-enter the right stanza name."
        )
        sys.exit(1)
    else:
        return client_id, client_secret


def delete_checkpoint(
    session_key: str, input_name: str, input_type: str, LOG_FILE_NAME: str
) -> None:
    """
    Deleted the checkpoint when user deletes the input
    :param session_key: a session key
    :param input_name: input name which is to be deleted
    :param input_type: type of the input to be deleted
    :param LOG_FILE_NAME: log file name
    """
    logger = log.Logs().get_logger(LOG_FILE_NAME)
    use_log_level_from_config(logger, session_key)

    if input_type == ALERTS_INPUT_TYPE:
        checkpoint_name = f"atp_lastUpdateTime_{input_name}"
    elif input_type == INCIDENTS_INPUT_TYPE:
        checkpoint_name = f"m365_incident_lastUpdateTime_{input_name}"
    elif input_type == SIMULATIONS_INPUT_TYPE:
        checkpoint_name = f"simulation_lastUpdateTime_{input_name}"
    elif input_type == MACHINES_INPUT_TYPE:
        checkpoint_name = f"machines_lastUpdateTime_{input_name}"
    else:
        checkpoint_name = f"event_hub_lastUpdate_{input_name}"

    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            CHECKPOINTER, session_key, APP_NAME
        )
        logger.debug(f"Trying to get checkpoint for the input : InputName={input_name}")
        checkpoint_dict = checkpoint_collection.get(checkpoint_name)
        if not checkpoint_dict:
            logger.info(
                f"Checkpoint not yet set for the InputName={input_name}, deleting the input directly"
            )
            return
    except Exception as e:
        logger.error(f"Error in Checkpoint handling, reason={e}")
        sys.exit(1)

    try:
        rest_url = f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{CHECKPOINTER}/{checkpoint_name}"

        _, _ = rest.simpleRequest(
            rest_url,
            sessionKey=session_key,
            method="DELETE",
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )

        logger.info(f"Deleted checkpoint for InputName={input_name}")

    except Exception as e:
        logger.error(f"Error deleting checkpoint, reason={e}")
        sys.exit(1)


@lru_cache(maxsize=8)
def get_current_addon_version(
    logger: logging.Logger, session_key: str
) -> Optional[str]:
    """
    Gets current addon version from app.conf
    :param logger: logger object
    :param session_key: a session key
    :returns string: current addon version from app.conf
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-app",
        )
        current_version = cfm.get_conf("app").get("launcher").get("version")
        logger.debug(f"Found TA Version from app.conf - version={current_version}")
        return current_version
    except Exception as e:
        logger.error(f"Failed to get details from app.conf with exception, reason={e}")


@lru_cache(maxsize=8)
def use_log_level_from_config(logger: logging.Logger, session_key: str):
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=APP_NAME,
        conf_name=SETTINGS_CONF_NAME,
    )
    logger.info(f"log level set is log_level={log_level}")
    logger.setLevel(log_level)


@lru_cache(maxsize=2)
def get_hostname_from_socket(logger):
    logger.debug("Getting hostname from socket")
    try:
        host = socket.gethostname()
    except Exception:
        logger.error("Error getting host from socket, setting host to None")
        host = None
    logger.debug(f"Host value successfully obtained HostName={host}")
    return host


def raise_error_from_http_error(logger, e: RequestException):
    error_message = f"Failure occurred while loading error response: {e}"
    detailed_error_message = None
    try:
        error_dict = (
            json.loads(e.response.content)
            if e.response is not None and e.response.content
            else None
        )

        detailed_error_message = (
            f"Failure occurred. Received error message: {error_dict['error']['message']}"
            if error_dict
            and error_dict.get("error")
            and error_dict["error"].get("message")
            else None
        )

    except (KeyError, JSONDecodeError, TypeError) as inner_ex:
        logger.debug(f"Exception while processing error message: {inner_ex}")

    logger.error(detailed_error_message or error_message)
    raise TaExecutionException(e, 1) from e


#  Define Generic for the method below
T_ = TypeVar("T_")


def required(obj: T_, error_msg="required value is not set", name: str = "") -> T_:
    # updated the condition to accept all built-in data type's False values
    if not obj:
        prefix = (name + ": ") if name else ""
        raise ValueError(prefix + error_msg)
    return obj


def decode_access_token(access_token: str, logger: logging.Logger) -> str:
    """
    Decodes the access token and returns the roles from the token details
    """
    try:
        access_token_claims = access_token.split(".")[1]
        # we fix the padding of "=" if it is incorrect for `base64` library
        access_token_claims += "=" * (-len(access_token_claims) % 4)
        byte_token = b64decode(access_token_claims)
        decoded_access_token: dict = json.loads(byte_token)
    except JSONDecodeError:
        logger.debug(f"action=token_decode_failed, reason={traceback.format_exc()}")
        # two types of quotes are used for the correct auto KV extraction for token roles
        return '"Invalid JSON found, unable to decode the access token"'
    except Exception:
        logger.debug(f"action=token_parse_failed, reason={traceback.format_exc()}")
        # two types of quotes are used for the correct auto KV extraction for token roles
        return '"Unable to parse the access token"'
    else:
        logger.debug(
            f"action=token_parse_success, Successfully parsed the access token"
        )
        return decoded_access_token.get(
            "roles", "<roles not found in the decoded token>"
        )


def get_simulation_report(
    logger: logging.Logger,
    session_key: str,
    access_token: str,
    url: str,
    user_agent: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Gets the simulation report
    :param logger: logger object
    :param session_key: a session key
    :param access_token: access token used for header
    :param url: url on which we request to get data
    :param user_agent: user-agent for header. Defaults to None
    :raises ValueError: if url is not HTTPS
    :raises Exception e: if request call failed
    :returns Dict: simulation event data
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-type": "application/json",
    }
    if user_agent:
        headers["User-Agent"] = user_agent
    proxies = get_proxy(logger, session_key)

    try:
        logger.debug(f"Fetching simulation report from: {url.split('?')[0]}")
        r = requests.get(
            url, headers=headers, proxies=proxies, timeout=DEFAULT_REQUEST_TIMEOUT
        )
        r.raise_for_status()
        simulation_report = r.json()

    except HTTPError as http_error:
        logger.exception(http_error.response.json())
        raise http_error
    except Exception as e:
        logger.error(  # nosemgrep
            f"Exception occurred while getting data using access token : {e}"
        )
        raise e

    return simulation_report


@lru_cache(maxsize=8)
def get_proxy_dict_for_eventhub(
    logger: logging.Logger, session_key: str
) -> Optional[Dict[str, str]]:
    """
    Gets the proxy setting if proxy is configured
    :param logger: logger object
    :param session_key: a session key
    :raises Exception: raises excepotion if unable to fetch proxy details
    :returns None: if proxy is disabled
    :returns dict: dictionary with proxy parameter details
    """
    proxies = None
    logger.debug("Loading Event Hub proxy configuration")
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{SETTINGS_CONF_NAME}",
        )

        proxy = cfm.get_conf(SETTINGS_CONF_NAME).get("proxy")
    except Exception:
        logger.error(
            f"Failed to fetch proxy details from configuration. Traceback={traceback.format_exc()}"
        )
        sys.exit(1)

    if proxy:
        if utils.is_false(proxy.get("proxy_enabled", 0)):
            logger.info("Proxy is not enabled.")
        else:
            proxies = {
                "proxy_hostname": proxy.get("proxy_url"),
                "proxy_port": int(proxy.get("proxy_port")),
            }
            logger.debug(f"Proxy is enabled: proxies={proxies}")

            if proxy.get("proxy_username") and proxy.get("proxy_password"):
                proxies = {
                    "proxy_hostname": proxy.get("proxy_url"),
                    "proxy_port": int(proxy.get("proxy_port")),
                    "username": proxy.get("proxy_username"),
                    "password": proxy.get("proxy_password"),
                }
    return proxies
