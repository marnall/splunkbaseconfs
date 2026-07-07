# This file contains possible attribute/value pairs for saved search entries in
# savedsearches.conf.  You can configure saved searches by creating your own
# savedsearches.conf.
#
# There is a default savedsearches.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To
# set custom configurations, place a savedsearches.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. For examples, see
# savedsearches.conf.example. You must restart Splunk to enable configurations.
#
# To learn more about configuration files (including precedence) please see the
# documentation located at
# http://docs.splunk.com/Documentation/Splunk/latest/Admin/Aboutconfigurationfiles

####
# Event generator settings
####

[<stanza_name>]
action.itsi_event_generator = <boolean>
* Whether the alert is enabled.

action.itsi_event_generator.param.title = <string>
* The title of the notable event in Episode Review. 
* Optional. If title is not provided then the search name 
  becomes the title.

action.itsi_event_generator.param.description = <string>
* A description of the notable event.
* Optional. If a description is not provided then the search
  description becomes the event description.

action.itsi_event_generator.param.owner = <string>
* The initial owner of the notable event.
* Optional.
* Default: unassigned

action.itsi_event_generator.param.status = <string>
* The triage status of the event in Episode Review.
* Values must match an integer specified in the default version of 
  itsi_notable_event_status.conf (or the local version if you created one).
* Optional.
* Default: 1 (New)

action.itsi_event_generator.param.severity = <string>
* The level of importance of the event. 
* Values must match an integer specified in the default version of 
  itsi_notable_event_severity.conf (or the local version if you created one).
* Optional.
* Default: 1 (Info)

action.itsi_event_generator.param.itsi_instruction = <string>
* Instructions for how to address the notable event.
* Must use tokens such as %fieldname% to map the field name from an external event.
  Static instructions are not supported.
* You can use an aggregation policy to aggregate individual instructions into an episode.
  By default, episodes display the instructions for the first event in an episode.
* Optional.

action.itsi_event_generator.param.drilldown_search_title = <string>
* You can drill down to a specific Splunk search from an event or episode.	
* The name of the drilldown search link.
* Optional.

action.itsi_event_generator.param.drilldown_search_search = <string>
* The drilldown search string.
* Optional.

action.itsi_event_generator.param.drilldown_search_latest_offset = <seconds>
* Defines how far ahead from the time of the event, in seconds,
  to look for related events.
* This offset is added to the event time.
* Default: 300 (Next 5 minutes)

action.itsi_event_generator.param.drilldown_search_earliest_offset = <string>
* Defines how far back from the time of the event, in seconds,
  to start looking for related events.
* This offset is subtracted from the event time.
* Default: -300 (Last 5 minutes)

action.itsi_event_generator.param.drilldown_title = <string>
* You can drill down to a specific website from an event or episode.
* The name of the drilldown website link.
* Optional.

action.itsi_event_generator.param.drilldown_uri = <string>
* The URI of the website you drill down to.
* Optional.

param.event_identifier_fields = <comma-separated list>
* A list of fields that are used to identify event duplication.
* Default: source

action.itsi_event_generator.param.service_ids = <comma-separated list>
* A list of service IDs representing one or more ITSI services to 
  which this correlation search applies.
* Optional.

action.itsi_event_generator.param.entity_lookup_field = <string>
* The field in the data retrieved by the correlation search that
  is used to look up corresponding entities. For example, host.
* Optional.

action.itsi_event_generator.param.search_type = <string>
* The search type.
* Optional.
* Default: custom

action.itsi_event_generator.param.meta_data = <string>
* The search type of any stored metadata.  
* Optional.

action.itsi_event_generator.param.is_ad_at = <boolean>
* Whether this correlation is created by enabling adaptive 
  thresholding or anomaly detection (AT/AD) for KPIs or services.
* Optional.
* If "1", the correlation is created by AT/AD.
* If "0", the correlation is not created by AT/AD.
* Default: 0

action.itsi_event_generator.param.ad_at_kpi_ids = <comma-separated list>
* A list of KPIs where AT/AD is enabled.
* Optional.

action.itsi_event_generator.param.editor = <string>
* The type of editor used to create the correlation search. 
* Can be either "advance_correlation_builder_editor", which is the correlation
  search editor in ITSI, or "multi_kpi_alert_editor", which is the multi-KPI
  alert builder.
* Default: advance_correlation_builder_editor
