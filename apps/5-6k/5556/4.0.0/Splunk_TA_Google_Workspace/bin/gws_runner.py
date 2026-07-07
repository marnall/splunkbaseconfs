#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import concurrent.futures
import http
import json
import logging
import math
import time
from typing import Optional, Dict, Any, Tuple, List, Generator

import google_auth_httplib2
import googleapiclient.discovery
import googleapiclient.errors
import httplib2
from google.oauth2 import service_account
from solnlib import modular_input
from solnlib import log

import gws_checkpoint
from gws_preprocess import split_events
import gws_utils
from splunklib import modularinput as smi

CHUNK_SECONDS = 20
# In ideal scenario when end_time - start_time is exactly CHUNK_SECONDS, we
# want to have 5 intervals which are 4 seconds each.
# This is not the case all the time. Imagine a modular input running with 1
# minute interval, it may be a case that Splunk schedules a modular input to run
# after 1 minute and 1 second. In this case, first 3 results from
# yield_query_intervals function will be ideal size, but 4th one will be one
# element in the list with 1 second interval size.
# This value should be the same default value as in globalConfig for the
# "activity_report_interval_size" field.
OPTIMAL_INTERVAL_SIZE_SECONDS = 4
MAX_RESULTS = 1000
NUM_RETRIES = 3
UNSUCCESSFUL_RUNS_LIMIT = 30


def _get_activities(
    logger: logging.Logger,
    service: googleapiclient.discovery.Resource,
    authorized_http: google_auth_httplib2.AuthorizedHttp,
    start_time: str,
    end_time: str,
    application: str,
    page_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns a page of events from Google Workspace API, but could also report
    time spent if log level is DEBUG.
    """
    request_start_time = time.time()
    activities = (
        service.activities()
        .list(
            userKey="all",
            startTime=start_time,
            endTime=end_time,
            applicationName=application,
            maxResults=MAX_RESULTS,
            pageToken=page_token,
        )
        .execute(http=authorized_http, num_retries=NUM_RETRIES)
    )
    request_end_time = time.time()
    request_time = round(request_end_time - request_start_time, 4)
    logger.debug(f"Request took {request_time} seconds")
    return activities


def _get_customerUsageReports(
    logger: logging.Logger,
    service: googleapiclient.discovery.Resource,
    authorized_http: google_auth_httplib2.AuthorizedHttp,
    date: str,
) -> List[str]:
    """
    Returns customerUsageReports from Google API
    :param logger: logger object
    :param service: google API resource
    :param authorized_http: A httplib2 HTTP class with credentials
    :param date: date for API call
    :return items: reports from API
    """
    usage_reports = (
        service.customerUsageReports()
        .get(
            date=date,
        )
        .execute(http=authorized_http, num_retries=NUM_RETRIES)
    )
    items = usage_reports.get("usageReports", [])
    next_page_token = usage_reports.get("nextPageToken", "")
    while next_page_token:
        usage_reports = (
            service.customerUsageReports()
            .get(
                date=date,
                pageToken=next_page_token,
            )
            .execute(http=authorized_http, num_retries=NUM_RETRIES)
        )
        next_page_token = usage_reports.get("nextPageToken", "")
        items.extend(usage_reports.get("usageReports", []))

    return items


def _get_entityUsageReports(
    logger: logging.Logger,
    service: googleapiclient.discovery.Resource,
    authorized_http: google_auth_httplib2.AuthorizedHttp,
    date: str,
) -> List[str]:
    """
    Returns entityUsageReports from Google API
    :param logger: logger object
    :param service: google API resource
    :param authorized_http: A httplib2 HTTP class with credentials
    :param date: date for API call
    :return items: reports from API
    """
    usage_reports = (
        service.entityUsageReports()
        .get(
            date=date,
            entityType="gplus_communities",
            entityKey="all",
        )
        .execute(http=authorized_http, num_retries=NUM_RETRIES)
    )
    items = usage_reports.get("usageReports", [])
    next_page_token = usage_reports.get("nextPageToken", "")
    while next_page_token:
        usage_reports = (
            service.entityUsageReports()
            .get(
                date=date,
                pageToken=next_page_token,
                entityKey="all",
                entityType="gplus_communities",
            )
            .execute(http=authorized_http, num_retries=NUM_RETRIES)
        )
        next_page_token = usage_reports.get("nextPageToken", "")
        items.extend(usage_reports.get("usageReports", []))

    return items


def _get_userUsageReports(
    logger: logging.Logger,
    service: googleapiclient.discovery.Resource,
    authorized_http: google_auth_httplib2.AuthorizedHttp,
    date: str,
) -> List[str]:
    """
    Returns userUsageReports from Google API
    :param logger: logger object
    :param service: google API resource
    :param authorized_http: A httplib2 HTTP class with credentials
    :param date: date for API call
    :return items: reports from API
    """
    usage_reports = (
        service.userUsageReport()
        .get(
            date=date,
            userKey="all",
        )
        .execute(http=authorized_http, num_retries=NUM_RETRIES)
    )
    items = usage_reports.get("usageReports", [])
    next_page_token = usage_reports.get("nextPageToken", "")
    while next_page_token:
        usage_reports = (
            service.userUsageReport()
            .get(
                date=date,
                pageToken=next_page_token,
                userKey="all",
            )
            .execute(http=authorized_http, num_retries=NUM_RETRIES)
        )
        next_page_token = usage_reports.get("nextPageToken", "")
        items.extend(usage_reports.get("usageReports", []))

    return items


def _get_unsuccessful_runs(
    unsuccessful_runs_checkpointer: modular_input.KVStoreCheckpointer,
) -> List[List[str]]:
    # Returns list (maybe empty) of unsuccessful runs.
    unsuccessful_runs = unsuccessful_runs_checkpointer.get(
        gws_utils.ACTIVITY_REPORT_UNSUCCESSFUL_RUNS_COLLECTION_KEY
    )
    return [] if unsuccessful_runs is None else unsuccessful_runs


def _update_unsuccessful_intervals_from_run(
    logger: logging.Logger,
    unsuccessful_runs_checkpointer: modular_input.KVStoreCheckpointer,
    successful_runs: List[List[str]],
    unsuccessful_runs: List[List[str]],
):
    # Updates KVStore collection for unsuccessful runs taking into account
    # last successful and unsuccessful runs.
    # Removes any successful run which was found in the collection and adds
    # all the unsuccessful runs into the collection.
    unsuccessful_runs_in_kvstore = _get_unsuccessful_runs(
        unsuccessful_runs_checkpointer
    )
    updated_unsuccessful_runs = []
    for unsuccessful_run_in_kvstore in unsuccessful_runs_in_kvstore:
        if unsuccessful_run_in_kvstore in successful_runs:
            continue
        else:
            updated_unsuccessful_runs.append(unsuccessful_run_in_kvstore)
    for unsuccessful_run in unsuccessful_runs:
        # This statement protects from duplicating unsuccessful runs.
        # Situation described below.
        # KVStore collection consists of 6 unsuccessful runs.
        # After rerunning:
        #   * second and third were successful.
        #   * first, fourth and fifth were not.
        # KVStore should be updated with first, fourth, fifth and sixth (as it
        # was not even run).
        if unsuccessful_run not in updated_unsuccessful_runs:
            updated_unsuccessful_runs.append(unsuccessful_run)
    logger.debug(
        f"Updating unsuccessful KVStore collection to {updated_unsuccessful_runs}"
    )
    unsuccessful_runs_checkpointer.update(
        gws_utils.ACTIVITY_REPORT_UNSUCCESSFUL_RUNS_COLLECTION_KEY,
        updated_unsuccessful_runs,
    )


def get_events(
    logger: logging.Logger,
    service_account_credentials: service_account.Credentials,
    application: str,
    start_time: str,
    end_time: str,
    proxy_config: Optional[Dict[str, Any]] = None,
):
    _http = gws_utils.build_http_connection(proxy_config)
    authorized_http = google_auth_httplib2.AuthorizedHttp(
        service_account_credentials, http=_http
    )
    service = googleapiclient.discovery.build(
        "admin",
        "reports_v1",
        credentials=service_account_credentials,
    )
    try:
        activities = _get_activities(
            logger,
            service,
            authorized_http,
            start_time,
            end_time,
            application,
        )
        items = activities.get("items", [])
        next_page_token = activities.get("nextPageToken", "")
        while next_page_token:
            activities = _get_activities(
                logger,
                service,
                authorized_http,
                start_time,
                end_time,
                application,
                page_token=next_page_token,
            )
            next_page_token = activities.get("nextPageToken", "")
            items.extend(activities.get("items", []))
        return items
    except (googleapiclient.errors.HttpError, httplib2.HttpLib2Error):
        # There are the exceptions declared here: https://github.com/googleapis/google-api-python-client/blob/main/googleapiclient/http.py#L892-L894.
        raise
    except Exception as e:
        logger.error(f"Exception raised while getting events: {e}")
        raise


def get_events_threaded(
    logger: logging.Logger,
    service_account_credentials: service_account.Credentials,
    application: str,
    intervals: List[List[str]],
    unsuccessful_runs_checkpointer: modular_input.KVStoreCheckpointer,
    proxy_config: Optional[Dict[str, Any]] = None,
) -> List:
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(intervals)) as executor:
        future_to_job = {
            executor.submit(
                get_events,
                logger,
                service_account_credentials,
                application,
                interval[0],
                interval[1],
                proxy_config,
            ): interval
            for interval in intervals
        }
        successful_runs = []
        unsuccessful_runs = []
        for future in concurrent.futures.as_completed(future_to_job):
            interval = future_to_job[future]
            try:
                items.extend(future.result())
                successful_runs.append(interval)
            except googleapiclient.errors.HttpError as exc:
                if exc.status_code == http.HTTPStatus.BAD_REQUEST:
                    logger.error(
                        f"Bad request exception while getting events for '{interval}', "
                        f"not updating unsuccessful runs collection: {exc}"
                    )
                elif exc.status_code == http.HTTPStatus.UNAUTHORIZED:
                    # HTTP 401 is a permanent authorization failure — retrying the same
                    # interval will not fix a permissions misconfiguration.
                    # The delegated "Administrator email" account must be a Google Workspace
                    # Super Admin, or hold a custom admin role with Reports › Audit read
                    # privileges and the matching OAuth scope authorised via domain-wide
                    # delegation. This interval is intentionally not added to unsuccessful_runs.
                    logger.error(
                        f"HTTP 401 Unauthorized while getting events for '{interval}': {exc}. "
                        "The 'Administrator email' account configured for this input does not have "
                        "permission to read Google Admin activity records. "
                        "Required: a Google Workspace Super Admin account, or a custom admin role "
                        "with 'Reports > Audit' read privileges and domain-wide delegation configured "
                        "in Google Admin Console → Security → API controls → Domain-wide delegation. "
                        "This interval will not be retried — fix the account permissions first."
                    )
                else:
                    log.log_exception(
                        logger,
                        exc,
                        "HttpError",
                        msg_before=f"Exception while getting events for '{interval}': {exc}",
                    )
                    unsuccessful_runs.append(interval)
            except Exception as exc:
                log.log_exception(
                    logger,
                    exc,
                    "GetEventsError",
                    msg_before=f"Exception while getting events for '{interval}': {exc}",
                )
                unsuccessful_runs.append(interval)
    _update_unsuccessful_intervals_from_run(
        logger,
        unsuccessful_runs_checkpointer,
        successful_runs,
        unsuccessful_runs,
    )
    return items


def _split_start_end_interval(
    logger: logging.Logger,
    start_time: str,
    end_time: str,
    number_of_intervals: int,
    unsuccessful_runs: List[List[str]],
) -> Tuple[List[List[str]], Optional[str]]:
    """
    Returns intervals from start_time and end_time based on number_of_intervals
    and unsuccessful_runs from the past runs. If there are any unsuccessful_runs
    those will be before the intervals calculated based on start and end time.

    The add-on executes requests to Google Workspace API based on the CHUNK_SIZE
    variable defined in this file.
    """
    if len(unsuccessful_runs) >= number_of_intervals:
        logger.info("Taking unsuccessful runs intervals only")
        return unsuccessful_runs[:number_of_intervals], None
    start_time_seconds = gws_checkpoint.str_to_seconds(start_time)
    end_time_seconds = gws_checkpoint.str_to_seconds(end_time)
    interval_range_seconds_raw = (
        end_time_seconds - start_time_seconds
    ) / number_of_intervals
    # This covers the scenario when difference between end_time and start_time
    # is less than the number_of_intervals. It means that there is no need to
    # split it even further.
    if interval_range_seconds_raw < 1:
        return [[start_time, end_time]], end_time
    interval_range_seconds = math.ceil(interval_range_seconds_raw)
    intervals = []
    interval_start_seconds = start_time_seconds
    while interval_start_seconds + interval_range_seconds < end_time_seconds:
        interval_end_seconds = interval_start_seconds + interval_range_seconds
        intervals.append(
            [
                gws_checkpoint.seconds_to_str(interval_start_seconds),
                gws_checkpoint.seconds_to_str(interval_end_seconds),
            ]
        )
        interval_start_seconds = interval_end_seconds
    intervals.append(
        [
            gws_checkpoint.seconds_to_str(interval_start_seconds),
            gws_checkpoint.seconds_to_str(end_time_seconds),
        ]
    )
    # unsuccessful_runs should be sorted, so we can take the oldest unsuccessful
    # to be processed again first.
    for unsuccessful_run in reversed(unsuccessful_runs):
        intervals.insert(0, unsuccessful_run)
    size_aware_intervals = intervals[:number_of_intervals]
    # Taking the end time from the last interval.
    return size_aware_intervals, size_aware_intervals[-1][1]


def yield_query_intervals(
    logger: logging.Logger,
    initial_start_time: str,
    initial_end_time: str,
    number_of_intervals: int,
    unsuccessful_runs_checkpointer: modular_input.KVStoreCheckpointer,
) -> Generator[List[List[str]], None, None]:
    """
    Yields intervals for querying Google Workspace Activity Report API.
    """

    def _calculate_end_time(start_time: str) -> str:
        end_time_seconds = gws_checkpoint.str_to_seconds(start_time) + CHUNK_SECONDS
        if end_time_seconds > initial_end_time_seconds:
            return gws_checkpoint.seconds_to_str(initial_end_time_seconds)
        return gws_checkpoint.seconds_to_str(end_time_seconds)

    start_time = initial_start_time
    initial_end_time_seconds = gws_checkpoint.str_to_seconds(initial_end_time)
    end_time = _calculate_end_time(start_time)
    unsuccessful_runs_counter = 0
    while True:
        unsuccessful_runs = _get_unsuccessful_runs(unsuccessful_runs_checkpointer)
        logger.info(f"Unsuccessful intervals: {unsuccessful_runs}")
        intervals, checkpoint_str = _split_start_end_interval(
            logger,
            start_time,
            end_time,
            number_of_intervals,
            unsuccessful_runs,
        )
        logger.debug(
            f"Intervals to query: {intervals}, checkpoint to save: {checkpoint_str}"
        )

        if len(unsuccessful_runs) == number_of_intervals:
            logger.debug(
                f"Timeout while requesting data for unsuccessful runs. Waiting: {unsuccessful_runs_counter}s"
            )
            time.sleep(unsuccessful_runs_counter)
            unsuccessful_runs_counter += 1

        yield intervals, checkpoint_str

        if unsuccessful_runs_counter == UNSUCCESSFUL_RUNS_LIMIT:
            logger.info(
                f"Counter of unsuccessful runs reached its limit of {UNSUCCESSFUL_RUNS_LIMIT}. Stopping..."
            )
            break
        # If checkpoint_str is None, it means that intervals consist only of
        # unsuccessful_runs and there is no need to move start and end time.
        if checkpoint_str is not None:
            start_time = checkpoint_str
            end_time = _calculate_end_time(start_time)
            if gws_checkpoint.str_to_seconds(start_time) >= initial_end_time_seconds:
                break


def run_ingest(
    logger: logging.Logger,
    session_key: str,
    account: str,
    input_name: str,
    application: str,
    lookback_offset: str,
    event_writer: smi.EventWriter,
    kvstore_checkpointer: modular_input.KVStoreCheckpointer,
    input_index: str,
):
    """
    All the steps involved in the pipeline to ingest data for application
    configured.
    :param logger: Logger object
    :param session_key: Splunk session key
    :param account: Account name to use for this input
    :param input_name: Name of the input
    :param application: Google Workspace application name to query
    :param lookback_offset: When to start looking at the data
    :param event_writer: Splunk event writer
    :param kvstore_checkpointer: Splunk KVStore client
    :param input_index: input index for monitoring dashboard
    :return: None
    """
    logger.debug("Getting proxy settings")
    proxy_config = gws_utils.get_proxy_settings(logger, session_key)
    proxies = gws_utils.build_proxies_from_proxy_config(proxy_config)

    logger.debug("Getting service account credentials")
    try:
        num_retries = 5
        service_account_credentials = gws_utils.get_service_account_credentials(
            logger,
            session_key,
            account,
            [gws_utils.ACTIVITY_REPORT_SCOPE],
            proxies,
            num_retries,
        )
    except gws_utils.CouldNotRefreshCredentialsException:
        logger.error(
            f"Could not obtain an access token for account '{account}'. "
            "If the error above mentions 'unauthorized_client', domain-wide delegation is "
            "not configured for this service account or the delegated 'Administrator email' "
            "lacks the required OAuth scopes in Google Admin Console → Security → API controls "
            "→ Domain-wide delegation. "
            "Ingestion will not proceed until the account configuration is corrected."
        )
        raise

    normalized_input_name = input_name.replace("/", "_")

    (
        initial_start_time,
        initial_end_time,
    ) = gws_checkpoint.get_start_end_times_for_activity_report_from_kvstore(
        logger, lookback_offset, kvstore_checkpointer
    )
    if initial_start_time == initial_end_time:
        checkpoint_time = gws_checkpoint.str_to_seconds(initial_end_time)
        logger.info(
            "Start and end time intervals are equal, probably the first run, "
            "saving checkpoint and doing nothing."
        )
        logger.info(
            f"Saving checkpoint {initial_end_time} UTC, seconds {checkpoint_time}"
        )
        gws_checkpoint.save_checkpoint_to_kvstore(kvstore_checkpointer, checkpoint_time)
        return

    split_events_count = 0

    collection_name = (
        gws_utils.get_activity_report_unsuccessful_runs_collection_name_from_full_name(
            input_name
        )
    )
    logger.debug(f"Creating KVStore collection {collection_name}")
    unsuccessful_runs_checkpointer = modular_input.KVStoreCheckpointer(
        collection_name,
        session_key,
        gws_utils.APP_NAME,
    )
    advanced_settings = gws_utils.get_advanced_settings(logger, session_key)
    if advanced_settings is None:
        interval_size = OPTIMAL_INTERVAL_SIZE_SECONDS
    else:
        interval_size = advanced_settings.get("activity_report_interval_size")
    number_of_intervals = int(CHUNK_SECONDS / interval_size)

    for intervals, checkpoint_str in yield_query_intervals(
        logger,
        initial_start_time,
        initial_end_time,
        number_of_intervals,
        unsuccessful_runs_checkpointer,
    ):
        logger.info(f"Requesting data for the following intervals: {intervals}")
        try:
            items_from_google_api_response = get_events_threaded(
                logger,
                service_account_credentials,
                application,
                intervals,
                unsuccessful_runs_checkpointer,
                proxy_config,
            )
        except Exception:
            raise

        logger.info("Splitting events")
        events = split_events(items_from_google_api_response)

        split_events_count += len(events)

        sourcetype = f"gws:reports:{application}"
        log.events_ingested(
            logger,
            input_name,
            sourcetype,
            len(events),
            input_index,
        )
        for raw_event in events:
            event = smi.Event(
                data=json.dumps(raw_event, ensure_ascii=False, default=str),
                sourcetype=sourcetype,
            )
            event_writer.write_event(event)

        if checkpoint_str is not None:
            checkpoint_time = gws_checkpoint.str_to_seconds(checkpoint_str)
            logger.info(
                f"Saving checkpoint {checkpoint_str} UTC, seconds {checkpoint_time}"
            )
            gws_checkpoint.save_checkpoint_to_kvstore(
                kvstore_checkpointer, checkpoint_time
            )
        else:
            logger.info("Not updating checkpoint")
    if split_events_count == 0:
        logger.info("No events found")
    else:
        logger.info(f"Total split events ingested: {split_events_count}")
    logger.info("Runner finished")


def get_UsageReports(
    logger: logging.Logger,
    service: googleapiclient.discovery.Resource,
    authorized_http: google_auth_httplib2.AuthorizedHttp,
    date: str,
    applicationName: str,
) -> List[str]:
    """
    Function that returns a list of events from google API
    :param logger: Logger object
    :param service: google resource instance
    :param authorized_http: A httplib2 HTTP class with credentials.
    :param date: a date to query from API
    :param application: Google Workspace application name to query
    :return: List[str]
    """

    if applicationName == "customer":
        return _get_customerUsageReports(logger, service, authorized_http, date)

    elif applicationName == "user":
        return _get_userUsageReports(logger, service, authorized_http, date)

    elif applicationName == "entity":
        return _get_entityUsageReports(logger, service, authorized_http, date)
