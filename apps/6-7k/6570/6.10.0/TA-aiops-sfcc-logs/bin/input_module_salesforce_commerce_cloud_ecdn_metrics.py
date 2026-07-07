import logging

from re import search
from time import time
from uuid import uuid4
from os.path import join
from os import environ
from datetime import datetime, timedelta, timezone
from json import loads, dumps
from urllib.parse import urlparse
from collections import defaultdict
from dataclasses import dataclass

from opentelemetry.sdk.metrics import view

import otel
import utils
import license
import api_client
import file_manager

from config import CREATED_DATETIME_FORMAT

from typing import Any


data_input_ecdn_metric_views = [
    view.View(
        instrument_name="data_input.ecdn.duration",
        aggregation=view.LastValueAggregation(),
    ),
    view.View(
        instrument_name="data_input.ecdn.status",
        aggregation=view.LastValueAggregation(),
    ),
]
data_input_ecdn_meter, data_input_ecdn_metric_reader = otel.create_meter_provider(
    "sfcc-ecdn", data_input_ecdn_metric_views
)
metric_data_input_duration = data_input_ecdn_meter.create_histogram(
    "data_input.ecdn.duration",
    unit="s",
    description="Measures the duration of data input",
)
metric_data_input_status = data_input_ecdn_meter.create_up_down_counter(
    "data_input.ecdn.status",
    unit="",
    description="Operational status of data input: 1 (completed) or 0 (failed)",
)
metric_data_input_errors = data_input_ecdn_meter.create_counter(
    "data_input.ecdn.errors", unit="{errors}", description="Number of data input errors"
)
metric_data_input_ocapi_client_errors = data_input_ecdn_meter.create_counter(
    "data_input.ecdn.ocapi.client.errors",
    unit="{ecdn}",
    description="Number of Salesforce Commerce Cloud Open Commerce API errors",
)


def create_common_data_input_ecdn_metric_attributes(
    data_input_id, data_input_name, zone
):
    return {
        "data_input.id": data_input_id,
        "data_input.name": data_input_name,
        "data_input.zone": zone,
    }


def create_sfcc_ecdn_metric_attributes(host, endpoint, zone):
    return {
        "sfcc.host": host,
        "sfcc.endpoint": endpoint,
        "sfcc.zone": zone,
    }


def validate_input(helper, definition):
    from_datetime = datetime.strptime(
        definition.parameters.get("from_datetime", None), CREATED_DATETIME_FORMAT
    )

    if from_datetime is None:
        raise ValueError('Please enter "From datetime"')

    return None


def has_from_and_to_datetime_period_reached(from_datetime, to_datetime):
    has_period_reached = from_datetime == to_datetime
    if not has_period_reached:
        return False

    return True


def should_filter_out_log_line(line, regex_filter_pattern):
    if not regex_filter_pattern:
        return False

    if regex_filter_pattern:
        if search(regex_filter_pattern, line):
            return True

    return False


@dataclass
class EcdnRequestSuccessMetric:
    timestamp: datetime
    host: str
    url_path: str
    user_agent: str
    method: str
    status: int
    country: str
    ip: str
    zone: str
    count: int = 1

    def to_splunk_event(self) -> dict[str, Any]:
        """Convert to Splunk event format"""
        success_metric = {
            "time": int(self.timestamp.timestamp()),
            "host": self.zone,
            "source": self.url_path,
            "sourcetype": "aiopsgroup:monitoring:sfcc:ecdn:metrics",
            "event": "metric",
            "fields": {
                "metric_name:ecdn.requests.success": self.count,
                "zone": self.zone,
                "client_host": self.host,
                "user_agent": self.user_agent,
                "method": self.method,
                "status": self.status,
                "country": self.country,
                "ip": self.ip,
            },
        }

        return success_metric


@dataclass
class EcdnRequestErrorMetric:
    timestamp: datetime
    host: str
    url_path: str
    url_query_params: str
    user_agent: str
    ray_id: str
    method: str
    status: int
    country: str
    ip: str
    zone: str
    count: int = 1

    def to_splunk_event(self) -> dict[str, Any]:
        """Convert to Splunk event format"""
        error_metric = {
            "time": int(self.timestamp.timestamp()),
            "host": self.zone,
            "source": self.url_path,
            "sourcetype": "aiopsgroup:monitoring:sfcc:ecdn:metrics",
            "event": "metric",
            "fields": {
                "metric_name:ecdn.requests.error": self.count,
                "zone": self.zone,
                "client_host": self.host,
                "user_agent": self.user_agent,
                "ray_id": self.ray_id,
                "method": self.method,
                "status": self.status,
                "country": self.country,
                "ip": self.ip,
            },
        }
        if self.url_query_params:
            error_metric["fields"]["url_params"] = self.url_query_params
        return error_metric


class EcdnLogProcessor:
    """Process ECDN logs and generate metrics using streaming approach"""

    def __init__(self, ecdn_zone: str):
        self.ecdn_zone = ecdn_zone
        self.success_metrics: dict[tuple, EcdnRequestSuccessMetric] = {}
        self.error_metrics: dict[tuple, EcdnRequestErrorMetric] = {}

    def _get_time_bin(self, timestamp: int) -> datetime:
        """Get normalized 2.5-minute (150-second) time bin for timestamp"""
        ts = datetime.fromtimestamp(timestamp / 1e9)
        # Calculate seconds from the start of the hour
        seconds_in_hour = ts.minute * 60 + ts.second
        # Round down to nearest 150-second (2.5-minute) interval
        bin_seconds = (seconds_in_hour // 150) * 150
        bin_minutes = bin_seconds // 60
        bin_seconds_remainder = bin_seconds % 60
        return ts.replace(
            minute=bin_minutes, second=bin_seconds_remainder, microsecond=0
        )

    def process_log_entry(self, entry: dict[str, Any]) -> None:
        """Process a single log entry in streaming fashion"""
        time_bin = self._get_time_bin(entry["EdgeStartTimestamp"])
        parsed_uri = urlparse(entry["ClientRequestURI"])
        url_path = parsed_uri.path
        url_query_params = parsed_uri.query
        # Determine status type
        status = entry["EdgeResponseStatus"]
        is_success = 200 <= status < 400

        if is_success:
            # Aggregate success metrics
            group_key = (
                entry["ClientRequestHost"],
                url_path,
                entry["ClientRequestUserAgent"],
                entry["ClientRequestMethod"],
                status,
                entry["ClientCountry"],
                entry["ClientIP"],
                time_bin,
            )
            if group_key in self.success_metrics:
                self.success_metrics[group_key].count += 1
            else:
                self.success_metrics[group_key] = EcdnRequestSuccessMetric(
                    timestamp=time_bin,
                    host=entry["ClientRequestHost"],
                    url_path=url_path,
                    user_agent=entry["ClientRequestUserAgent"],
                    method=entry["ClientRequestMethod"],
                    status=status,
                    country=entry["ClientCountry"],
                    ip=entry["ClientIP"],
                    zone=self.ecdn_zone,
                )
        else:
            # Aggregate error metrics
            group_key = (
                entry["ClientRequestHost"],
                url_path,
                url_query_params,
                entry["ClientRequestUserAgent"],
                entry["RayID"],
                entry["ClientRequestMethod"],
                status,
                entry["ClientCountry"],
                entry["ClientIP"],
                time_bin,
            )
            if group_key in self.error_metrics:
                self.error_metrics[group_key].count += 1
            else:
                self.error_metrics[group_key] = EcdnRequestErrorMetric(
                    timestamp=time_bin,
                    host=entry["ClientRequestHost"],
                    url_path=url_path,
                    url_query_params=url_query_params,
                    user_agent=entry["ClientRequestUserAgent"],
                    ray_id=entry["RayID"],
                    method=entry["ClientRequestMethod"],
                    status=status,
                    country=entry["ClientCountry"],
                    ip=entry["ClientIP"],
                    zone=self.ecdn_zone,
                )

    def get_success_metrics(self) -> list[dict[str, Any]]:
        """Get aggregated success metrics"""
        return [metric.to_splunk_event() for metric in self.success_metrics.values()]

    def get_error_metrics(self) -> list[dict[str, Any]]:
        """Get aggregated error metrics"""
        return [metric.to_splunk_event() for metric in self.error_metrics.values()]


@license.license_required
def collect_events(helper, ew):
    # Get fields filled in the Data Input Form
    unique_id = str(uuid4())
    data_input_name = helper.get_arg("name")
    ocapi_credentials = helper.get_arg("ocapi_credentials")
    ocapi_hostname = helper.get_arg("ocapi_hostname")
    ocapi_endpoint = helper.get_arg("ocapi_endpoint")
    zone = helper.get_arg("zone")
    from_datetime_str = helper.get_arg("from_datetime")
    max_datetime_str = helper.get_arg("to_datetime")
    filter_pattern_str = helper.get_arg("filter_pattern")
    time_buffer = int(helper.get_arg("time_buffer"))
    delta_period = helper.get_arg("delta_period")
    host_url = f"https://{ocapi_hostname}"
    url = utils.urljoin(host_url, ocapi_endpoint)
    filter_pattern = None

    if filter_pattern_str is not None and filter_pattern_str != "":
        filter_pattern = filter_pattern_str

    try:
        utils.init_program_termination_handlers(unique_id, data_input_name, helper)
        # Validate the URL
        utils.enforce_secure_connection(url)
        data_input_ecdn_start_time = time()
        common_data_input_ecdn_metric_attrs = (
            create_common_data_input_ecdn_metric_attributes(
                unique_id, data_input_name, zone
            )
        )
        metric_data_input_status.add(0, attributes=common_data_input_ecdn_metric_attrs)
        # Dates operations
        from_datetime = datetime.strptime(from_datetime_str, CREATED_DATETIME_FORMAT)
        to_datetime = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=time_buffer)
        from_datetime_str = from_datetime.strftime(CREATED_DATETIME_FORMAT)
        to_datetime_str = to_datetime.strftime(CREATED_DATETIME_FORMAT)
        # Initialize Data Input state
        storage_dir = join(
            environ.get("SPLUNK_HOME", "/opt/splunk"),
            "var",
            "lib",
            "splunk",
            "modinputs",
            "salesforce_commerce_cloud_ecdn_metrics",
        )
        json_file_manager = file_manager.JSONFileManager(storage_dir)
        json_repo = file_manager.JSONFileRepository(json_file_manager)
        json_file_content = utils.get_job_checkpoint(
            json_repo, data_input_name, "ecdn", start_at=None
        )
        # Determine ingesting period
        date_from = None

        if (
            hasattr(json_file_content, "start_at")
            and json_file_content.start_at is not None
        ):
            start_at_datetime = datetime.strptime(
                json_file_content.start_at, CREATED_DATETIME_FORMAT
            )
            if start_at_datetime > from_datetime:
                date_from = start_at_datetime.strftime(CREATED_DATETIME_FORMAT)
            else:
                date_from = from_datetime_str
        else:
            date_from = from_datetime_str

        if max_datetime_str is not None and max_datetime_str != "":
            from_datetime = datetime.strptime(date_from, CREATED_DATETIME_FORMAT)
            max_datetime = datetime.strptime(max_datetime_str, CREATED_DATETIME_FORMAT)
            if has_from_and_to_datetime_period_reached(from_datetime, max_datetime):
                logging.info(
                    f"Data input has reached configured max time period data_input={data_input_name} to={max_datetime}"
                )
                # Exit from the script
                return None
            elif from_datetime < max_datetime:
                to_datetime = min(
                    max_datetime, from_datetime + timedelta(seconds=int(delta_period))
                )
                to_datetime_str = to_datetime.strftime(CREATED_DATETIME_FORMAT)

        date_to = to_datetime_str
        ecdn_api_client = api_client.SalesforceECDNAPIClient(
            host_url,
            ocapi_endpoint,
            ocapi_credentials["username"],
            ocapi_credentials["password"],
            download_dir_path=storage_dir,
        )
        logging.info(
            f"Starting eCDN ingestion data_input={data_input_name} id={unique_id} zone={zone}"
        )
        requested_log_file_id = ecdn_api_client.request_log_file_for_download(
            zone, date_from, date_to
        )
        log_file_download_link = ecdn_api_client.get_log_file_download_link(
            requested_log_file_id
        )
        utils.enforce_secure_connection(log_file_download_link)
        ecdn_log_processor = EcdnLogProcessor(zone)
        # Process logs in streaming fashion
        for log_line in ecdn_api_client.download_log_file(log_file_download_link):
            if should_filter_out_log_line(log_line, filter_pattern):
                continue
            json_obj = loads(log_line.strip())
            ecdn_log_processor.process_log_entry(json_obj)

        success_metrics = ecdn_log_processor.get_success_metrics()
        error_metrics = ecdn_log_processor.get_error_metrics()

        for success_metric in success_metrics:
            event = helper.new_event(
                time=success_metric["time"],
                data=dumps(success_metric["fields"]),
                index="sfcc_ecdn_metrics",
                host=success_metric["host"],
                source=success_metric["source"],
                sourcetype=success_metric["sourcetype"],
            )
            ew.write_event(event)

        for error_metric in error_metrics:
            event = helper.new_event(
                time=error_metric["time"],
                data=dumps(error_metric["fields"]),
                index="sfcc_ecdn_metrics",
                host=error_metric["host"],
                source=error_metric["source"],
                sourcetype=error_metric["sourcetype"],
            )
            ew.write_event(event)

        # Update data input starting point
        json_file_content.start_at = to_datetime_str
        # Save state
        utils.save_job_checkpoint(
            json_file_manager,
            json_repo,
            json_file_content,
            data_input_name,
            "ecdn",
            start_at=json_file_content.start_at,
        )
        data_input_duration_ms = otel.measure_duration_in_seconds(
            data_input_ecdn_start_time
        )
        metric_data_input_duration.record(
            data_input_duration_ms, attributes=common_data_input_ecdn_metric_attrs
        )
        metric_data_input_status.add(1, attributes=common_data_input_ecdn_metric_attrs)
        logging.info(
            f"Finished eCDN ingestion data_input={data_input_name} id={unique_id} zone={zone} ingested_events={len(success_metrics) + len(error_metrics)}"
        )
        otel.log_metrics_in_console(data_input_ecdn_metric_reader)
    except (
        api_client.APIRetryError,
        api_client.APIReadTimeoutError,
        api_client.APIClientOrServerError,
        api_client.APIResponseBodyDecodeError,
    ) as ocapi_err:
        metric_data_input_ocapi_client_errors.add(
            1,
            attributes=otel.create_ocapi_client_metric_attributes(
                url, "POST", ocapi_err.http_status_code, ocapi_err.http_response_body
            ),
        )
        json_file_content.start_at = date_to
        utils.save_job_checkpoint(
            json_file_manager,
            json_repo,
            json_file_content,
            data_input_name,
            "ecdn",
            start_at=date_to,
        )
        logging.error(
            f"[ERROR][OCAPIError] eCDN ingestion data_input={data_input_name} zone={zone} id={unique_id} exception={str(type(ocapi_err))} message={ocapi_err.exc_msg}",
        )
        otel.log_metrics_in_console(data_input_ecdn_metric_reader, log_info="ERROR")
    except file_manager.JSONFileDecodeError as json_file_decode_err:
        exception_type = str(type(json_file_decode_err))
        exception_msg = json_file_decode_err.exc_msg
        metric_data_input_errors.add(
            1,
            attributes=otel.create_exception_metric_attributes(
                exception_type, exception_msg
            ),
        )
        logging.error(
            f"[ERROR][File Checkpoint] Failed to load file data_input={data_input_name} zone={zone} id={unique_id} exception={exception_type} message={exception_msg} file={json_file_decode_err.fname}",
        )
        otel.log_metrics_in_console(data_input_ecdn_metric_reader, log_info="ERROR")
    except Exception as error:
        exception_type = str(type(error))
        exception_msg = str(error)
        metric_data_input_errors.add(
            1,
            attributes=otel.create_exception_metric_attributes(
                exception_type, exception_msg
            ),
        )
        logging.error(
            f"[ERROR] eCDN ingestion data_input={data_input_name} zone={zone} id={unique_id} exception={exception_type} exception={exception_msg}",
        )
        otel.log_metrics_in_console(data_input_ecdn_metric_reader, log_info="ERROR")
        raise error
