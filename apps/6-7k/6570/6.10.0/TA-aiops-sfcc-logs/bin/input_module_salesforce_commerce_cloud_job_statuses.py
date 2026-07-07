# encoding = utf-8

import time
import json
import logging

from uuid import uuid4
from os import environ
from os.path import join
from datetime import datetime, timedelta
from config import CREATED_DATETIME_FORMAT

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, view
from opentelemetry.sdk.metrics.export import (
    InMemoryMetricReader,
)
from opentelemetry.sdk.resources import Resource

import utils
import file_manager
import license

metric_reader = InMemoryMetricReader()
provider = MeterProvider(
    resource=Resource.create(
        {
            "service.name": "sfcc-jobs",
            "service.namespace": "DataInput",
            "service.instance.id": "627cc493-f310-47de-96bd-71410b7dec09",
        }
    ),
    views=[
        view.View(instrument_name="data_input.duration", aggregation=view.LastValueAggregation()),
        view.View(instrument_name="data_input.status", aggregation=view.LastValueAggregation()),
        view.View(instrument_name="data_input.ocapi.client.duration", aggregation=view.LastValueAggregation()),
        view.View(instrument_name="data_input.sfcc.jobs.count", aggregation=view.SumAggregation()),
        view.View(instrument_name="data_input.sfcc.steps.count", aggregation=view.SumAggregation()),
    ],
    metric_readers=[metric_reader]
)

# Sets the global default meter provider
metrics.set_meter_provider(provider)
# Creates a meter from the global meter provider
meter = metrics.get_meter(__name__)
metric_data_input_duration = meter.create_histogram(
    "data_input.job.duration", unit="s", description="Measures the duration of data input"
)
metric_data_input_status = meter.create_up_down_counter(
    "data_input.job.status", unit="", description="Operational status of data input: 1 (completed) or 0 (failed)"
)
metric_data_input_ocapi_client_duration = meter.create_histogram(
    "data_input.job.ocapi.client.duration",
    unit="s",
    description="Measures the duration of outbound Salesforce Commerce Cloud Open Commerce API HTTP requests"
)
metric_data_input_ocapi_client_response_time = meter.create_histogram(
    "data_input.job.ocapi.client.response_time",
    unit="s",
    description="Measures the time between a Salesforce Commerce Cloud Open Commerce API client sending a request and receiving a response"
)
metric_data_input_ocapi_client_errors = meter.create_counter(
    "data_input.job.ocapi.client.errors",
    unit="{error}",
    description="Number of Salesforce Commerce Cloud Open Commerce API errors"
)
metric_data_input_sfcc_jobs_count = meter.create_counter(
    "data_input.job.sfcc.jobs.count",
    unit="{job}",
    description="Count of Salesforce Jobs data entries"
)
metric_data_input_sfcc_steps_count = meter.create_counter(
    "data_input.job.sfcc.steps.count",
    unit="{step}",
    description="Count of Salesforce Job Steps data entries"
)


def log_opentelemetry_metrics(metric_collector, helper, log_info="INFO"):
    metrics = metric_collector.get_metrics_data()
    metrics_json = json.loads(metrics.to_json())

    if log_info == "INFO":
        logging.info(f"Metrics metrics={metrics_json}")
    elif log_info == "ERROR":
        logging.error(f"Metrics metrics={metrics_json}")

    return None


def get_common_metric_attributes(data_input_id, data_input_name):
    return {
        "data_input.id": data_input_id,
        "data_input.name": data_input_name
    }


def get_ocapi_client_metric_attributes(
    url,
    http_request_method,
    http_response_code,
    http_response_body
):
    attributes = {"server.address": url}

    if http_request_method is not None:
        attributes["http.request.method"] = http_request_method,

    if http_response_code is not None:
        attributes["http.response.status_code"] = http_response_code

    if http_response_body is not None:
        attributes["http.response.body"] = http_response_body

    return attributes


def measure_duration_in_seconds(start_time):
    end_time = time.time()

    return end_time - start_time


def get_time_buffer_in_seconds(time_buffer):
    if time_buffer is None:
        return timedelta(seconds=0)
    elif isinstance(time_buffer, str) and time_buffer != "":
        return timedelta(seconds=int(time_buffer))

    return timedelta(seconds=0)


def validate_input(helper, definition):
    return None


def write_to_index(ew, source, data, helper, ocapi_hostname):
    event = helper.new_event(
        data=json.dumps(data),
        host=ocapi_hostname,
        index=helper.get_output_index(),
        source=source,
    )
    ew.write_event(event)


def build_request_body(from_datetime, to_datetime, **kwargs):
    request_body = {
        "query" : {
            "filtered_query": {
                    "filter": {
                        "range_filter": {
                            "field": "end_time",
                            "from_inclusive": True,
                            "from": from_datetime,
                            "to_inclusive": True,
                            "to": to_datetime
                        }
                    },
                    "query": {
                        "match_all_query": {}
                    }
                }
        },
        "sorts":[{"field":"start_time", "sort_order":"asc"}]
    }

    if kwargs:
        request_body.update(kwargs)

    return request_body


def running_jobs_query(from_datetime, to_datetime, **kwargs):
    request_body = {
        "query" : {
            "filtered_query": {
                    "filter": {
                        "range_filter": {
                            "field": "start_time",
                            "from_inclusive": True,
                            "from": from_datetime,
                            "to_inclusive": True,
                            "to": to_datetime
                        }
                    },
                    "query": {
                        "term_query": { "fields": ["status"], "operator": "is", "values": ["RUNNING"] }
                    }
                }
        },
        "sorts":[{"field":"start_time", "sort_order":"asc"}]
    }

    if kwargs:
        request_body.update(kwargs)

    return request_body


def create_job_event(job_data):
    return {
        # Type of the object
        "type": "job",
        # Name of the job, this execution belongs to
        "job_name": job_data.get("job_id"),
        # Description of the job, this execution belongs to. Name of the job
        "job_description": job_data.get("job_description"),
        # ID of the execution job
        "execution_id": job_data.get("id"),
        # Timestamp, when execution was started
        "start_time": job_data.get("start_time"),
        # Timestamp, when execution was finished
        "end_time": job_data.get("end_time"),
        # Time in milliseconds, the execution was or is running
        "duration": job_data.get("duration"),
        # Time in milliseconds, the job has done work. Paused times are evicted
        "effective_duration": job_data.get("effective_duration"),
        # The current status. If the job execution is not executed currently anymore
        # (execution status is one one 'finished', 'paused' or 'aborted')
        "status": job_data.get("status"),
        # Status shows successful operation end
        "job_status": job_data.get("exit_status", {}).get("status", None),
        # Status code typically OK or ERROR
        "exit_status_code": job_data.get("exit_status", {}).get("code", None),
        # Status message, often not populated and returns null
        "status_message": job_data.get("exit_status", {}).get("message", None),
        # Hardcoded message that our Splunk searches rely on
        "message": "Execution of job finished",
        # Full WebDAV path of the log file, containing execution log
        "log_file_path": job_data.get("log_file_path"),
        # Sorted set of all execution scopes, used by individual steps
        "execution_scopes": job_data.get("execution_scopes"),
        # Current execution status of the step:
        #   pending, running, pausing, paused, resuming, resumed, restarting, restarted, retrying, retried, aborting, aborted, finished, unknown
        "execution_status": job_data.get("execution_status"),
        # The continuation information of this execution if available
        "continue_information": job_data.get("continue_information"),
        # Status metadata which includes client ID that is responsible,
        # reason of the status and user login that is responsible for the status
        "status_metadata": job_data.get("status_metadata"),
        # The retry information of this execution if available
        "retry_information": job_data.get("retry_information"),
    }


def create_step_event(job_data, step_data):
    return {
        # Type of the object
        "type": "step",
        # Name of the job, this execution belongs to
        "job_name": job_data.get("job_id"),
        # ID of the execution job
        "job_execution_id": job_data.get("id"),
        # Name of the step, this execution belongs to
        "step_name": step_data.get("step_id"),
        # Description of the step, this execution belongs to. Name of the step
        "step_description": step_data.get("step_description"),
        # The current status. If the step execution is not executed currently anymore
        # (execution status is one one 'finished', 'paused' or 'aborted') the exit status code of the step execution is returned.
        "step_status": step_data.get("status"),
        # Timestamp, when execution was started
        "start_time": step_data.get("start_time"),
        # Timestamp, when execution was finished
        "end_time": step_data.get("end_time"),
        # Time in milliseconds, the execution was or is running
        "duration": step_data.get("duration"),
        # Status shows successful operation end
        "status": step_data.get("exit_status", {}).get("status", None),
        # Status code typically OK or ERROR
        "exit_status_code": step_data.get("exit_status", {}).get("code", None),
        # Hardcoded message that our Splunk searches rely on
        "message": "Execution of step",
        # Status message, often not populated and returns null
        "status_message": step_data.get("exit_status", {}).get("message", None),
        # The ID of the scope this step is or was executed for, those are site ids
        "execution_scope": step_data.get("execution_scope"),
        # Current execution status of the step:
        #   pending, running, pausing, paused, resuming, resumed, restarting, restarted, retrying, retried, aborting, aborted, finished, unknown
        "execution_status": step_data.get("execution_status"),
        # Status metadata which includes client ID that is responsible,
        # reason of the status and user login that is responsible for the status
        "status_metadata": step_data.get("status_metadata"),
        # Additional information regarding the step's type at the time it is or was executed (e.g. name of a script module and function)
        "step_type_info": step_data.get("step_type_info"),
    }


def transform_job_execution_events(job_execution_events, skip_step_events=False):
    jobs = []
    steps = []

    for job_execution_event in job_execution_events:
        job = create_job_event(job_execution_event)
        jobs.append(job)

        if skip_step_events:
            continue

        if "step_executions" in job_execution_event:
            for step_execution_event in job_execution_event["step_executions"]:
                step = create_step_event(job_execution_event, step_execution_event)
                steps.append(step)

    return jobs, steps


@license.license_required
def collect_events(helper, ew):
    try:
        # Get fields filled in the Data Input Form
        from_datetime_str       = helper.get_arg('from_datetime')
        ocapi_hostname          = helper.get_arg('ocapi_hostname')
        data_input_name         = helper.get_arg('name')
        ocapi_data_api_endpoint = helper.get_arg('ocapi_data_api_endpoint')
        time_buffer             = helper.get_arg('time_buffer')
        auth_headers_str        = helper.get_arg('auth_headers')
        job_types               = helper.get_arg('job_types')
        host_override           = helper.get_arg('host_override')
        url                     = utils.urljoin(f"https://{ocapi_hostname}", ocapi_data_api_endpoint)
        unique_id               = str(uuid4())
        utils.init_program_termination_handlers(unique_id, data_input_name, helper)
        # Validate the URL
        utils.enforce_secure_connection(url)
        time_buffer_seconds     = get_time_buffer_in_seconds(time_buffer)
        from_datetime           = datetime.strptime(from_datetime_str, CREATED_DATETIME_FORMAT)
        json_file_manager       = file_manager.JSONFileManager(
            join(
                environ.get("SPLUNK_HOME", "/opt/splunk"),
                "var",
                "lib",
                "splunk",
                "modinputs",
                "salesforce_commerce_cloud_job_statuses"
            )
        )
        json_repo               = file_manager.JSONFileRepository(json_file_manager)
        json_file_content       = utils.get_job_checkpoint(json_repo, data_input_name, "jobs", start_at=None)
        # Determine ingesting period
        start_datetime          = None
        event_host_field = host_override if host_override else ocapi_hostname

        if (
            hasattr(json_file_content, "start_at") and
            json_file_content.start_at is not None
        ):
            start_datetime = datetime.strptime(json_file_content.start_at, CREATED_DATETIME_FORMAT)
            if start_datetime > from_datetime:
                start_datetime -= time_buffer_seconds
            else:
                start_datetime = from_datetime - time_buffer_seconds
        else:
            start_datetime = from_datetime

        to_datetime             = datetime.now()
        start                   = start_datetime.strftime(CREATED_DATETIME_FORMAT)
        to                      = to_datetime.strftime(CREATED_DATETIME_FORMAT)
        access_token            = utils.obtain_access_token(helper)
        token                   = access_token["access_token"]
        http_auth_headers       = {}
        data_input_start_time   = time.time()
        common_metric_attributes = get_common_metric_attributes(unique_id, data_input_name)
        metric_data_input_status.add(0, attributes=common_metric_attributes)

        if auth_headers_str:
            http_auth_headers = utils.split_http_auth_headers(helper, auth_headers_str)

        http_headers = {"Authorization": f"Bearer {token}"}

        if http_auth_headers:
            http_headers.update(http_auth_headers)

        logging.info(
            f'Starting Job Statuses ingestion data_input={data_input_name} id={unique_id} period_from={start} period_to={to} job_types={job_types}'
        )
        data_input_ocapi_client_start_time = time.time()
        for job_type in job_types:
            logging.info(
                f'Start ingesting jobs type={job_type}'
            )
            pagination_jobs_generator = None
            should_skip_job_steps = False
            if job_type == "running":
                pagination_jobs_generator = utils.paginate(
                    "POST",
                    url,
                    headers=http_headers,
                    json=running_jobs_query(start, to, **{"start": 0, "count": 200}),
                )
                should_skip_job_steps = True
            elif job_type == "finished":
                pagination_jobs_generator = utils.paginate(
                    "POST",
                    url,
                    headers=http_headers,
                    json=build_request_body(start, to, **{"start": 0, "count": 200}),
                )
            while True:
                try:
                    request_start_time = time.time()
                    response = next(pagination_jobs_generator)
                    ocapi_client_response_time = measure_duration_in_seconds(request_start_time)
                    metric_data_input_ocapi_client_response_time.record(
                        ocapi_client_response_time,
                        attributes=get_ocapi_client_metric_attributes(
                            url,
                            "POST",
                            response.status_code,
                            None
                        )
                    )
                    response_json_data = response.json()
                    data = response_json_data.get("hits", [])
                    jobs_events, steps_events = transform_job_execution_events(data, skip_step_events=should_skip_job_steps)
                    len_jobs_events = len(jobs_events)
                    len_steps_events = len(steps_events)
                    logging.debug(
                        f'Writing Job events into index data_input={data_input_name} id={unique_id} count={len_jobs_events}'
                    )
                    for job_event in jobs_events:
                        source = f"jobs-{job_event.get('job_name')}-{job_event.get('execution_id')}"
                        write_to_index(
                            ew,
                            source,
                            job_event,
                            helper,
                            event_host_field,
                        )
                    metric_data_input_sfcc_jobs_count.add(len_jobs_events, attributes=common_metric_attributes)
                    logging.debug(
                        f'Inserted Job events into index data_input={data_input_name} id={unique_id} count={len_jobs_events}'
                    )
                    logging.debug(
                        f'Writing Step events into index data_input={data_input_name} id={unique_id} count={len_steps_events}'
                    )
                    for step_event in steps_events:
                        source = f"jobs-{step_event.get('job_name')}-{step_event.get('job_execution_id')}"
                        write_to_index(
                            ew,
                            source,
                            step_event,
                            helper,
                            event_host_field,
                        )
                    metric_data_input_sfcc_steps_count.add(len_steps_events, attributes=common_metric_attributes)
                    logging.debug(
                        f'Inserted Step events into index data_input={data_input_name} id={unique_id} count={len_steps_events}'
                    )
                except StopIteration:
                    # Signal the end of an paginator
                    break
            logging.info(
                f'Finish ingesting jobs type={job_type}'
            )
        # Update data input starting point
        json_file_content.start_at = to
        json_repo.update(data_input_name, json_file_content)
        data_input_ocapi_client_duration_ms = measure_duration_in_seconds(data_input_ocapi_client_start_time)
        metric_data_input_ocapi_client_duration.record(
            data_input_ocapi_client_duration_ms,
            attributes=get_ocapi_client_metric_attributes(
                url,
                None,
                None,
                None
            )
        )
        data_input_duration_ms = measure_duration_in_seconds(data_input_start_time)
        metric_data_input_duration.record(
            data_input_duration_ms,
            attributes=common_metric_attributes
        )
        metric_data_input_status.add(1, attributes=common_metric_attributes)
        log_opentelemetry_metrics(metric_reader, helper)
        logging.info(
            f'Finished Job Statuses ingestion data_input={data_input_name} id={unique_id}'
        )
    except (
        utils.OCAPIClientOrServerError,
        utils.OCAPIResponseBodyDecodeError,
        utils.OCAPIReadTimeoutError,
        utils.OCAPIRetryError,
    ) as ocapi_error_exc:
        metric_data_input_ocapi_client_errors.add(
            1,
            attributes=get_ocapi_client_metric_attributes(
                url,
                "POST",
                ocapi_error_exc.http_status_code,
                ocapi_error_exc.http_response_body
            )
        )
        log_opentelemetry_metrics(metric_reader, helper, log_info="ERROR")
        logging.error(
            f"Job Statuses ingestion data_input={data_input_name} id={unique_id} exception={str(ocapi_error_exc)}"
        )
        raise utils.OCAPIError(child_exc=ocapi_error_exc)
    except Exception as exc:
        log_opentelemetry_metrics(metric_reader, helper, log_info="ERROR")
        logging.error(
            f"Job Statuses ingestion data_input={data_input_name} id={unique_id} exception={str(exc)}"
        )
        raise exc
