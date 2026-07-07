import re
import signal
import logging

from functools import partial
from os import getpid
from re import match
from json import loads
from json.decoder import JSONDecodeError
from base64 import b64encode
from itertools import islice
from dataclasses import dataclass
from datetime import datetime, timedelta
from random import randint
from time import sleep

import requests

from requests.exceptions import (
    HTTPError,
    RetryError,
    ReadTimeout,
)

from config import (
    DEFAULT_AUTH_URL,
    SECURE_HTTP_PROTOCOL,
    CONNECTION_READ_TIMEOUT,
    CREATED_DATETIME_FORMAT,
    ACCESS_TOKEN_EXPIRATION_BUFFER_TIME,
    SALESFORCE_OCAPI_ORDER_SEARCH_FETCH_LIMIT,
)

import file_manager


###
### Clases
###
class HTTPForbiddenError(Exception):
    """A HTTP error with status code 403"""

    def __init__(self, errorMessage):
        self.errorMessage = errorMessage


@dataclass
class OCAPIOAuthClientOrServerError(Exception):
    """
    OCAPI Auth client or server error occurred.

    HTTP Client errors status codes: 4xx
    HTTP Server errors status codes: 5xx
    """

    http_status_code: int
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class OCAPIClientOrServerError(Exception):
    """
    OCAPI API client or server error occurred.

    HTTP Client errors status codes: 4xx
    HTTP Server errors status codes: 5xx
    """

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class OCAPIResponseBodyDecodeError(Exception):
    """Couldn't decode the text into JSON"""

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class OCAPIRetryError(Exception):
    """Custom retries logic failed"""

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class OCAPIReadTimeoutError(Exception):
    """Server is taking longer to respond and send information"""

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class OCAPIError(Exception):
    """OCAPI API error occurred."""

    child_exc: Exception

    def __post_init__(self):
        super().__init__(self.child_exc.exc_msg)


class SplunkIndexer:
    def __init__(
        self,
        splunk_helper,
        splunk_index_writer,
        splunk_index=None,
        host=None,
        source=None,
        sourcetype=None,
    ):
        self.host = host
        self.source = source
        self.index = splunk_index
        self.helper = splunk_helper
        self.index_writer = splunk_index_writer
        self.sourcetype = sourcetype

    def insert(self, data, dynamic_source=None):
        source = dynamic_source if dynamic_source else self.source
        event = self.helper.new_event(
            data=data,
            index=self.index,
            host=self.host,
            source=source,
            sourcetype=self.sourcetype,
        )
        self.index_writer.write_event(event)

        return None


class TimePeriodOrderFetchPlanner:
    """
    Discovers safe, optimal time periods for fetching data from an API
    with a hard result limit.

    It uses a progressive granularity approach, starting with large time
    slices and recursively breaking them down into smaller ones until it
    finds a period that contains fewer results than the API limit.
    """

    # Define the sequence of time granularities to try, from largest to smallest.
    # The values are the size of the slice in seconds.
    TIME_PERIOD_SLICES_IN_SECONDS = [
        timedelta(days=2).total_seconds(),
        timedelta(days=1).total_seconds(),
        timedelta(hours=12).total_seconds(),
        timedelta(hours=1).total_seconds(),
        timedelta(minutes=15).total_seconds(),
        timedelta(minutes=1).total_seconds(),
        timedelta(seconds=30).total_seconds(),
        timedelta(seconds=15).total_seconds(),
        timedelta(seconds=5).total_seconds(),
    ]

    def __init__(self, api_client, order_type, select_statement):
        """
        Initializes the planner.

        Args:
            api_client: An instance of SalesforceOrderAPIClient.
            order_type (str): The type of order to query for ('created' or 'updated').
            select_statement (str): The 'select' statement for the OCAPI query.
        """
        self._api_client = api_client
        self._order_type = order_type
        self._select_statement = select_statement
        self._get_count_method = getattr(
            self._api_client, f"get_{self._order_type}_orders_total_count_within_period"
        )

    def _fetch_order_count_for_period(self, start_time, end_time):
        """Private helper to get the total count of orders within a time period."""
        start_str = start_time.strftime(CREATED_DATETIME_FORMAT)
        end_str = end_time.strftime(CREATED_DATETIME_FORMAT)

        return self._get_count_method(start_str, end_str, fields=self._select_statement)

    def _find_fetchable_sub_periods(
        self, start_time, end_time, time_period_slice_index
    ):
        """
        Recursive method to find safe sub time periods.

        Returns:
            A list of (start_time, end_time, count) tuples.
        """
        # All time period slices exhausted, we cannot slice further.
        if time_period_slice_index >= len(self.TIME_PERIOD_SLICES_IN_SECONDS):
            logging.info(
                f"Un-sliceable data period detected from {start_time} to {end_time}. "
                f"The data volume is too high to be sliced further. "
                f"Proceeding to fetch it as a single chunk, but this may be slow."
            )
            # Return this period as-is.
            count = self._fetch_order_count_for_period(start_time, end_time)

            return [(start_time, end_time, count)]

        current_slice_duration = timedelta(
            seconds=self.TIME_PERIOD_SLICES_IN_SECONDS[time_period_slice_index]
        )

        # If the period is smaller than our current time slice
        # try the next time period slice.
        if (end_time - start_time) < current_slice_duration:
            return self._find_fetchable_sub_periods(
                start_time, end_time, time_period_slice_index + 1
            )

        safe_periods = []
        current_start = start_time
        while current_start < end_time:
            current_end = current_start + current_slice_duration

            if current_end > end_time:
                current_end = end_time

            count = self._fetch_order_count_for_period(current_start, current_end)

            # Skip empty periods entirely to avoid cluttering the list and doing extra work.
            if count == 0:
                current_start = current_end
                continue

            if count < SALESFORCE_OCAPI_ORDER_SEARCH_FETCH_LIMIT:
                safe_periods.append((current_start, current_end, count))
            else:
                # This slice is too large, so we "zoom in" with the next time period slice.
                finer_periods = self._find_fetchable_sub_periods(
                    current_start, current_end, time_period_slice_index + 1
                )
                safe_periods.extend(finer_periods)

            current_start = current_end

        return safe_periods

    def plan_fetchable_time_periods(self, start_time, end_time):
        """
        Discover all safe to fetch time periods within a
        given period.

        Args:
            start_time (datetime): The start of the overall time period.
            end_time (datetime): The end of the overall time period.

        Returns:
            A list of tuples, where each tuple is a (start_time, end_time, count)
            period that is guaranteed to contain fewer orders than the API limit.
            Returns an empty list if there is no data.
        """
        logging.info(
            f"Starting discovery for time period slices type={self._order_type} start_time={start_time} to end_time={end_time}"
        )
        initial_count = self._fetch_order_count_for_period(start_time, end_time)

        if initial_count == 0:
            return []

        if initial_count < SALESFORCE_OCAPI_ORDER_SEARCH_FETCH_LIMIT:
            return [(start_time, end_time, initial_count)]

        logging.info(
            f"Total count ({initial_count}) exceeds limit. Starting progressive slicing."
        )
        # Start the recursive discovery at the coarsest granularity level (index 0).
        return self._find_fetchable_sub_periods(start_time, end_time, 0)


###
### Functions
###
def split_into_batches(iterable, len):
    """Splits an iterable(lists, tuples, and etc) into batches wi

    Args:
        iterable (iter): Iterator.
        len (int): Number of items per batch.

    Returns:
        iter: Iterator object.
    """
    iterator = iter(iterable)

    while True:
        batch = list(islice(iterator, len))

        if not batch:
            break

        yield batch


def batch_save_kvstore(helper, kv_pairs_iterator):
    """Saves batches of key-value pairs into Splunk KVStore.

    Args:
        helper (ModInputsalesforce_commerce_cloud_*): Object that represents a module input.
        kv_pairs_iterator (iter): Iterator with dict objects {"_key": "...', "state": "..."}

    Returns:
        None
    """
    for batch in kv_pairs_iterator:
        helper.batch_save_check_point(batch)

    return None


def sigterm_signal_handler(signum, frame, helper, pid, data_input_id, data_input_name):
    """
    Handles SIGTERM which is used in Unix-based operating systems signal,
    outputs a logging message including the Process going to be terminated.
    """
    helper.log_info(
        f"Process Signal received pid={pid} signal=SIGTERM id={data_input_id} data_input={data_input_name} message={str(frame)}"
    )
    raise SystemExit(
        f"Process Signal received pid={pid} signal=SIGTERM id={data_input_id} data_input={data_input_name} message={str(frame)}"
    )

    return None


def sighup_signal_handler(signum, frame, helper, pid, data_input_id, data_input_name):
    """
    Handles SIGHUP which is used in Unix-based operating systems signal,
    outputs a logging message including the Process hung up.
    """
    helper.log_info(
        f"Process Signal received pid={pid} signal=SIGHUP id={data_input_id} data_input={data_input_name} message={str(frame)}"
    )
    raise SystemExit(
        f"Process Signal received pid={pid} signal=SIGHUP id={data_input_id} data_input={data_input_name} message={str(frame)}"
    )
    return None


def enforce_secure_connection(url):
    """Enforces secure HTTP connections when requesting web resources.

    Args:
        url(str): URL for the HTTP connection

    Returns:
        None
    """
    if match(SECURE_HTTP_PROTOCOL, url) is None:
        raise ValueError("The given url (%s) is not using TLS!" % url)


def obtain_access_token(helper):
    """
    Obtains access token for OCAPI authentication.
    :param helper: Splunk Add-On Builder Helper functions wrapper
    :return: a new Bearer token
    """
    auth_url = helper.get_global_setting("oauth_2_0_server_url")
    if auth_url is None:
        auth_url = DEFAULT_AUTH_URL

    enforce_secure_connection(auth_url)
    account = helper.get_arg("ocapi_credentials")

    credentials = account["username"] + ":" + account["password"]
    basic_auth = b64encode(credentials.encode("utf-8")).decode("utf-8")
    payload = "grant_type=client_credentials"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + basic_auth,
        "Accept": "*/*",
    }

    helper.log_debug("Requesting access token")

    access_request_time = datetime.now()
    try:
        response = helper.send_http_request(
            url=auth_url,
            method="POST",
            payload=payload,
            headers=headers,
            timeout=CONNECTION_READ_TIMEOUT,
        )
        response.raise_for_status()
    except HTTPError as http_error_exc:
        raise OCAPIOAuthClientOrServerError(
            http_status_code=response.status_code, exc_msg=str(http_error_exc)
        )

    access_token = loads(response.text)
    access_token["expires_datetime"] = access_request_time + timedelta(
        seconds=int(access_token["expires_in"]) - ACCESS_TOKEN_EXPIRATION_BUFFER_TIME
    )

    helper.log_debug("Token expires at %s" % access_token["expires_datetime"])

    return access_token


def split_http_auth_headers(helper, auth_headers_str):
    try:
        http_auth_headers = dict(
            (k.strip(), v.strip())
            for k, v in (item.split("=", 1) for item in auth_headers_str.split(","))
        )
        return http_auth_headers
    except ValueError as value_err_exc:
        helper.log_error(
            f"Failed to split HTTP Auth Headers auth_headers={auth_headers_str} exception={str(value_err_exc)}"
        )

        return None


def paginate(
    method,
    url,
    headers=None,
    files=None,
    data=None,
    params=None,
    auth=None,
    cookies=None,
    hooks=None,
    json=None,
    position=0,
    count=200,
):
    http_session = requests.Session()

    with http_session:
        page = 0
        total = 0
        counter = 0

        while True:
            logging.info(
                f"Sending HTTP Request url={url} page_count={page} total_count={total} counter={counter} position={position}"
            )
            try:
                response = http_session.request(
                    method,
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    params=params,
                    auth=auth,
                    cookies=cookies,
                    hooks=hooks,
                    json=json,
                    timeout=120,  # 2 minutes for bulk operations and larger file downloads
                )
                response.raise_for_status()
                response_data = response.json()
                total = response_data.get("total", -1)
                hits = response_data.get("hits", [])
                counter += len(hits)
                yield response

                if (total and counter >= total) or "next" not in response_data:
                    logging.info(
                        f"Pagination done url={url} page_count={page} total_count={total} counter={counter} position={position}"
                    )
                    break

                if json is not None:
                    position = json["start"] + count
                    json["start"] = position
                    json["count"] = count

                page += 1
            except HTTPError as http_error_exc:
                raise OCAPIClientOrServerError(
                    http_status_code=response.status_code,
                    http_response_body=response.text,
                    exc_msg=str(http_error_exc),
                )
            except JSONDecodeError as json_decode_exc:
                raise OCAPIResponseBodyDecodeError(
                    http_status_code=response.status_code,
                    http_response_body=response.text,
                    exc_msg=str(json_decode_exc),
                )
            except ReadTimeout as read_timeout_exc:
                raise OCAPIReadTimeoutError(
                    http_status_code=response.status_code,
                    http_response_body=response.text,
                    exc_msg=str(read_timeout_exc),
                )
            except RetryError as json_decode_exc:
                raise OCAPIRetryError(
                    http_status_code=response.status_code,
                    http_response_body=response.text,
                    exc_msg=str(json_decode_exc),
                )


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """
    return "/".join(map(lambda x: str(x).rstrip("/"), args))


def build_sfcc_url(hostname, endpoint, site_id, connection_type="ocapi"):
    if connection_type == "ocapi":
        return f"https://{hostname}/s/{site_id}/{endpoint}"
    elif connection_type == "gateway":
        return f"https://{hostname}/{endpoint}"
    else:
        return f"https://{hostname}/s/{site_id}/{endpoint}"


def get_sfcc_url_and_endpoint(hostname, endpoint, site_id, connection_type="ocapi"):
    if connection_type == "ocapi":
        url = f"https://{hostname}"
        assembled_endpoint = f"s/{site_id}/{endpoint}"

        return (url, assembled_endpoint)
    elif connection_type == "gateway":
        url = f"https://{hostname}"

        return (url, endpoint)
    else:
        url = f"https://{hostname}"
        assembled_endpoint = f"s/{site_id}/{endpoint}"

        return (url, assembled_endpoint)


def init_program_termination_handlers(data_input_id, data_input_name, splunk_helper):
    signal.signal(
        signal.SIGTERM,
        partial(
            sigterm_signal_handler,
            helper=splunk_helper,
            pid=getpid(),
            data_input_id=data_input_id,
            data_input_name=data_input_name,
        ),
    )
    signal.signal(
        signal.SIGHUP,
        partial(
            sighup_signal_handler,
            helper=splunk_helper,
            pid=getpid(),
            data_input_id=data_input_id,
            data_input_name=data_input_name,
        ),
    )

    return None


def get_filename_patterns(helper):
    """
    Returns a list of regular expression that are used to check
    whether a file in the logs folder is eligible for indexing.

    :param helper: Splunk Add-On Builder Helper functions wrapper

    :return: dictionary if regular expressions (ex. {
        "system_log_files_pattern": re.compile(r'^error-'),
        "jobs_log_files_pattern": re.compile(r'^jobs-'),
        "custom_log_files_pattern": re.compile(r'^customerror-')
    })
    :rtype: dict
    """
    pattern_names = [
        "custom_log_files_pattern",
        "system_log_files_pattern",
        "jobs_log_files_pattern",
        "services_log_files_pattern",
        "replication_log_files_pattern",
        "other_log_files_pattern",
    ]

    return dict(
        (name, re.compile(helper.get_arg(name)))
        for name in pattern_names
        if helper.get_arg(name)
    )


def get_job_checkpoint(
    json_repo, data_input_name, job_type, **json_file_content_metadata
):
    try:
        json_file_content = json_repo.get(data_input_name)

        if json_file_content is None:
            logging.info(
                f"File not found for job checkpoint data_input={data_input_name}"
            )
            json_file_content = file_manager.JSONFileContent(
                **file_manager.create_json_file_content(
                    type=job_type, **json_file_content_metadata
                )
            )
            json_repo.create(data_input_name, json_file_content)
            logging.info(
                f"File created for job checkpoint data_input={data_input_name} content={json_file_content.dict()}"
            )
    except file_manager.JSONFileNotFoundError as json_file_not_found_err:
        logging.error(
            f"Failed to find job checkpoint file due to file not found error data_input={data_input_name} file={json_file_not_found_err.fpath} exception={str(json_file_not_found_err)}"
        )
        logging.info(f"Creating new job checkpoint file data_input={data_input_name}")
        if (
            job_type in ("jobs", "orders", "ecdn")
            and "start_at" in json_file_content_metadata
        ):
            start_at = (datetime.now() - timedelta(minutes=15)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            json_file_content_metadata["start_at"] = start_at

        json_file_content = file_manager.JSONFileContent(
            **file_manager.create_json_file_content(
                type=job_type, **json_file_content_metadata
            )
        )
        logging.info(
            f"New job checkpoint file successfully created data_input={data_input_name} content={json_file_content.dict()}"
        )
    except file_manager.JSONFileDecodeError:
        logging.error(
            f"Failed to load job checkpoint file due to decode error data_input={data_input_name}"
        )
        logging.info(f"Creating new job checkpoint file data_input={data_input_name}")
        if (
            job_type in ("jobs", "orders", "ecdn")
            and "start_at" in json_file_content_metadata
        ):
            json_file_content_metadata["start_at"] = datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )

        json_file_content = file_manager.JSONFileContent(
            **file_manager.create_json_file_content(
                type=job_type, **json_file_content_metadata
            )
        )
        json_repo.delete(data_input_name)
        json_repo.create(data_input_name, json_file_content)
        logging.info(
            f"New job checkpoint file successfully created data_input={data_input_name} content={json_file_content.dict()}"
        )

    return json_file_content


def rollout_job_checkpoint_data(
    data_input_name,
    json_file_content,
    job_type,
    clean_period_in_days=3,
    **json_file_content_metadata,
):
    # Initializes new file content
    new_json_file_content = file_manager.JSONFileContent(
        **file_manager.create_json_file_content(
            type=job_type, **json_file_content_metadata
        )
    )
    # Trim data entries which are older than X days
    # Returns fresh content
    new_json_file_content.data = file_manager.trim_old_json_file_content_data_entries(
        json_file_content, trim_period_in_days=clean_period_in_days
    )
    logging.debug(
        f"Job checkpoint rolled out data_input={data_input_name} content={json_file_content.dict()}"
    )

    return new_json_file_content


def save_job_checkpoint(
    json_file_manager,
    json_repo,
    json_file_content,
    data_input_name,
    job_type,
    **json_file_content_metadata,
):
    # Checks whether the JSON File should be replaced with fresh one
    if json_file_manager.should_replace(json_file_content.created_at_datetime):
        logging.info(
            f"Job checkpoint start cleaning old data entries data_input={data_input_name}"
        )
        # Cleans records under `data` attribute in the JSON File
        # which are not modified for X days
        json_file_content = rollout_job_checkpoint_data(
            data_input_name,
            json_file_content,
            job_type,
            clean_period_in_days=json_file_manager.file_clean_period,
            **json_file_content_metadata,
        )
        logging.info(
            f"Job checkpoint old data entries successfully cleaned data_input={data_input_name}"
        )
    json_repo.update(data_input_name, json_file_content)

    return None


def add_failed_task_for_retry(failed_tasks, failed_task_func, additional_data):
    sleep_time = randint(1, 5)
    sleep(sleep_time)
    failed_tasks.append((failed_task_func, additional_data))

    return None


def resubmit_failed_tasks_for_retry(failed_tasks, thread_pool_executor):
    futures_for_retry = {}

    for failed_task_func, additional_data in failed_tasks:
        future = thread_pool_executor.submit(failed_task_func)
        futures_for_retry[future] = additional_data

    return futures_for_retry
