[extrahop://<name>]
global_account = Extrahop account
cyclesize = The aggregation period for metrics
object_type = 
object_id = A comma-delimited list of API IDs for the devices, groups, or applications
metric_category = The category of metrics for this input. You can find this value under REST API Parameters in the ExtraHop Metric Catalog
metric_name = A comma-delimited list of metric names. You can find metric names under metric_specs in the ExtraHop Metric Catalog
interval = How often Splunk will collect metrics from the ExtraHop appliance, in seconds. This should be a multiple of the Metric Cycle Length.
input_type = Metrics

[detection://<name>]
global_account = Extrahop account
detection_category = Comma separated categories to fetch the detections. If not provided, sec.attack would be considered as default.
status = Select the status to fetch the detections. If provided None, the detections will be fetched for all the status.
interval = How often Splunk will collect detections from the ExtraHop appliance (in seconds).
input_type = Detections
