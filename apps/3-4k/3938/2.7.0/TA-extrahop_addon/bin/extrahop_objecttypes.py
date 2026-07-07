"""Model for ExtraHop object types."""


class ExtraHopTypeHandler:
    """Maps ExtraHop Add-On data input types to ExtraHop device types + API endpoint for metrics.

    Args:
        api_object_type (str): Object type used in ExtraHop API payloads to /metrics.
        canonical_object_type (str, optional): The underlying ExtraHop metric type.
            e.g. device_group metrics are actually metrics for *devices*
            Used for Splunk KV store data.
            Defaults to api_object_type.
        event_object_type (str, optional): The "object_type" field in Splunk events.
            Should allow users to combine object_type and oid in Splunk event data to find
            the object in ExtraHop's API.
            Defaults to api_object_type.
        aggregate (bool, optional): Aggregate/total metrics for this type? Defaults to False.
    """

    def __init__(
        self,
        api_object_type,
        canonical_type=None,
        event_object_type=None,
        aggregate=False,
    ):
        """Init method for handler class."""
        self.api_object_type = api_object_type
        self.canonical_metric_type = (
            canonical_type if canonical_type is not None else api_object_type
        )
        self.event_object_type = (
            event_object_type
            if event_object_type is not None
            else api_object_type
        )
        self.aggregate = aggregate
        self.metrics_endpoint = "metrics/total" if aggregate else "metrics"


EXTRAHOP_OBJECT_TYPES = {
    "application": ExtraHopTypeHandler("application"),
    "device": ExtraHopTypeHandler("device"),
    "device_group": ExtraHopTypeHandler(
        "device_group", canonical_type="device", event_object_type="device"
    ),
    "device_group_summary": ExtraHopTypeHandler(
        "device_group", canonical_type="device", aggregate=True
    ),
    "network": ExtraHopTypeHandler("network", canonical_type="capture"),
}
