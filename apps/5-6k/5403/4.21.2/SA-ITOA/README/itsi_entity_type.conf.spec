# This file contains possible settings you can use to upload sample
# entity types to the KV store.
#
# An entity type defines how to classify a type of data source.
# For example, you can create a Windows, Kubernetes, or VMware vCenter Server entity type.
# An entity type can include zero or more entity data drilldowns and zero or more entity data dashboards.
#
# There is an itsi_entity_type.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To set custom
# configurations, place an itsi_entity_type.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
# You must restart ITSI to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles.

[<name>]
title = <string>
* Required
* Title of the entity type.

description = <string>
* Description of the entity type.

dashboard_drilldowns = <json array>
* Required. If no value empty list
* A list of dashboard drilldowns that entities of this class can use to associate with raw data.
* A single dashbobard drilldown JSON object contains the following fields
{
    "title": <string>
    * Usage:
        * Required
        * The title of the dashboard.

    "id" = <string>
    * Usage:
        * Required
        * A unique ID for the dashboard drilldown.

    "dashboard_type" = <string>
    * Usage:
        * Required
        * Type of dashboard, one of udf_dashboard (internal use only), xml_dashboard or navigation_link

    "base_url": <string>
    * Usage:
        * An internal or external URL pointing to the dashboard.

    "params": <json>
    * Usage:
        * Contains two fields: 'alias_param_map' and 'static_params'.
        * 'alias_param_map' is a mapping of a URL parameter and its alias.
        * 'static_params' are parameters with a defined value.
        * Example:
            {
                "static_params": {
                    "start_time": "-12h",
                },
                "alias_param_map": [
                    {
                        "alias": "host",
                        "param": "node"
                    }
                ]
            }
}

data_drilldowns = <json array>
* A list of data drilldowns that entities of this class can use to populate pre-built dashboards.
* A single data drilldown JSON object contains the following fields
{
    "title": <string>
    * Usage:
        * Required
        * The title of the entity data drilldown.

    "type": <metrics|events>
    * Usage:
        * Required
        * The type of indexed data that this drilldown is associated with.
        * Must be either "metrics" or "events".

    "static_filter": <json>
    * Usage:
        * An SPL filter represented by a JSON structure following a defined schema.
        * The static filter finds a subset of indexed data that is associated with
          this entity data drilldown.
        * There are two types of filters for a static_filter:
          1. Basic filter - fields including:
            - type: One of "include" or "exclude"
            - field: The field name in raw data
            - values: A list of values for "field" to filter on
          2. Boolean filter - fields including:
            - type: One of "or" or "and"
            - filters: A list of filters in the shape of a basic filter or boolean filter

        * The following example filter is equivalent to "sourcetype=access_logs AND index=main":
        { \
            "type": "and", \
            "filters": [ \
                { \
                    "type": "include", \
                    "field": "sourcetype", \
                    "values": ["access_logs"] \
                }, \
                { \
                    "type": "include", \
                    "field": "index", \
                    "values": ["main"] \
                } \
            ] \
        }

    "entity_field_filter": <json>
    * Usage:
        * Specifies what field (info or alias) of an entity to apply
          to further filter down the indexed data.
        * There are two types of filters for an entity_field_filter:
          1. Entity field filter - fields including:
            - type: Must be "entity"
            - data_field: The field name in raw data
            - entity_field: The field of an entity whose value will be used to filter on raw data with "data_field"
          2. Boolean filter - fields including:
            - type: One of "or" or "and"
            - filters: A list of filters in the shape of a entity field filter or boolean filter

        * Example:
        { \
            "type": "or", \
            "filters": [ \
                { \
                    "type": "entity", \
                    "data_field": "src", \
                    "entity_field": "ip" \
                }, \
                { \
                    "type": "entity", \
                    "data_field": "dest", \
                    "entity_field": "ip" \
                } \
            ] \
        }
        * For an entity with "ip=1.2.3.4", this is equivalent to "src=1.2.3.4 OR dest=1.2.3.4".
        * Combined with the static filter example above, the final filter of this entity data drilldown
          is equivalent to "(sourcetype=access_logs AND index=main) AND (src=1.2.3.4 OR dest=1.2.3.4)"
}

vital_metrics = <json array>
* Optional
* A list of vital metrics that entities of this class are associated with.
{
    "metric_name": <string>
    * Usage:
        * Required
        * The name of the metric.

    "search" = <string>
    * Usage:
        * Required
        * SPL to find this metric.

    "split_by_fields": <array>
    * Usage:
        * Required
        * An array of fields used to split the results to entities.

    "matching_entity_fields": <array>
    * Usage:
        * Required
        * The fields used to look up entities from the KV store.
        * Example: split_by_fields=[id,name], matching_entity_fields=[id,host]
        * Raw event "id" field maps to "id" field of entity, and "name" field maps to "host" field

    "is_key": <boolean>
    * Usage:
        * Optional
        * If "true", this metric is used as a key metric for this entity type in the Entity Overview.
        * Default: false

    "unit": <string>
    * Usage:
        * Optional
        * The unit for the metric.

    "alert_rule": <json>
    * Usage:
        * Optional
        * If defined, following fields are required: suppress_time, cron_schedule, is_enabled, critical_threshold, info_threshold
        * suppress_time:        The alert will stop tirggering for the specified time
        * cron_schedule:        The alert search running frequency
        * is_enabled:           False means alert is disabled.
        * critical_threshold:   The range of critical threshold value
        * warning_threshold:    The range of warning threshold value
        * info_threshold:       The range of info threshold value
        * entity_filter:        Filter entities based on the field dimensions. Filtering use 'OR' for same field, otherwise use 'AND'.
        * Example:
        {
            "suppress_time" : "0",
            "cron_schedule" : "*/1 * * * *",
            "is_enabled" : true,
            "critical_threshold" : [ "100", "+inf" ],
            "warning_threshold" : [ "50", "100" ],
            "info_threshold" : [ "-inf", "50" ],
            "entity_filter" : [
                {"field":"os_version","value":"7.0","field_type":"info"},
                {"field":"os_version","value":"11.0","field_type":"info"},
                {"field":"cluster","value":"cluster01_datagen","field_type":"info"}
            ]
        }
}

_immutable = <boolean>
* Required
* Whether you can edit or delete the entity data drilldown.
* If "true", you can't edit or delete the entity data drilldown.
* If "false", you can edit or delete the entity data drilldown.
* Default: false
