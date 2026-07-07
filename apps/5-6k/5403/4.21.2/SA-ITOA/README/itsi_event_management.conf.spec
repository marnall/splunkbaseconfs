# This file contains attributes and values for configuring different ITSI
# event management features.
#
# There is an itsi_event_management.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_event_management.conf in
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
* A setting that you want to enable for Episode Review.
* Supported settings (stanzas) are 'similar_episodes' and 'common_fields'

[similar_episodes]
default_fields = <comma-separated list>
* The list of field names selected by default in Similar Episodes pane
* For example, ["title","description","host"]
* Default: ["title"]

[common_fields]
number_of_fields = <integer|all>
* The number of common fields to display on the Common Fields tab of an episode.
* Can be a positive integer or the word "all" to display all common fields.
* For example, "50" displays 50 common fields.
* Default: 50

[migration]
The settings in this stanza apply to upgrades from pre-4.6.0 ITSI versions to
version 4.6.0 or later. The settings support the addition of the following
fields to the itsi_notable_group_system KV store collection: parent_group_id,
split_by_hash, first_event_id, and group_template_id. If you are upgrading from
ITSI version 4.6.0 or later, these settings no longer apply.

kv_store_batch_size = <integer>
* The maximum batch size of fetch requests to the itsi_notable_group_system
  KV store collection.
* For example, if set to "10000", 10,000 objects are fetched
  from the KV store in a single fetch request.
* Default: 10000

cluster_manager_check_required = <integer>
* Whether a cluster manager check is required before migration starts.
* If set to "1", a cluster manager check is required.
* If set to "0", migration proceeds without a cluster manager check.
* Default: 1

itsi_grouped_alerts_index_lookback = <integer>
* The amount of time, in days, to look back to fetch old active groups from the itsi_grouped_alerts index.
* For example, if set to "60", active groups from last two months are fetched from the index.
* Default: 90

itsi_grouped_alerts_index_search_wait_time = <integer>
* The amount of time, in seconds, to wait for the search job to return results from the itsi_grouped_alerts index.
* For example, if set to "900", the search job will wait for 15 minutes to return results from the index.
* Default: 7200

[precheck]
The settings in this stanza apply to upgrades from pre-4.6.0 ITSI versions to
version 4.6.0 or later. The settings suppport the prechecks that runs before
the migration happens.

kv_store_collection_size_limit = <integer>
* The maximum number of a single object type allowed in any KV store collection.
* For example, if set to "1000000", 1000000 objects of a single type are allowed in a KV store collection.
* Default: 1000000

[tracked_alert]
The settings in this stanza apply to notable events.

sort_notable_events = <integer>
* Decides whether notable events will be sorted based on _time or not.
* If set to "1", sort notable events.
* If set to "0", do not sort notable events.
* Default 0

[ingest_service]
The settings in this stanza apply to notable events & NEAP's data for Ingest Service.

notable_events_batch_size = <integer>
* The maximum number of events that can be sent to the ingest service at one time.

max_retries = <integer>
* The maximum number of attempts to retry sending the event to the ingest service.

retry_interval = <integer>
* The interval, in seconds, to retry sending an event to the ingest service.

[event_onboarding]
The settings in this stanza apply to onboarding external data sources to monitor as events using ITSI Event Analytics.

preview_results_limit = <integer>
* The maximum number of results that return in a preview of the transformed fields for the connection.
* Default: 300

preview_results_search_wait_time = <integer>
* The maximum amount of time, in seconds, to wait for the search job that returns preview results to complete.
  For example, if set to "10", the system waits 10 seconds for the search job to complete.
  If there is no time limit, use "-1" as the value.
* Default: 10

special_characters = <string>
* Comma separated list of special characters. Do not include spaces surrounding the special characters.
  In the example shown there is a period and an asterisk. Example: .,*
* Default: .,*,},{

required_fields = <string>
* Comma separated list of required fields for event onboarding.
* Default: title, severity_id, owner, status, src, signature, subcomponent, alert_identifier_fields, vendor_severity


[export_csv]
The setting to export CSV

max_batch_size = <integer>
* The maximum number of results in one batch to process
* Default: 5000

delete_period = <integer>
* The time in days for which the exports will exist for
* Default: 7 days

[service_topology]
The settings in this stanza apply to the getservicetopology command and the get_service_trees REST API.

service_topology_parent_level = <integer>
* The maximum number of parent levels to fetch for the service topology
* Default: 3

service_tree_cache_enabled = <integer>
* Enables or disables in-memory caching for the get_service_trees API.
* If set to "1", responses are cached when the caller passes use_cache=1 (e.g. getservicetopology).
* If set to "0", caching is disabled. Callers that omit use_cache=1 never use the cache.
* Default: 1

service_tree_cache_ttl_seconds = <integer>
* The time-to-live in seconds for cached get_service_trees results.
* Cached entries expire after this duration and are evicted on the next cache miss.
* Only applies when service_tree_cache_enabled is 1.
* Minimum: 1
* Default: 60

service_tree_rest_timeout_seconds = <integer>
* Timeout in seconds for the get_service_trees REST call used by getservicetopology.
* Prevents the command from hanging indefinitely if the API does not respond.
* Minimum: 1
* Default: 60

[telemetry]
List of event management telemetry search queries

latency_query = <string>
* Query for rules engine event processing latency

queue_enabled_query = <string>
* Query to see if nats is enabled

cpu_mem_query = <string>
* Query to view cpu and memory usage in nats environment

backfill_rate_query = <string>
* Query for backfill per minute in last 24 hours

events_processed_rate_query = <string>
* Query for events processed per minute by rules engine

messages_pushed_to_nats_rate_query = <string>
* Query for nats ingestion rate

rules_engine_start_stop_query = <string>
* Query for rules engine starts and stops in the last 24 hours