# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
# This file contains all possible attribute/value pairs for configuring
# drilldown options for deep dive lanes.
#
# A unique drilldown options is represented by a stanza in this file. 
# The name of the stanza is the name that will appear in the UI. 
# ITSI currently supports a maximum of 22 drilldown stanzas in this file.
# Default values are provided for most settings and are defined in 
# the [default] stanza of the configuration file.
#
# Other more complex drilldown options are not defined in this file 
# because they are only represented in the deep dive code and cannot
# be disabled.
#
# There is a deep_dive_drilldowns.conf in $SPLUNK_HOME/etc/apps/itsi/default.
# To set custom configurations, place a deep_dive_drilldowns.conf in
# $SPLUNK_HOME/etc/apps/itsi/local/. You must restart Splunk software to 
# enable configurations.
#
# To learn more about configuration files (including precedence) please 
# see the documentation located at
# https://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#   * You can also define global settings outside of any stanza, at the top of
#     the file.
#   * Each conf file should have at most one default stanza. If there are
#     multiple default stanzas, settings are combined. In the case of
#     multiple definitions of the same setting, the last definition in the
#     file wins.
#   * If a setting is defined at both the global level and in a specific
#     stanza, the value in the specific stanza takes precedence.

[<name>]
* Each stanza represents a unique drilldown option. Use these settings to 
  configure properties for all types of drilldowns.

type = uri|search
* Represents whether this drilldown is meant to redirect to a new 
  URI or open a Splunk search.
* Required.

replace_tokens = true|false
* Enables token replacement in the search string or URI.
* Optional.
* If "true", the search or URI is token replaced by properties of the drilldown.
* Token replacement is similar to token replacement in simpleXML. Tokens are 
  represented in tokenized strings as a sub-string key surrounded by '$'.
    * For example, search=index=_internal | stats count | where count>$value$
* The following tokens are available for replacement by default:
  * lane_title - the title of the lane
  * lane_subtitle - the subtitle of the lane
  * lane_search - the search that powered the primary graph in the lane
  * earliest - the earliest epoch time stamp of the entire lane
  * latest - the latest epoch time stamp of the entire lane
  * bucket_earliest - the earliest epoch time stamp of the time bucket clicked
  * bucket_latest - the latest epoch time stamp of the time bucket clicked
* The following tokens are available for KPI lanes only:
  * kpi.service_id - the ID of the service to which the KPI belongs
  * kpi.service_title - the tite of the service to which the KPI belongs
  * kpi.kpi_id - the ID of the KPI represented in the lane
  * kpi.kpi_title - the title of the KPI represented in the lane
  * kpi.single_value_search - the raw data alert search for the KPI
  * kpi.timeseries_search - the raw data time series search for the KPI
  * kpi.base_search - the event gathering/filtering search for the KPI
* Default: false

metric_lane_enabled = true|false
* Whether to enable drilldowns on metric lanes.
* Optional.
* If "true", drilldown is available on metric lanes.
* If "false", drilldown is unavailable on metric lanes.
* Default: false

kpi_lane_enabled = true|false
* Whether to enable drilldowns on KPI lanes.
* Optional.
* If "true", drilldown is available on KPI lanes.
* If "false", drilldown is unavailable on KPI lanes.
* Default: false

event_lane_enabled = true|false
* Whether to enable drilldowns on event lanes.
* Optional.
* If "true", drilldown is available on event lanes.
* If "false", drilldown is unavailable on event lanes.
* Default: false

####
# Entity-based features
####
# Entity-based features are only available on KPI lanes because KPI lanes are the only 
# lanes that understand entities. Note that KPIs must have 'Split by Entity' enabled.

entity_level_only = true|false
* Whether to enable drilldowns only on lanes that surface entity-level information.
* Optional.
* If "true", drilldown is only available on lanes that surface entity-level information.
* If "false", drilldown is available on all lanes.
* Entity-level drilldowns make additional tokens and information available based
  on the entities clicked. See the 'entity_tokens' setting for more details.
* Default: false

entity_tokens = <csv>
* A CSV file of entity attributes to include on a drilldown.
* Optional.
* Only defiend entities will be available on entity-level 
  drilldowns. Pseudo-entities are ignored.
* If the 'replace_tokens' setting is "true", this setting will generate
  additional token replacements.
* Attributes can be either info fields or aliases.
* If the 'uri_payload_type' setting is set to "json", these entity attributes
  are added to the JSON payload per entity.
* Tokens from the first entity are replaced. If there are multiple entities,
  they all appear in a JSON payload.
* Tokens have the format "entity.<attribute name>".
* If any entity tokens are set to "all" (required to make drilldown work), 
  entity.id and entity.title will always be available as tokens.

entity_activation_rules = <JSON blob of entity rules>|all|kpi_title_match
* Determines which entities to consider for drilldown.
* Optional.
* If "all", all entities are considered valid for drilldown.
* If "kpi_title_match", no entity rule-based matching is performed. Instead,
  for the KPIs listed in the 'kpi_titles_with_drilldown' setting,
  their associated entity lanes include a custom drilldown for that KPI. 
  The drilldown redirects to the URI you provide, after token replacement.
* If set to a JSON blob of entity rules, entities are tested for 
  compliance with those rules. If no entities match, the drilldown 
  isn't available. If some or all all entities match, only those 
  matching are passed to the drilldown.
* Default: "all"

kpi_titles_with_drilldown = <comma-separated list of KPI titles>
* Configure custom drilldowns for specific KPIs. This setting lets you drill down
  to a specified URI when viewing the entity overlays for that KPI in a deep dive.
* Optional.
* This setting is only consumed if the 'entity_activation_rules' setting
  is set to "kpi_title_match".

####
# Properties for search type drilldowns
####
search = <tokenized search string>
* The search to use in the new lane or on the search page.
* Required for search type drilldowns.
* If the 'replace_tokens' setting is "true", the search is token replaced
  by properties from the drilldown itself.

add_lane_enabled = true|false
* Whether users can activate the drilldown as a search.
* Required for search type drilldowns
* If "true", users can activate the drilldown as a search.
* If "false', users cannot activate the drilldown as a search. 
* Default: false

use_bucket_timerange = true|false
* Whether to use only the time range of the selected bucket
  when redirected to a Splunk search.
* Optional.
* If "true", the drilldown search uses only the time range from which
  the user clicked in the deep dive. 
* If "false, the drilldown search uses the entire search timerange.
* Default: true

new_lane_settings = <tokenized JSON for lane settings properties>
* A tokenized JSON string that represents a model to use for new lanes.
* Required for search type drilldowns with the 'add_lane_enabled' setting
  set to "true".
* The "search" setting is overridden by the search property in this stanza.
* If the 'replace_tokens' setting is "true", the string is token replaced 
  by properties from the drilldown itself.
* Default lane settings are applied if you do not specify any values.

####
# Properties for URI type drilldowns
####
uri = <str>
* The URI to redirect to on the drilldown.
* Required for URI type drilldowns.
* If the 'replace_tokens' setting is "true" and the 'uri_payload_type' 
  setting is "simple", the URI string is replaced by tokens.
* Follows the format of an href:
  * A leading protocol allows a change in domain.
  * A leading slash changes the full path on the same domain.
  * Any other string only replaces the last segment of the URI with that string.

uri_payload_type = simple|json
* If "simple", token replacement is performed on the URI as if it were a search.
* If "json", no token replacement is performed and a query string parameter 
  'drilldown_payload' is appended to the URI with a JSON representation of 
  the context of a drilldown. This payload will always contain
  the context portion of the JSON blob, which contains the basic properties.
* If it is entity level and the entity properties of the drilldown are specified,
  the entities portion will exist and consist of the entity ID and title 
  as well as all attributes specified in as 'entity_tokens'. A JSON payload 
  format will look like the following (assumes 'entity_tokens' was host,family):
    {
      "context": {
        "earliest": <earliest time of full lane>,
        "latest": <latest time of full lane>,
        "bucket_earliest": <earliest time of bucket clicked>,
        "bucket_latest": <latest time of the bucket clicked>,
        "return_url": <URI of the current deep dive>,
        "service_id": "158bdaf4-6b0c-433e-9c24-c3a36c0e8eea",
        "kpi_id": "65ec30c5e1dd5046ac5416f5",
        "service_title": "Production Webservers",
        "kpi_title": "Total Request Latency (ms)"
      },
      "entities": [
        {
          "id": "5303377f-162c-45cc-809a-d1e3254ea4a1",
          "title": "Host Title 1",
          "host": "Host1",
          "family": "Linux"
        },
        {
          "id": "7aefd044-0f46-4ba4-ab13-f31e5797a3bf",
          "title": "Host Title 2",
          "host": "Host2",
          "family": "Linux"
        }
      ]
    }
* Default: simple
