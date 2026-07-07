# This file contains possible settings you can use to upload sample
# KPI base searches to the KV store.
#
# There is an itsi_kpi_base_search.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To set custom
# configurations, place an itsi_kpi_base_search.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
# You must restart ITSI to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles.

[<name>]
description = <string>
* A description of the KPI base search.

title = <string>
* The title of the KPI base search

_owner = <string>
* The owner of this KPI base search
* Default: itsi

base_search = <search>
* The search to execute in the KPI base search. This search is the source
  for the fields defined in metrics.
* Set the search to "*" if the 'is_metric' setting is set to "true".

metrics = <json>
* A JSON blob that specifies the array of metrics to be collected.
* Example item in the blob:
* {
*     "unit": "%",
*     "title": "CPU Utilization: %",
*     "entity_statop": "avg",
*     "aggregate_statop": "avg",
*     "_key": "620b26a6f286a508fd356d94",
*     "threshold_field": "cpu_load_percent"
*  }
* The threshold_field in the item corresponds to a field from the base search.

is_metric = <boolean>
* Whether the KPI base search is a metric search.

metric = <json>
* A JSON blob that specifies the metric index and metric name to search on.
* Example item in the blob:
* {
*     "metric_index": "itsi_im_metrics",
*     "metric_name": "cpu.user"
* }

is_entity_breakdown = <boolean>
* Whether the metrics should be broken down by entities for
  threshold calculations.
* If "1", metrics are broken down by entities.
* If "0", metrics are not broken down by entities.

is_service_entity_filter = <boolean>
* Whether metrics should filter out entities not in the service.
* If "1", entities that don't belong to the service are filtered out.
* IF "0", entities that don't belong to the service are still included.

entity_id_fields = <string>
* The field in the base search used to look up the corresponding
  entity to filter KPIs.
* For example, host, ip, and so on.
* This field is required if the 'is_service_entity_filter' setting is set to "true".

entity_breakdown_id_fields = <string>
* The field in the base search used to look up the corresponding entity
  to split KPIs.
* For example, host, ip, and so on.
* This field is required if the 'is_entity_breakdown' setting is set to "true".

entity_alias_filtering_fields = <comma-separated list>
* A list of alias attributes to be used to filter out entities not in the service.
* Optional.
* This field is required if the 'is_service_entity_filter' setting is set to "true".

alert_period = <integer>
* The frequency, in minutes, at which to run the search.

search_alert_earliest = <integer>
* The time window, in minutes, over which to evaluate the metrics.

alert_lag = <integer>
* The amount of time, in seconds, to push back the metric evaluation.
* This setting corresponds to the data indexing lag.
* Default: 30

metric_qualifier = <string>
* The field in the base search used to further split metrics.
* CAUTION: You cannot modify this setting in the UI.

source_itsi_da = <string>
* The ITSI module that is the source defining this KPI base search.
