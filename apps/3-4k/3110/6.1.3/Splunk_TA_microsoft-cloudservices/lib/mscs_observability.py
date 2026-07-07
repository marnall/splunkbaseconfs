#!/usr/bin/python
#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
"""
OpenTelemetry observability service for MSCS add-on.

This module provides a centralized service for managing OpenTelemetry metrics
including setup of metric providers, exporters, and metric instruments.
"""

from typing import Optional
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Histogram
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    MetricExporter,
    MetricExportResult,
    AggregationTemporality,
)
from opentelemetry.sdk.resources import Resource
from splunksdc import logging

_default_logger = logging.get_module_logger()


class LoggerMetricExporter(MetricExporter):
    """Custom MetricExporter that writes metrics to the logger."""

    def __init__(self, logger=None):
        super().__init__(
            preferred_temporality={
                Histogram: AggregationTemporality.DELTA,
            }
        )
        self._logger = logger or _default_logger

    @staticmethod
    def _build_attributes(resource_metrics, data_point):
        resource_attributes = (
            dict(resource_metrics.resource.attributes)
            if getattr(resource_metrics, "resource", None)
            and resource_metrics.resource.attributes
            else {}
        )
        attributes_dict = resource_attributes.copy()
        if data_point.attributes:
            attributes_dict.update(dict(data_point.attributes))
        return attributes_dict

    def export(
        self,
        metrics_data,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Export metrics to logger. Only histograms are supported."""
        try:
            for resource_metrics in metrics_data.resource_metrics:
                for scope_metrics in resource_metrics.scope_metrics:
                    for metric in scope_metrics.metrics:
                        for data_point in metric.data.data_points:
                            attributes_dict = self._build_attributes(
                                resource_metrics, data_point
                            )

                            if hasattr(data_point, "bucket_counts"):
                                self._logger.debug(
                                    f"OpenTelemetry Metric: {metric.name}",
                                    metric_name=metric.name,
                                    count=data_point.count,
                                    sum=data_point.sum,
                                    min=getattr(data_point, "min", None),
                                    max=getattr(data_point, "max", None),
                                    bucket_counts=list(data_point.bucket_counts)
                                    if data_point.bucket_counts
                                    else [],
                                    explicit_bounds=list(data_point.explicit_bounds)
                                    if data_point.explicit_bounds
                                    else [],
                                    unit=metric.unit,
                                    description=metric.description,
                                    **attributes_dict,
                                )
                            else:
                                self._logger.debug(
                                    f"Skipping unsupported metric type for {metric.name}. Only histograms are supported."
                                )
            return MetricExportResult.SUCCESS
        except Exception as e:
            self._logger.error(f"Failed to export metrics: {e}", exc_info=e)
            return MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shutdown the exporter."""
        pass

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Force flush any buffered metrics."""
        return True


class ObservabilityService:
    """
    Centralized service for managing OpenTelemetry metrics.

    This service provides a singleton-like interface for setting up and accessing
    OpenTelemetry metrics across the MSCS add-on.
    """

    _instance: Optional["ObservabilityService"] = None
    _initialized: bool = False

    def __init__(self, logger=None):
        """Initialize the observability service."""
        self._logger = logger or _default_logger
        self._meter = None
        self._provider = None

    @classmethod
    def get_instance(cls, logger=None) -> "ObservabilityService":
        """Get or create the singleton instance of ObservabilityService."""
        if cls._instance is None:
            cls._instance = cls(logger=logger)
        elif logger is not None:
            cls._instance.set_logger(logger)
        return cls._instance

    def set_logger(self, logger):
        """Update the logger used by the observability service."""
        if logger:
            self._logger = logger

    def initialize(
        self,
        service_name: str,
        input_name: str,
    ) -> None:
        """
        Initialize the OpenTelemetry metrics provider and meter.

        Args:
            service_name: Name of the service for resource identification
            input_name: Name of the specific input instance providing metrics
        """
        if not service_name or not input_name:
            self._logger.error(
                "Cannot initialize ObservabilityService: missing service_name or input_name",
                service_name=service_name,
                input_name=input_name,
            )
            self._meter = None
            self._provider = None
            return

        if self._initialized:
            self._logger.debug("ObservabilityService already initialized, skipping")
            return

        try:
            attributes = {
                "service.name": service_name,
                "service.input_name": input_name,
            }

            resource = Resource(attributes=attributes)

            reader = PeriodicExportingMetricReader(
                LoggerMetricExporter(logger=self._logger)
            )
            self._provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(self._provider)

            meter_name = "mscs.observability"
            self._meter = metrics.get_meter(meter_name)

            self._initialized = True
            self._logger.info(
                "ObservabilityService initialized successfully",
                service_name=service_name,
                input_name=input_name,
                meter_name=meter_name,
            )
        except Exception as e:
            self._logger.warning(f"Failed to initialize ObservabilityService: {e}")
            self._meter = None
            self._provider = None

    def is_initialized(self) -> bool:
        """Check if the service has been initialized."""
        return self._initialized

    def create_histogram(
        self,
        name: str,
        description: str = "",
        unit: str = "",
    ) -> Optional[Histogram]:
        """
        Create a histogram metric instrument.

        Args:
            name: Name of the histogram
            description: Description of what the histogram measures
            unit: Unit of measurement

        Returns:
            Histogram instance or None if service not initialized
        """
        if not self._meter:
            self._logger.warning(
                f"Cannot create histogram '{name}': ObservabilityService not initialized"
            )
            return None

        try:
            histogram = self._meter.create_histogram(
                name=name,
                description=description,
                unit=unit,
            )
            self._logger.debug(f"Created histogram metric: {name}")
            return histogram
        except Exception as e:
            self._logger.error(f"Failed to create histogram '{name}': {e}")
            return None

    def shutdown(self) -> None:
        """Shutdown the observability service and clean up resources."""
        if self._provider:
            try:
                self._provider.shutdown()
                self._logger.info("ObservabilityService shut down successfully")
            except Exception as e:
                self._logger.error(f"Error shutting down ObservabilityService: {e}")

        self._meter = None
        self._provider = None
        self._initialized = False


def get_observability_service(logger=None) -> ObservabilityService:
    """Get the singleton instance of ObservabilityService."""
    return ObservabilityService.get_instance(logger=logger)
