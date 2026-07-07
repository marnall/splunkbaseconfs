import time
import certifi
import splunklib.client as client
import splunklib.results as results
import json
import ApiConstants
import requests
import traceback
import os
from datetime import datetime, timedelta
from splunklib.modularinput import *
from collections.abc import Sequence

def mask_proxy_url(proxy_url):
    """
    Mask the password (and partially the username) inside proxy URL before logging.
    Example:
      http://alice:SuperPass123@10.0.1.5:8080
      → http://a***:****@10.0.1.5:8080
    """
    if not proxy_url or "@" not in proxy_url or "://" not in proxy_url:
        return proxy_url  # nothing to mask

    try:
        scheme, rest = proxy_url.split("://", 2)
        creds, host = rest.split("@", 1)
        if ":" in creds:
            username, password = creds.split(":", 1)
            masked_username = username[:1] + "***" if username else ""
            masked_password = "****"
            masked_creds = f"{masked_username}:{masked_password}"
        else:
            masked_creds = "***"

        return f"{scheme}://{masked_creds}@{host}"
    except Exception:
        return proxy_url  # fallback if unexpected formatting

def make_request(url, api_key, logger=None, certificate=None, method='GET', payload_json=None, params=None,
                 proxy_enabled=None, proxy_url=None, proxy_username=None, proxy_password=None):
    """
    Make an HTTP request to the specified URL using the provided API key and method.

    Supports GET/POST methods and optional proxy configuration (with or without authentication).
    Automatically encodes headers via ApiConstants.

    Args:
        url (str): The target endpoint URL for the request.
        api_key (str): API key used for authorization.
        logger (Logger, optional): Logger instance for logging info/errors. Defaults to None.
        method (str, optional): HTTP method ('GET', 'POST', etc.). Defaults to 'GET'.
        payload_json (dict or str, optional): JSON payload to send in the request body. Defaults to None.
        params (dict, optional): Query parameters to send in the URL. Defaults to None.
        proxy_enabled (bool, optional): Whether to enable proxy usage. Defaults to None.
        proxy_url (str, optional): Proxy URL (e.g., "http://proxy.example.com:8080"). Defaults to None.
        proxy_username (str, optional): Proxy authentication username. Defaults to None.
        proxy_password (str, optional): Proxy authentication password. Defaults to None.

    Returns:
        requests.Response: The HTTP response object.

    Raises:
        requests.exceptions.RequestException: If the HTTP request fails due to connection or timeout issues.

    Logs:
        - Proxy configuration used.
        - Request target and method.
    """

    headers = ApiConstants.HEADERS(api_key)
    encoded_headers = ApiConstants.ENCODED_HEADER(headers)
    proxies = None
    if str(proxy_enabled).lower() == "true" and proxy_url:
        if proxy_username and proxy_password:
            # Insert username/password into proxy URL safely
            scheme = "https" if proxy_url.startswith("https") else "http"
            auth_proxy = proxy_url.replace(f"{scheme}://", f"{scheme}://{proxy_username}:{proxy_password}@")
            proxies = {
                "http": auth_proxy,
                "https": auth_proxy
            }
        else:
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
    masked_key = api_key[:4] + "****" + api_key[-4:] if api_key else "N/A"
    masked_proxy = mask_proxy_url(proxy_url) if proxy_enabled else "No proxy"

    logger.info(f"[Cyble EVENTS] Request URL     : {url}")
    logger.info(f"[Cyble EVENTS] API Key (masked): {masked_key}")
    logger.info(f"[Cyble EVENTS] Proxy Enabled   : {proxy_enabled}")
    logger.info(f"[Cyble EVENTS] Proxy Used      : {masked_proxy}")
    logger.info(f"[Cyble EVENTS] Certificate Provided: {True if certificate else False}")
    if certificate and os.path.isfile(certificate):
        return requests.request(
            method,
            url,
            data=payload_json,
            headers=encoded_headers,
            params=params,
            proxies=proxies,
            timeout=ApiConstants.DEFAULT_REQUEST_TIMEOUT,
            verify=certifi.where()
        )
    else:
        return requests.request(
            method,
            url,
            data=payload_json,
            headers=encoded_headers,
            params=params,
            proxies=proxies,
            timeout=ApiConstants.DEFAULT_REQUEST_TIMEOUT,
            verify=True
        )


def get_data(host, payload, alerts_api_key, logger,
             proxy_enabled=None, proxy_url=None, proxy_username=None, proxy_password=None, certificate=None):
    """
    Send an HTTP POST request to fetch alert data from the Cyble API.

    Uses `make_request()` to handle proxy settings and header encoding.
    Returns parsed JSON data if successful, otherwise an empty dictionary.

    Args:
        host (str): Base host URL for the Cyble API.
        payload (dict): Payload to send in the request.
        alerts_api_key (str): API key for authentication.
        logger (Logger): Logger instance.
        proxy_enabled (bool, optional): Whether to use proxy. Defaults to None.
        proxy_url (str, optional): Proxy URL. Defaults to None.
        proxy_username (str, optional): Proxy username. Defaults to None.
        proxy_password (str, optional): Proxy password. Defaults to None.

    Returns:
        dict: Parsed JSON response if successful, else empty dictionary.
    """
    max_retries = 3
    retry_delay = 5
    url = f"{host}/y/tpi/splunk/alerts"
    for attempt in range(1, max_retries + 1):
        try:
            payload_json = json.dumps(payload)
            response = make_request(
                url,
                alerts_api_key,
                logger=logger,
                certificate=certificate,
                method='POST',
                payload_json=payload_json,
                params=None,
                proxy_enabled=proxy_enabled,
                proxy_url=proxy_url,
                proxy_username=proxy_username,
                proxy_password=proxy_password,
            )

            if response.status_code != 200:
                logger.error(f"[CYBLE_HTTP_UTIL][Cyble Events] Request failed with status code: {response.status_code}")
                if attempt < max_retries:
                    logger.info(f"[Cyble Events] Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return {}

            return response.json()

        except Exception as e:

            if attempt < max_retries:
                logger.info(f"[Cyble Events] Retrying to fetch data in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"[Cyble Events] All retries failed.")
                logger.error(f"[Cyble Events][CYBLE_HTTP_UTIL] Error while processing alert request: {str(e)}")
                return {}

    return {}


def get_data_with_retry(api_key, gte: datetime, lte: datetime, logger, input_name, service, hide_data=False,
                        proxy_enabled=None, proxy_url=None, proxy_username=None, proxy_password=None, session_key=None,
                        certificate=None):
    """
    Retrieve alert data from Cyble API for a given time range and service with retry support.

    Splits the time window recursively into smaller ranges if the API fails or no data is returned.

    Args:
        api_key (str): API key for Cyble authentication.
        gte (datetime): Start time of data retrieval.
        lte (datetime): End time of data retrieval.
        logger (Logger): Logger instance for logging.
        input_name (str): Splunk input name.
        service (dict): Service dictionary (includes 'name' and 'displayName').
        hide_data (bool, optional): Whether to hide sensitive fields. Defaults to False.
        proxy_enabled (bool, optional): Proxy enable flag. Defaults to None.
        proxy_url (str, optional): Proxy URL. Defaults to None.
        proxy_username (str, optional): Proxy username. Defaults to None.
        proxy_password (str, optional): Proxy password. Defaults to None.
        session_key (str, optional): Splunk session key for index insertion. Defaults to None.

    Returns:
        dict: The processed service object.
    """
    logger.info(f"[Cyble Events] Fetching data for service (get_data_with_retry): {service['name']}")
    que, take = [[gte, lte]], ApiConstants.DATA_PAR_PAGE

    while len(que) > 0:
        current_gte, current_lte = que.pop(0)
        payload = ApiConstants.PAYLOAD_ALERTS(
            current_gte, current_lte, False, 0, take, service['name'], hide_data
        )

        response = get_data(
            ApiConstants.HOST,
            payload,
            api_key,
            logger,
            proxy_enabled=proxy_enabled,
            proxy_url=proxy_url,
            proxy_username=proxy_username,
            proxy_password=proxy_password,
            certificate=certificate
        )

        if 'data' in response:
            insert_data_in_index(api_key, current_gte, current_lte, logger, input_name, service, hide_data, session_key,
                                 proxy_enabled, proxy_url, proxy_username, proxy_password, certificate,
                                 initial_response=response)
        elif time_diff_in_mins(current_gte, current_lte) >= ApiConstants.MIN_MINUTES_TO_FETCH:
            mid_datetime = current_gte + (current_lte - current_gte) / 2
            que.extend([[current_gte, mid_datetime], [mid_datetime + timedelta(microseconds=1), current_lte]])
        else:
            logger.error(f"[Cyble Events] Unable to fetch data for gte: {current_gte} to lte: {current_lte}")

    return service


def get_all_services(api_key, logger, certificate, proxy_enabled, proxy_url, proxy_username, proxy_password):
    """
    Retrieve all available alert services from the Cyble API.

    Args:
        api_key (str): API key for authentication.
        logger (Logger): Logger instance for logging.

    Returns:
        list[dict]: A list of service dictionaries if successful, otherwise an empty list.

    Raises:
        Exception: If the API response format is invalid or request fails.
    """
    max_retries = 3
    retry_delay = 5
    for attempt in range(1, max_retries + 1):
        try:
            url = "%s/y/tpi/splunk/alerts/services" % ApiConstants.HOST
            if certificate:
                response = make_request(url, api_key, logger, certificate=certificate, method='GET', payload_json=None,
                                        params=None,
                                        proxy_enabled=proxy_enabled,
                                        proxy_url=proxy_url,
                                        proxy_username=proxy_username,
                                        proxy_password=proxy_password)
            else:
                response = make_request(url, api_key, logger, certificate=None, method='GET', payload_json=None,
                                        params=None,
                                        proxy_enabled=proxy_enabled,
                                        proxy_url=proxy_url,
                                        proxy_username=proxy_username,
                                        proxy_password=proxy_password)

            if response.status_code != 200:
                logger.error("[Cyble Events] Request failed with status code: %d" % response.status_code)
                if attempt < max_retries:
                    logger.info(f"[Cyble Events] Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error("[Cyble Events] Max retries reached. Giving up.")
                    return []

            response = response.json()
            if 'data' in response and isinstance(response['data'], Sequence):
                return response['data']
            else:
                raise Exception("[Cyble Events] Wrong Format for services response")
        except Exception as e:
            logger.error("[Cyble Events] Error while processing Alert request: %s" % str(e))
            if attempt < max_retries:
                logger.info(f"[Cyble Events] Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            else:
                logger.error("[Cyble Events] Max retries reached. Giving up.")
                return []
    return []


def time_diff_in_mins(gte: datetime, lte: datetime):
    """
    Calculates the difference in minutes between two datetime objects.

    :param gte: The start date time
    :param lte: The end date time
    :return: The difference in minutes
    """
    return (lte - gte).total_seconds() / 60


def insert_data_in_index(api_key, gte: datetime, lte: datetime, logger, input_name, service, hide_data, session_key,
                         proxy_enabled, proxy_url, proxy_username, proxy_password, certificate, initial_response=None):
    """
    Insert fetched Cyble alert data into a Splunk index.

    Pulls data in batches and writes each entry to the "cyble_alerts" index.

    Args:
        api_key (str): API key used for Cyble API requests.
        gte (datetime): Start timestamp.
        lte (datetime): End timestamp.
        logger (Logger): Logger instance.
        input_name (str): Input stanza name in Splunk.
        service (dict): Cyble service info.
        hide_data (bool): Whether to hide sensitive content.
        session_key (str): Splunk session key for authentication.
        proxy_enabled (bool): Whether proxy is enabled.
        proxy_url (str): Proxy URL.
        proxy_username (str): Proxy username.
        proxy_password (str): Proxy password.
        initial_response (dict, optional): Pre-fetched response for the first page to avoid duplicate API call. Defaults to None.
    """
    skip, take = 0, ApiConstants.DATA_PAR_PAGE
    logger.info("[Cyble Events] Fetching data for service in batches(insert_data_in_index): %s" % str(service['name']))
    try:
        while True:
            if initial_response is not None:
                response = initial_response
                initial_response = None
            else:
                response = get_data(ApiConstants.HOST,
                                    ApiConstants.PAYLOAD_ALERTS(gte, lte, False, skip, take, service['name'],
                                                                hide_data),
                                    api_key, logger, proxy_enabled=proxy_enabled, proxy_url=proxy_url,
                                    proxy_username=proxy_username, proxy_password=proxy_password,
                                    certificate=certificate)
            skip += take
            if 'data' in response and isinstance(response['data'], Sequence):
                inserted_count = 0
                skipped_count = 0
                logger.info("[Cyble Events] Received %s for Processing" % str(len(response['data'])))
                for row in response['data']:
                    row['service_name'] = service['displayName']
                    server = client.connect(token=session_key, app="CybleThreatIntel")
                    row_id = row.get("id")
                    search_query = f'search index="cyble_alerts"  id="{row_id}" earliest=-180d latest=now'
                    logger.info(f"[Cyble Events] Checking for existing record with id={search_query}")
                    results_found = False
                    try:
                        rr = results.JSONResultsReader(server.jobs.oneshot(search_query, output_mode="json"))
                        for result in rr:
                            if isinstance(result, results.Message):
                                logger.info(f"Splunk Message - {result.type}: {result.message}")
                                logger.info(f"JSON Load Error: {response}")
                            elif isinstance(result, dict):
                                logger.info(
                                    f"[Cyble Events] Duplicate record found with id={row_id}, skipping insertion.")
                                logger.info(f"[Cyble Events] Record details: {json.dumps(result)}")
                                results_found = True
                                skipped_count += 1
                        if not results_found:
                            logger.info(
                                f"[Cyble Events] No existing record found with id={row_id}, proceeding with insertion.")
                            index = server.indexes["cyble_alerts"]
                            index.submit(json.dumps(row))
                            inserted_count += 1
                    except Exception as e:
                        logger.error("[Cyble Events] Error inserting data into index: %s" % str(e))
                        logger.error("[Cyble Events] Traceback:\n%s" % traceback.format_exc())

                logger.info("[Cyble Events] Summary | Total received: %s | Inserted: %s | Skipped (duplicates): %s",
                            str(len(response['data'])), inserted_count, skipped_count)
            else:
                logger.warning(
                    f"[Cyble Events] Unexpected or missing 'data' in response for service={service['name']}, "
                    f"gte={gte}, lte={lte}, skip={skip}, take={take}. Response={response}"
                )

                break
            if len(response['data']) <= 0:
                break
    except Exception as e:
        logger.error("[Cyble Events] Failed to insert data, Error: %s" % str(e))
        logger.error("[Cyble Events] Traceback:\n%s" % traceback.format_exc())


def get_ioc_base(api_key, gte: datetime, lte: datetime, page, proxy_enabled=False, proxy_url=None, proxy_username=None,
                 proxy_password=None, logger=None, certificate=None):
    """
    Makes a POST request to the Cyble IOCs API with the given parameters and proxy support.

    :param api_key: The API key to be used for the request.
    :param gte: The start date time.
    :param lte: The end date time.
    :param page: The page number to fetch.
    :param proxy_enabled: Whether to use proxy.
    :param proxy_url: Proxy URL (http or https).
    :param proxy_username: Proxy username.
    :param proxy_password: Proxy password.
    :return: The response object.
    """

    headers = ApiConstants.HEADERS(api_key)
    encoded_headers = ApiConstants.ENCODED_HEADER(headers)
    body = {
        "page": page,
        "startDate": gte.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": lte.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    # --- Build proxy configuration ---
    proxies = None
    if proxy_enabled and proxy_url:
        # Format authentication if available
        if proxy_username and proxy_password:
            # Insert username/password into proxy URL safely
            scheme = "https" if proxy_url.startswith("https") else "http"
            auth_proxy = proxy_url.replace(f"{scheme}://", f"{scheme}://{proxy_username}:{proxy_password}@")
            proxies = {
                "http": auth_proxy,
                "https": auth_proxy
            }
        else:
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }

    masked_key = api_key[:4] + "****" + api_key[-4:] if api_key else "N/A"
    masked_proxy = mask_proxy_url(proxy_url) if proxy_enabled else "No proxy"
    logger.info(f"[Cyble IOCs] Request URL     : {ApiConstants.IOC_URL}")
    logger.info(f"[Cyble IOCs] API Key (masked): {masked_key}")
    logger.info(f"[Cyble IOCs] Proxy Enabled   : {proxy_enabled}")
    logger.info(f"[Cyble IOCs] Proxy Used      : {masked_proxy}")
    try:
        if proxies:
            response = requests.post(ApiConstants.IOC_URL, headers=encoded_headers, json=body, proxies=proxies,
                                     timeout=60, verify=certifi.where())
        else:
            response = requests.post(ApiConstants.IOC_URL, headers=encoded_headers, json=body, timeout=60, verify=True)
        return response
    except requests.exceptions.ProxyError as e:
        raise Exception(f"[Cyble IOCs] Proxy connection failed: {e}")
    except Exception as e:
        raise Exception(f"[Cyble IOCs] Error making API request: {e}")


def get_iocs_page(api_key, page, gte: datetime, lte: datetime, logger, proxy_enabled=False, proxy_url=None,
                  proxy_username=None, proxy_password=None, certificate=None):
    """
    Fetch a single page of Indicators of Compromise (IOCs) data from the Cyble API.

    This function retrieves IOCs for a specified time range (gte to lte) and page number.
    It also handles pagination and proxy configuration. If the request fails or the response
    format is invalid, it logs detailed error information and returns an empty list.

    Args:
        api_key (str): The API key used to authenticate with the Cyble API.
        page (int): The page number to fetch from the paginated IOC data.
        gte (datetime): The start datetime (greater than or equal to) for IOC data retrieval.
        lte (datetime): The end datetime (less than or equal to) for IOC data retrieval.
        logger (Logger): Logger instance used for logging information and errors.
        proxy_enabled (bool, optional): Whether to use a proxy for the request. Defaults to False.
        proxy_url (str, optional): The proxy server URL (e.g., "http://proxy.example.com:8080"). Defaults to None.
        proxy_username (str, optional): Username for proxy authentication. Defaults to None.
        proxy_password (str, optional): Password for proxy authentication. Defaults to None.

    Returns:
        tuple[list, bool]:
            - list: The list of IOC entries retrieved for the given page.
            - bool: Indicates whether more pages are available (`True` if pagination `next` exists).

    Raises:
        Exception: If the API response is invalid or the data cannot be fetched successfully.

    Logs:
        - Info: Request URL, pagination status, and number of IOC entries retrieved.
        - Error: HTTP errors, missing pagination data, or unexpected response formats.
    """
    max_retries, retry_delay = 3, 5
    for attempt in range(1, max_retries + 1):
        page_array, more = [], False
        try:
            if certificate:
                response = get_ioc_base(api_key, gte, lte, page, proxy_enabled, proxy_url, proxy_username,
                                        proxy_password, logger, certificate)
            else:
                response = get_ioc_base(api_key, gte, lte, page, proxy_enabled, proxy_url, proxy_username,
                                        proxy_password, logger, None)

            if response.status_code != 200:
                logger.error(
                    f"[Cyble IOCs] Failed to fetch data. Status code: {response.status_code}, Response: {response.text}")
                if attempt < max_retries:
                    logger.info(f"[Cyble IOCs] Retrying page {page} in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[Cyble IOCs] All retries failed for page {page}.")
                    return page_array, more

            response_json = response.json()

            if 'data' in response_json and 'pagination' in response_json['data']:
                more = response_json['data']['pagination'].get('next', False)
                logger.info(f"[Cyble IOCs] Pagination next: {more}")
            else:
                logger.error("[Cyble IOCs] Invalid or missing pagination data in response.")

            if 'data' in response_json and 'iocs' in response_json['data'] and isinstance(response_json['data']['iocs'],
                                                                                          Sequence):
                page_array = response_json['data']['iocs']
                logger.info(f"[Cyble IOCs] Retrieved {len(page_array)} IOC entries")
            else:
                logger.info("[Cyble IOCs] no further iocs found.")

            return page_array, more

        except Exception as e:
            logger.error(f"[Cyble IOCs] Exception in get_iocs_page: {str(e)}")
            logger.error(f" [Cyble IOCs] Traceback:\n{traceback.format_exc()}")

            if attempt < max_retries:
                logger.info(f"[Cyble IOCs] Retrying page {page} in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            else:
                logger.error(f"[Cyble IOCs] All retries failed for page {page}.")
                return page_array, more

    return page_array, more


