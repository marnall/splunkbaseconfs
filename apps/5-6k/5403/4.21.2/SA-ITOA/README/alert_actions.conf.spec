# This file contains possible attributes and values for generating ITSI
# notable events, configuring episode actions, and executing
# post-search processing actions.
#
# There is an alert_actions.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an alert_actions.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#  * You can also define global settings outside of any stanza, at the top
#    of the file.
#  * Each .conf file should have at most one default stanza. If there are
#    multiple default stanzas, attributes are combined. In the case of
#    multiple definitions of the same attribute, the last definition in the
#    file wins.
#  * If an attribute is defined at both the global level and in a specific
#    stanza, the value in the specific stanza takes precedence.

[<stanza_name>]
ttl = <integer> [p]
* The minimum time to live (TTL), in seconds, of the search artifacts
  if this action is triggered.
* If p follows the integer, then the integer is the number of scheduled periods.
* Default: 600 (10 minutes)

maxtime = <integer> [m|s|h|d]
* The maximum amount of time that the execution of an action is allowed to
  take before the action is aborted.
* Use the d, h, m and s suffixes to define the period of time:
  d = day, h = hour, m = minute and s = second.
  For example: 5d means 5 days.
* If you do not include a suffix, the time defaults to seconds.
* Default: 600 (10 minutes)

maxresults = <integer>
* The maximum number of search results sent via the alert.
* Default: 10000

is_custom = <boolean>
* Specifies whether the alert action is based on the custom alert
  actions framework and is supposed to be listed in the search UI.
* Default: 1

label = <string>
* Defines the label shown in the UI.
* If not specified, the stanza name is used instead.

description = <string>
* Defines the description shown in the UI.

payload_format = [xml|json]
* The format in which the alert script receives
  the configuration via STDIN.
* Default: json

[itsi_event_generator]
* Generate notable events under this stanza name.
* ITSI sends notable events to the ITSI summary index.
* Follow this stanza name with any number of the following
  attribute/value pairs.
* If you do not specify an entry for each attribute, Splunk will
  use the default value.

param.http_token_name = <string>
* The HTTP token name.
* Optional.
* If you do not provide a token name, ITSI obtains one
  token using the index and sourcetype parameters below.

param.index = <string>
* The index name.
* This setting is required if you do not provide an HTTP
  token for the 'param.http_token_name' setting.
* Default: itsi_tracked_alerts

param.sourcetype = <string>
* The sourcetype.
* This setting is used if you do not provide an HTTP
  token for the 'param.http_token_name' setting.
* Default: itsi_notable:event

param.event_identifier_fields = <comma-separated list>
* A list of fields that are used to identify event duplication.
* Default: source

param.is_use_event_time = <boolean>
* If "1", ITSI uses the actual event time.
* If "0", ITSI uses the time the event was indexed.
* Default: 0

param.batch_size = <integer>
* The number of notable events to send via HEC in a
  single HTTP request
* Default: 5000

param.event_field_max_length = <integer>
* The maximum field length.
* Default: 10000

param.title = <string>
* The title of the notable event in Episode Review.
* Optional. If a title is not provided the search name
  becomes the title.

param.description = <string>
* A description of the notable event.
* Optional. If a description is not provided the search
  description becomes the event description.

param.owner = <string>
* The initial owner of the notable event.
* Optional.
* Default: unassigned

param.status = <string>
* The triage status of the event in Episode Review.
* Optional. If a status is not provided then default_status is assigned.
* Values must match an integer specified in the default version of
  itsi_notable_event_status.conf, or the local version if you created one.

param.severity = <string>
* The level of importance of the event.
* Optional. If a severity is not provided then default_severity is assigned.
* Values must match an integer specified in the default version of
  itsi_notable_event_severity.conf, or the local version if you created one.

param.itsi_instruction = <string>
* Instructions for how to address the notable event.
* Optional.
* Must use tokens such as %fieldname% to map the field name from an external event.
  Static instructions are not supported.
* You can use an aggregation policy to aggregate individual instructions into an episode.
  By default, episodes display the instructions for the first event in an episode.

param.drilldown_search_title = <string>
* You can drill down to a specific Splunk search from an event or episode. This setting
  specifies the text of the drilldown link. Provide the actual search string in the
  'param.drilldown_search_search' setting.
* Optional.

param.drilldown_search_search = <string>
* The Splunk search string to drill down to from an event or episode.
* Optional.

param.drilldown_search_latest_offset = <seconds>
* Defines how far ahead from the time of the event, in seconds,
  to look for related events.
* This offset is added to the event time.
* Optional.

param.drilldown_search_earliest_offset = <string>
* Defines how far back from the time of the event, in seconds,
  to start looking for related events.
* This offset is subtracted from the event time.
* Optional.

param.drilldown_title = <string>
* You can drill down to a specific URI from an event or episode. This setting
  specifies the text of the drilldown link. Provide the actual URI string in
  the 'param.drilldown_uri' setting.
* Optional.

param.drilldown_uri = <string>
* The URI to drill down to from an event or episode.
* Optional.

param.service_ids = <comma-separated list>
* A list of service IDs representing one or more ITSI services to
  which this correlation search applies.
* Optional.

param.entity_lookup_field = <string>
* The field in the data retrieved by the correlation search that
  is used to look up corresponding entities. For example, "host".
* Optional.

param.search_type = <string>
* The search type.
* Optional.
* Default: custom

param.meta_data = <string>
* The search type of any stored metadata.
* Optional.

param.is_ad_at =  <boolean>
* Whether this correlation is created by enabling adaptive
  thresholding or anomaly detection (AT/AD) for KPIs or services.
* Optional.
* If "1", the correlation is created by adaptive thresholding or anomaly detection.
* If "0", the correlation is not created by adaptive thresholding or anomaly detection.

param.ad_at_kpi_ids = <comma-separated list>
* A list of KPIs where adaptive thresholding or anomaly detection is enabled.
* Optional.

param.editor = <string>
* The type of editor used to create the correlation search.
* Can be either "advance_correlation_builder_editor", which is the correlation
  search editor in ITSI, or "multi_kpi_alert_editor", which is the multi-KPI
  alert builder.
* Default: advance_correlation_builder_editor

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_pagerduty_event]

param.pd_account = <string>
* (Required) PagerDuty account configured in ITSI

param.pd_dedup_key = <string>
* (Required) Used to deduplicate on the PagerDuty side.  Repeated
* alerts carrying this value will not create new incidents
* ITSI requires this value to be Episode ID
* Default: $result.itsi_group_id$

param.pd_event_action = <string>
* (Required) Type of Event Action
* Must be one of the values
* trigger, acknowkedge or resolve

param.pd_source = <string>
* (Required) The object about which this alert is being raised

param.pd_summary = <string>
* (Required) The short description of the problem, < 1024 chars

param.pd_severity = <string>
* (Required) One of the values
* critical, error, warning or info

param.pd_link_text = <string>
* (Optional) Ordered list of names for the link hrefs supplied
* These will be displayed as hyperlinks in PagerDuty

param.pd_link_href = <string>
* (Optional) Ordered list of hyperlinks for this event
* See param.pd_link_text

param.pd_class = <string>
* (Optional) Class of the event

param.pd_component = <string>
* (Optional) Component is the parameter, eg CPU on host X
* CPU is the component to the source 'host X'

param.pd_group = <string>
* (Optional) Major grouping, ie application/service

param.pd_timestamp = <string>
* (Optional) Timestamp of the event that is sent to PagerDuty
* Must be in epoch time which will be converted into ISO formatted string
* If nothing is passed, the time of firing the alert is considered

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_sample_event_action_ping]
* Ping a host in one or more ITSI episodes under this stanza name.
* Follow this stanza name with any number of the following
  attribute/value pairs.
* If you don't specify an entry for each attribute, Splunk uses
  the default value.

param.host_to_ping = <string>
* The field from the episode representing the host to ping.
* If your event contains the field 'server', set to '%server%'.
* When ITSI executes the alert action, it extracts the value corresponding
  to the token value from event data and tries to ping it.
* If you set a value that does not begin and end with '%', ITSI
  considers this to be the value to ping. No extractions are done in this case.
* Default: %orig_host%

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_event_action_link_ticket]
* Set options to associate an episode with a ticket from an
  external ticketing system under this stanza name.
* Follow this stanza name with any number of the following
  attribute/value pairs.
* If you do not specify an entry for each attribute, Splunk will
  use the default value.

param.ticket_system = <string>
* The name of the external ticketing system.
* This setting is required to create/update/delete a ticket.
* There is no default.

param.ticket_id = <string>
* The ID of the specific ticket to link to.
* This setting is required to create/update/delete a ticket.
* There is no default.

param.ticket_url = <string>
* The drilldown link to the ticket in the external ticketing system.
* This setting is required to create/update a ticket.
* There is no default.

param.operation = <upsert|delete>
* Specifies the type of action to take on the ticket.
* If "upsert", ITSI inserts or updates existing fields.
* If "delete", ITSI deletes the ticket.
* There is no default.

param.kwargs = <dict>
* A dictionary of additional fields to pass to the ticket.
* Optional.
* There is no default.

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_event_action_link_url]
* Set options to associate an episode with an external URL.
* Follow this stanza name with any number of the following
  attribute/value pairs.
* If you do not specify an entry for each attribute, Splunk will
  use the default value.

param.url = <string>
* A URL to an external document or incident

param.url_description = <string>
* The label or description of the document to link to.
* This setting is required to create/update/delete a URL.
* There is no default.

param.operation = <upsert|delete>
* Specifies the type of action to take on the URL.
* If "upsert", ITSI inserts or updates existing fields.
* If "delete", ITSI deletes the URL.
* There is no default.

param.kwargs = <dict>
* A dictionary of additional fields to pass to the URL.
* Optional.
* There is no default.

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_event_action_webhook]
* Trigger a POST call for the provided webhook url.

param.webhook_name = <string>
* The name of the triggered webhook.
* Required.

param.webhook_uri = <string>
* The URL of the webhook.
* Required.

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_event_action_snow_wrapper]
param.account = <list>
* The name of the account in which the incident is created.
* Required.

param.state = <string>
* The state of the incident.
* Optional.

param.configuration_item = <string>
* Configuration item.
* Optional.

param.contact_type = <string>
* The method by which the incident was reported.
* Optional.

param.assignment_group = <string>
* The name of the assignment group associated with the incident.
* Optional.

param.category = <string>
* The category of the incident.
* Required.

param.subcategory = <string>
* The subcategory of the incident.
* Optional.

param.impact = <number>
* The impact value of the incident.
* Optional.

param.urgency = <number>
* The urgency of the incident.
* Optional.

param.priority = <number>
* The priority of the incident, determined by the impact and urgency values.
* Optional.

param.short_description = <string>
* A brief description of the ITSI episode.
* Required.

param.correlation_id = <string>
* A brief description of the ServiceNow incident.
* Optional.

param.splunk_url = <link>
* An external drilldown link from the ServiceNow incident.
* You can use this setting to link back to the corresponding episode in ITSI.
* Optional.

param.custom_fields = <string>
* Custom fields.
* Optional.

param.closing_status = <list>
* Custom fields.
* Optional.

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_event_action_jira_wrapper]
param.api_token = <list>
* The name of the account in which the issue is created.
* Required.

param.project_key = <string>
* The Project Key is the prefix of the issue number.
* Required.

param.affected_version = <integer>
* Affected version for the issue
* Optional.

param.issue_type = <string>
* Type of the issue. For example {Epic | Bug | Story | Task}
* Required.

param.summary = <string>
* The summary of the Jira issue
* Required.

param.priority = <string>
* The priority of the Jira issue
* Optional.

param.custom_fields = <string>
* All the custom fields created on the Jira project
* Optional.

param.component = <string>
* A component for the Jira issue
* Optional.

param.label = <string>
* A label of the Jira issue
* Optional.

param.jira_key = <string>
* A jira key to be updated
Default: $result.jira_ticket_id$

param.description = <string>
* A description of the Jira issue
* Optional.

param.correlation_id = <string>
* Group id of the episode which is used in internal logs
* Optional.

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_event_action_clear_sim_incidents]
* Clear all Splunk Infrastructure Monitoring incidents within an ITSI episode. An incident
  in Splunk Infrastructure Monitoring is the combination of an alert event and a clear event.

python.required = 3.9
* Specifies the required Python version for this alert action.

[itsi_import_objects]
* Import entity and service object data.

param.backfill_enabled = <boolean>
* Whether to enable backfill on all KPIs in linked service templates.
* Optional.
* Default: 0

param.entity_description_fields = <string>
* A list of fields that represents the description of an entity.
* Optional.

param.entity_field_mapping = <string>
* A key-value mapping of fields to re-map to other fields in the data.
* Follows a <field> = <Splunk search field> format.
* For example, ip1 = dest, ip2 = dest, storage_type = volume
* Use this setting to rename a field or column to an alias or info value.
* Optional.

param.entity_identifier_fields = <string>
* A list of fields that represent identifier data of an entity.
* Optional.

param.entity_informational_fields = <string>
* A list of fields that represent the informational data of an entity.
* Optional.

param.entity_merge_field = <string>
* The field that should be used when resolving conflicts between entities.
* Optional.

param.entity_merge_fqdn = <boolean>
* Whether the entity relies on FQDN match to find duplicates to merge.
* Optional.
* Default: 0

param.entity_status_tracking = <boolean>
* Whether the discovery search contributes to entity status calculation.
* Optional.
* Default: 1

param.entity_title_field = <string>
* The field that represents the title of an entity.
* Optional.

param.entity_type_field = <string>
* The field that matches the title for the entity type that is associated with an entity.
* Optional.

param.field_level_update_type = <string>
* Field level conflict resolution for duplicate entities merge.
* Optional.

param.service_dependents_fields = <string>
* A list of fields that indicate service dependencies.
* Optional.

param.service_description_fields = <string>
* A list of fields that represents the description of a service.
* Optional.

param.service_tags_field = <string>
* A list of fields that represents one or more tags to be added to a service.
* Optional.

param.service_enabled = <boolean>
* Whether or not imported services should be enabled.
* Optional.
* Default: 0

param.service_team = <string>
* The ITSI team that the imported services belong to.
* Optional.
* Default: default_itsi_security_group

param.service_templates_config = <string>
* A dictionary of key-value pairs that maps entity rules to service templates.
* Optional.

param.service_template_field = <string>
* Determines which service template a service is linked to.
* Optional.

param.service_title_field = <string>
* The field that represents the title of a service.
* Optional.

param.update_type = <string>
* The update/insertion method when uploading entities.
* APPEND: ITSI makes no attempt to identify commonalities between entities.
*   All information is appended to the table.
* UPSERT: ITSI appends new entries.  Existing entries (based on the value
*   found in the title_field) have additional information appended
*   to the existing record.
* REPLACE: ITSI appends new entries. Existing entries (based on the value
*   found in the title_field) are replaced by the new record value.
* Optional.
* Default: UPSERT

[itsi_summary_metrics_collect]
* Wraps the mcollect macro for converting event data into metrics and pushing it into the ITSI metrics summary index.

[itsi_event_action_episode_summarization]
* Trigger a call for invoking summarization

param.custom_queries = <string>
* The custom queries provided by the user for additional summarization data points
* Optional.

python.required = 3.9
* Specifies the required Python version for this alert action.