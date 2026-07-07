"""
Modular input for ingesting of Salesforce Commerce Cloud Logs from WebDAV
"""

import hashlib
import re
import logging

from time import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
from xml.etree import ElementTree
from uuid import uuid4
from os import environ
from os.path import join
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)
from functools import partial
from opentelemetry.sdk.metrics import view

from config import (
    REQUEST_PARAMETERS_W_STACKTRACE_PATTERN,
    REQUEST_PARAMETERS_W_STACKTRACE_SUBSTITUTE,
    REQUEST_PARAMETERS_PATTERN,
    REQUEST_PARAMETERS_SUBSTITUTE,
    LOG_FILE_CREATED_DATETIME_FORMAT,
    MESSAGE_SEPARATOR_PATTERN,
)
import otel
import utils
import license
import api_client
import file_manager


data_input_log_metric_views = [
    view.View(instrument_name="data_input.log.duration", aggregation=view.LastValueAggregation()),
    view.View(instrument_name="data_input.log.status", aggregation=view.LastValueAggregation()),
    view.View(instrument_name="data_input.log.webdav.client.errors", aggregation=view.SumAggregation()),
    view.View(instrument_name="data_input.log.sfcc.logs.count", aggregation=view.LastValueAggregation()),
    view.View(instrument_name="data_input.log.sfcc.logs.bytes.total", aggregation=view.LastValueAggregation()),
]
data_input_log_meter, data_input_log_metric_reader = otel.create_meter_provider(
    "sfcc-logs",
    data_input_log_metric_views
)
metric_data_input_duration = data_input_log_meter.create_histogram(
    "data_input.log.duration", unit="s", description="Measures the duration of data input"
)
metric_data_input_status = data_input_log_meter.create_up_down_counter(
    "data_input.log.status", unit="", description="Operational status of data input: 1 (completed) or 0 (failed)"
)
metric_data_input_errors = data_input_log_meter.create_counter(
    "data_input.log.errors",
    unit="{errors}",
    description="Count of errors raised during runtime"
)
metric_data_input_webdav_client_latency = data_input_log_meter.create_histogram(
    "data_input.log.webdav.client.latency",
    unit="s",
    description="Measures the time between a Salesforce Commerce WebDav client sending a request and receiving a response"
)
metric_data_input_webdav_client_errors = data_input_log_meter.create_counter(
    "data_input.log.webdav.client.errors",
    unit="{log}",
    description="Number of Salesforce Commerce WebDav errors"
)
metric_data_input_sfcc_logs_count = data_input_log_meter.create_counter(
    "data_input.log.sfcc.logs.count",
    unit="{log}",
    description="Count of Salesforce Logs file entries"
)
metric_data_input_sfcc_logs_bytes_total = data_input_log_meter.create_histogram(
    "data_input.log.sfcc.bytes.total",
    unit="{bytes}",
    description="Total bytes of Salesforce Logs for ingesting"
)


def create_common_data_input_log_metric_attributes(
    data_input_id,
    data_input_name,
    webdav_host,
    webdav_endpoint
):
    return {
        "data_input.id": data_input_id,
        "data_input.name": data_input_name,
        "data_input.webdav.host": webdav_host,
        "data_input.webdav.endpoint": webdav_endpoint
    }


def validate_input(helper, definition):
    """
    Validation of user inputs:
    WebDAV folder URL where the log files are served from (input parameter 'webdav_host_url').
    URL for the OAuth2.0 authentication (input parameter 'webdav_host_url').
    Checks if the urls are secured.

    :param helper: Splunk Add-On Builder Helper functions wrapper
    :param definition: Splunk Add-On Builder Definition
    :raises: ValueError if the given inputs are invalid
    """
    logs_url = definition.parameters.get('webdav_host_url', None)
    utils.enforce_secure_connection(logs_url)


def filter_webdav_folder_files(
    xml_content,
    filename_patterns,
    date_threshold,
):
    """
    Filters the PROPFIND response returned from the SFCC WebDAV server
    by creating a list of remote files that are eligible for indexing.
    Returns a list of dictionaries each representing a file and
    the byte range which is eligible for download.
    >>> {'file_name': 'warn-blade6-6.mon.demandware.net-0-appserver-20190725.log',
    >>>  'range_start': 45235,
    >>>  'range_end': 53257
    >>> }
    """
    root = ElementTree.fromstring(xml_content)
    file_list = []

    for xml_element in root.iter('{DAV:}response'):
        if xml_element.find('.//{DAV:}collection') is not None:
            logging.debug('Skipping WebDAV folder %s' % xml_element.find('.//{DAV:}href').text)
            continue

        log_file_creation_date = datetime.strptime(
            xml_element.find('.//{DAV:}creationdate').text,
            LOG_FILE_CREATED_DATETIME_FORMAT
        )

        log_file_name = xml_element.find('.//{DAV:}displayname').text
        if log_file_creation_date < date_threshold:
            logging.debug(
                'Skipping file because it is too old: %s created at %s' % (log_file_name, log_file_creation_date))
            continue

        if next(
            (pattern for pattern in list(filename_patterns.values()) if pattern.match(log_file_name)),
            None
        ) is None:
            logging.debug('Skipping file because it is not enabled for indexing: %s' % log_file_name)
            continue

        log_file_creation_date_str = log_file_creation_date.strftime(LOG_FILE_CREATED_DATETIME_FORMAT)
        range_end = int(xml_element.find('.//{DAV:}getcontentlength').text) - 1
        logging.debug('File is eligible for indexing: %s' % log_file_name)
        file_list.append(
            {
                'file_name': log_file_name,
                'file_creation_date': log_file_creation_date_str,
                'file_range_end': range_end
            }
        )

    return file_list


def filter_files_with_new_content_for_download(files, json_file_content):
    files_with_new_content = []

    for file_dikt in files:
        file_name = file_dikt["file_name"]
        file_range_end = file_dikt["file_range_end"]
        file_creation_date = file_dikt["file_creation_date"]
        checkpoint_key = hashlib.sha256(file_name.encode('utf-8')).hexdigest()
        range_start = 0
        if checkpoint_key not in json_file_content.data:
            json_file_content.data[checkpoint_key] = {
                "file_name": file_name,
                'created_at': file_creation_date,
                "last_ingested_at": datetime.now().strftime(json_file_content.datetime_format),
                "range_start": 0,
            }
        else:
            range_start = json_file_content.data[checkpoint_key].get("range_start", 0)

        if not (file_range_end > 0 and range_start < file_range_end):
            logging.debug(
                'Skipping file because it has not been changed after the last indexing: %s' % file_name
            )
            continue

        files_with_new_content.append(
            {
                'file_name': file_name,
                'file_creation_date': file_creation_date,
                'file_range_start': range_start,
                'file_range_end': file_range_end,
                "file_checkpoint_key": checkpoint_key
            }
        )

    return files_with_new_content


def obfuscate_sensitive_data(contents, file_name, file_name_patterns):
    """
    Obfuscate any personal or sensitive information.
    """
    if file_name_patterns["system_log_files_pattern"] and file_name_patterns["system_log_files_pattern"].match(
            file_name):
        # message contains stacktrace, we want to preserve it for investigation purposes
        if re.search(REQUEST_PARAMETERS_W_STACKTRACE_PATTERN, contents):
            return re.sub(REQUEST_PARAMETERS_W_STACKTRACE_PATTERN, REQUEST_PARAMETERS_W_STACKTRACE_SUBSTITUTE, contents)

        # message does not contain stacktrace, we omit everything after the "Request Parameters"
        elif re.search(REQUEST_PARAMETERS_PATTERN, contents):
            return re.sub(REQUEST_PARAMETERS_PATTERN, REQUEST_PARAMETERS_SUBSTITUTE, contents)

    return contents


def write_events(url, file_content, file_name, filename_patterns, helper, ew):
    # Split file content by multiple delimiters which are timestamps
    # Pattern [<log_timestamp>, <log_line>, ..., <log_timestamp>, <log_line>]
    log_entries = MESSAGE_SEPARATOR_PATTERN.split(file_content)
    last_timestamp = ""
    parsed_url = urlparse(url)
    for log_entry in log_entries:
        if log_entry and log_entry.strip() != '':
            if MESSAGE_SEPARATOR_PATTERN.match(log_entry):
                last_timestamp = log_entry
            else:
                contents = obfuscate_sensitive_data(last_timestamp + log_entry, file_name, filename_patterns)
                event = helper.new_event(
                    data=contents,
                    host=parsed_url.netloc,
                    index=helper.get_output_index(),
                    source=file_name
                )
                ew.write_event(event)


def insure_save_job_checkpoint(
    data_input_name,
    json_repo,
    json_file_content,
    last_saved_datetime,
    trigger_save_at_in_seconds=50
):
    if json_repo is None:
        logging.debug(
            f"Skip insure saving job checkpoint data_input_name={data_input_name} json_repo={json_repo}"
        )
        return None

    current_datetime = datetime.now()
    substracted_datetime = current_datetime - last_saved_datetime

    if not substracted_datetime.seconds >= trigger_save_at_in_seconds:
        logging.debug(
            f"Time for insure saving job checkpoint not reached data_input_name={data_input_name} current_seconds={substracted_datetime.seconds}"
        )
        return None

    json_repo.update(data_input_name, json_file_content)
    logging.info(
        f"Insure saving job checkpoint saved data_input_name={data_input_name}"
    )

    return "ok"


@license.license_required
def collect_events(helper, ew):
    unique_id               = str(uuid4())
    data_input_name         = helper.get_arg('name')
    webdav_host_url         = helper.get_arg('webdav_host_url')
    webdav_endpoint         = helper.get_arg('webdav_endpoint')
    ocapi_credentials       = helper.get_arg('ocapi_credentials')
    days_threshold          = int(helper.get_arg('days_threshold'))
    try:
        utils.init_program_termination_handlers(unique_id, data_input_name, helper)
        utils.enforce_secure_connection(webdav_host_url)
        data_input_log_start_time = time()
        common_data_input_log_metric_attrs = create_common_data_input_log_metric_attributes(
            unique_id,
            data_input_name,
            webdav_host_url,
            webdav_endpoint
        )
        metric_data_input_status.add(0, attributes=common_data_input_log_metric_attrs)
        logging.info(
            f'Starting logs ingestion data_input={data_input_name} id={unique_id} host={webdav_host_url} endpoint={webdav_endpoint}'
        )
        date_threshold          = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_threshold)
        log_filename_patterns   = utils.get_filename_patterns(helper)
        json_file_manager       = file_manager.JSONFileManager(
                                    join(
                                        environ.get("SPLUNK_HOME", "/opt/splunk"),
                                        "var",
                                        "lib",
                                        "splunk",
                                        "modinputs",
                                        "salesforce_commerce_cloud_logs_v2"
                                    )
                                )
        json_repo               = file_manager.JSONFileRepository(json_file_manager)
        json_file_content       = utils.get_job_checkpoint(json_repo, data_input_name, "files")
        file_last_saved_at      = datetime.now()
        log_api_client  = api_client.SalesforceLogAPIClient(
            webdav_host_url,
            webdav_endpoint,
            ocapi_credentials["username"],
            ocapi_credentials["password"]
        )
        webdav_url = log_api_client.url
        webdav_response = log_api_client.list_webdav_files()
        webdav_content = webdav_response.content.decode('utf8')
        logging.debug(
            'Going to index log files with names matching: %s data_input=%s id=%s' % (log_filename_patterns, data_input_name, unique_id)
        )
        eligible_files = filter_webdav_folder_files(
            webdav_content,
            log_filename_patterns,
            date_threshold,
        )
        logging.info(f"Eligible files count={len(eligible_files)}")
        files_with_new_content = filter_files_with_new_content_for_download(eligible_files, json_file_content)
        logging.info(f"Files with new content count={len(files_with_new_content)}")
        logging.info(
            f'Files data_input={data_input_name} id={unique_id} indexed={files_with_new_content} count={len(files_with_new_content)}'
        )
        total_files_bytes = sum(
            [log_file.get('file_range_end', 0) - log_file.get('file_range_start', 0) for log_file in files_with_new_content]
        )
        metric_data_input_sfcc_logs_bytes_total.record(
            total_files_bytes,
            attributes=common_data_input_log_metric_attrs
        )
        logging.info('Files bytes to read data_input=%s id=%s total_bytes=%s' % (data_input_name, unique_id, total_files_bytes))
        # After a few tests, it was found that the thread pool performs
        # best and remains stable with a maximum of 4 workers.
        thread_workers_count = 4
        with ThreadPoolExecutor(
            max_workers=thread_workers_count,
            thread_name_prefix='LogsWorkersPool'
        ) as executor:
            files_futures = {}
            files_failed_tasks = []
            webdav_requests_start_time = time()
            for file_info in files_with_new_content:
                file_byte_start_range = file_info['file_range_start']
                file_byte_end_range = file_info['file_range_end']
                file_future = executor.submit(
                    log_api_client.get_file_content,
                    file_info['file_name'],
                    file_byte_start_range,
                    file_byte_end_range
                )
                files_futures[file_future] = file_info
            logging.debug(f"Workers count={len(files_futures)} objects={files_futures}")
            for future in as_completed(files_futures):
                if future.exception():
                    future_exc = future.exception()
                    logging.exception(f"Task has failed reason={future_exc}")
                    # Get the associated data for the task
                    file_data = files_futures[future]
                    # Submit the task again
                    file_failed_task_func = partial(
                        log_api_client.get_file_content,
                        file_data['file_name'],
                        file_data['file_range_start'],
                        file_data['file_range_end']
                    )
                    # Add failed task into retry list
                    utils.add_failed_task_for_retry(
                        files_failed_tasks,
                        file_failed_task_func,
                        file_data
                    )
                    metric_data_input_webdav_client_errors.add(
                        1,
                        attributes=otel.create_exception_metric_attributes(str(type(future_exc)), "null")
                    )
                    # Continue to the next task
                    continue
                file_info = files_futures[future]
                response = future.result()
                log_message = response.content.decode("utf-8")
                # Get the response time of the WebDav client in seconds
                webdav_client_response_time = otel.measure_duration_in_seconds(webdav_requests_start_time)
                # Record the response time of the WebDav client in seconds
                metric_data_input_webdav_client_latency.record(
                    webdav_client_response_time,
                    attributes=common_data_input_log_metric_attrs
                )
                logging.info(f"Processing file={file_info['file_name']}")
                write_events(
                    webdav_url,
                    log_message,
                    file_info.get('file_name'),
                    log_filename_patterns,
                    helper,
                    ew,
                )
                json_file_content.data[file_info['file_checkpoint_key']] = {
                    "file_name": file_info['file_name'],
                    'created_at': file_info['file_creation_date'],
                    "last_ingested_at": datetime.now().strftime(json_file_content.datetime_format),
                    "range_start": file_info['file_range_end'],
                }
                status = insure_save_job_checkpoint(data_input_name, json_repo, json_file_content, file_last_saved_at)
                if status == "ok":
                    # Update time determining last saved checkpoint of the file
                    file_last_saved_at = datetime.now()
            # Check for failed tasks for retry
            if files_failed_tasks:
                logging.info(f"Failed tasks count={len(files_failed_tasks)}")
                files_futures_retries = utils.resubmit_failed_tasks_for_retry(files_failed_tasks, executor)
                logging.info(f"Workers to retry failed tasks count={len(files_futures_retries)}")
                for retried_future in as_completed(files_futures_retries):
                    file_info = files_futures_retries[retried_future]
                    response = retried_future.result()
                    log_message = response.content.decode("utf-8")
                    logging.info(f"Processing retried file={file_info['file_name']}")
                    write_events(
                        webdav_url,
                        log_message,
                        file_info.get('file_name'),
                        log_filename_patterns,
                        helper,
                        ew,
                    )
                    json_file_content.data[file_info['file_checkpoint_key']] = {
                        "file_name": file_info['file_name'],
                        'created_at': file_info['file_creation_date'],
                        "last_ingested_at": datetime.now().strftime(json_file_content.datetime_format),
                        "range_start": file_info['file_range_end'],
                    }
        # Record the count of Salesforce Logs read and ingested
        metric_data_input_sfcc_logs_count.add(len(files_with_new_content), attributes=common_data_input_log_metric_attrs)
        utils.save_job_checkpoint(
            json_file_manager,
            json_repo,
            json_file_content,
            data_input_name,
            "files"
        )
        logging.info(
            f'Finish logs ingestion data_input={data_input_name} id={unique_id} host={webdav_host_url} endpoint={webdav_endpoint}'
        )
        metric_data_input_status.add(1, attributes=common_data_input_log_metric_attrs)
        # Get the duration of the OCAPI client in seconds
        data_input_duration_in_seconds = otel.measure_duration_in_seconds(
            data_input_log_start_time
        )
        # Record the duration of the input
        metric_data_input_duration.record(
            data_input_duration_in_seconds,
            attributes=common_data_input_log_metric_attrs
        )
        otel.log_metrics_in_console(data_input_log_metric_reader)
    except (
        api_client.APIRetryError,
        api_client.APIReadTimeoutError,
        api_client.APIClientOrServerError,
        api_client.APIResponseBodyDecodeError,
    ) as webdav_client_err:
        exception_type = str(type(webdav_client_err))
        exception_msg = webdav_client_err.exc_msg
        logging.error(
            f'[ERROR][WebDAVError] Logs ingestion data_input={data_input_name} id={unique_id} exception={exception_type} message={exception_msg}',
        )
        metric_data_input_errors.add(
            1,
            attributes=otel.create_exception_metric_attributes(exception_type, exception_msg)
        )
        otel.log_metrics_in_console(data_input_log_metric_reader, log_info="ERROR")
    except file_manager.JSONFileDecodeError as json_file_decode_err:
        exception_type = str(type(json_file_decode_err))
        exception_msg = json_file_decode_err.exc_msg
        logging.error(
            f'[ERROR][File Checkpoint] Failed to load file data_input={data_input_name} id={unique_id} exception={exception_type} message={exception_msg} file={json_file_decode_err.fname}',
        )
        metric_data_input_errors.add(
            1,
            attributes=otel.create_exception_metric_attributes(exception_type, exception_msg)
        )
        otel.log_metrics_in_console(data_input_log_metric_reader, log_info="ERROR")
    except Exception as error:
        exception_type = str(type(error))
        exception_msg = str(error)
        logging.error(
            f'[ERROR] Logs ingestion data_input={data_input_name} id={unique_id} exception={exception_type} message={exception_msg}',
        )
        metric_data_input_errors.add(
            1,
            attributes=otel.create_exception_metric_attributes(exception_type, exception_msg)
        )
        otel.log_metrics_in_console(data_input_log_metric_reader, log_info="ERROR")
        raise error