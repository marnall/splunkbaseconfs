import logging

from time import time
from json import loads
from typing import Optional

from opentelemetry import metrics
from opentelemetry.sdk.metrics import (
    view,
    Meter,
    MeterProvider,
)
from opentelemetry.sdk.metrics.export import (
    InMemoryMetricReader,
)
from opentelemetry.sdk.resources import Resource


def create_meter_provider(
    service_name: str,
    metric_views: Optional[list[view.View]] = []
) -> Meter:
    metric_reader = InMemoryMetricReader()
    provider = MeterProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "service.namespace": "DataInput",
            }
        ),
        views=metric_views,
        metric_readers=[metric_reader]
    )

    # Sets the global default meter provider
    metrics.set_meter_provider(provider)
    # Creates a meter from the global meter provider
    meter = metrics.get_meter(__name__)

    return meter, metric_reader


def log_metrics_in_console(metric_reader: InMemoryMetricReader, log_info="INFO"):
    metrics = metric_reader.get_metrics_data()
    metrics_json = loads(metrics.to_json())

    if log_info == "INFO":
        logging.info(f"Metrics metrics={metrics_json}")
    elif log_info == "ERROR":
        logging.error(f"Metrics metrics={metrics_json}")

    return metrics_json


def create_ocapi_client_metric_attributes(
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


def create_exception_metric_attributes(
    exception_class: str,
    exception_msg: str
) -> dict:
    return {
        "exception.type": exception_class,
        "exception.message": exception_msg
    }


def measure_duration_in_seconds(start_time):
    end_time = time()

    return end_time - start_time