# This file contains possible settings you can use to configure ITSI inputs, register
# user access roles, and import services and entities from CSV files or search strings.
#
# There is an inputs.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To set custom
# configurations, place an inputs.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
# You must restart ITSI to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

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

# log_level = <DEBUG|INFO|WARN|ERROR>
# * This setting sets the logging level of each modular input.
# * Logging levels are in order of most to least verbose.
# * The logging level describes the type and/or quantity of output
#   that an application writes to a log file.
# * Set the logging verbosity of each modular input to specify how
#   much and what kind of information it writes to the log file.
# * Setting a log level gets you messages at that level and higher,
#   so default settings are typically INFO or WARN.

[itsi_user_access_init]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_user_access_init://<name>]
* A modular input that runs once during startup (or at the user's request)
  to register user access roles and capabilities with the SA-UserAccess module.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: WARN

app_name = <name>
* The Splunk application that has the user access roles and capabilities.
* Default: itsi

registered_capabilities = [true|false]
* Indicates whether or not capabilities have already been registered with ITSI.
* If true, the 'itsi_user_access_init' input does not re-register capabilities.
* If false, 'itsi_user_access_init' registers ITSI capabilities again.
* Default: false

[configure_itsi]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[configure_itsi://<name>]
* A configuration input that runs once (or at the user's request) to pull
  entities from the configuration file system into the App Key Value (KV) Store.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: WARN

is_configured = ""
* Left it for backwards compatibility.

[itsi_csv_import]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_csv_import://<string>]
* A modular input that periodically uploads CSV data into the KV Store.
* The CSV file must contain headers for the import to work properly.
* This input runs every 4 hours or after a Splunk software restart.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: WARN

import_from_search = <boolean>
* Indicates whether to import data from a CSV file or a Splunk search.
* If "true", this input imports data from the search specified by 'search_string'.
* If "false", this input imports CSV data from the path specified by  'csv_location'.
* This setting is required, and the input does not run if the setting is
  not present.
* There is no default.

csv_location = <path>
* The location on disk of the CSV file to import.
* NOTE: The disk must be local to the search head. Cloud storage is unacceptable.
* This setting is required if you import data from a CSV file
  (if you set 'import_from_search' to "false").
* There is no default.

search_string = <string>
* The Splunk search string that generates the data to import.
* This setting is required if you import from a search string
  (if you set 'import_from_search' to "true").
* There is no default.

service_security_group = <string>
* The ITSI team that the imported services belong to.
* Use teams to group services by department, organization, or
  type of service and control access to the services.
* This setting is required, and the input does not run if the setting is
  not present.
* There is no default.

index_earliest = <integer>
* Specify the earliest _indextime, in minutes, for the time range of your search.
* This setting is required if you import from a search string
  (if you set 'import_from_search' to "true").
* Default: -15m

index_latest = <integer>
* Specify the latest _indextime, in minutes, for the time range of your search.
* This setting is required if you import from a search string
  (if you set 'import_from_search' to "true").
* Default: now

entity_title_field = <string>
* The column name in the CSV file, or the field in the search, to import
  the entity title from.
* This field serves as the informal identifier of the entity.
* There is no default.

entity_merge_field = <string>
* The column name in the CSV file, or the field in the search, to import
  the entity merge field from.
* There is no default.

entity_relationship_spec = <dict>
* A dictionary of key:value pairs that specifies how
  'entity_title_field' associates with other fields and in what relationship.
* NOTE: This setting is unused.
* For example,
  {"hosts": "vm1, vm2", "hostedBy": "host_id"}, or
  {"hosts": ["vm1", "vm2"], "hostedBy": "host_id"}.
* For a record that has values for fields: vm1, vm2, host_id,
  <'entity_title_field' value>, three relationships are extracted:
  <value for 'entity_title_field'> hosts <value for vm1>
  <value for 'entity_title_field'> hosts <value for vm2>
  <value for 'entity_title_field'> hostedBy <value for host_id>
* There is no default.

selected_services = <comma-separated list>
* A list of existing services to associate the imported entities with.
* DEPRECATED.
* There is no default.

service_rel = <comma-separated list>
* A list of existing service relationships.
* DEPRECATED.
* Use this setting to represent service dependencies in ITSI.
* There is no default.

service_dependents = <comma-separated list>
* A list of child columns in the CSV file, or child fields in the search,
  that indicate service dependencies.
* There is no default.

entity_service_columns = <comma-separated list>
* A list of services found in the CSV file or search that are to be
  associated with the entity for the row.
* DEPRECATED.
* There is no default.

entity_identifier_fields = <comma-separated list>
* A list of columns found in the CSV file or fields in the search
  that identify the entities (entity aliases).
* There is no default.

entity_description_column = <comma-separated list>
* A list of columns found in the CSV file or fields in the search
  that describe the entities.
* There is no default.

entity_informational_fields = <comma-separated list>
* A list of informational columns in the CSV file or fields in the search.
* These are non-identifying fields for the entities.
* There is no default.

entity_field_mapping = <key-value pairs>
* A key-value mapping of fields to re-map to other fields in your data.
* Follows a <CSV field> = <Splunk search field> format.
* For example, ip1 = dest, ip2 = dest, storage_type = volume
* Use this setting to rename a field or column to an alias or info value.
* There is no default.

service_title_field = <string>
* The field to import the service title from.
* This field is the informal identifier of the service.
* There is no default.
* This setting is required if you import services.

service_description_column = <comma-separated list>
* A list of columns in the CSV file or fields in the search
  that describe the services.
* There is no default.

service_tags_field = <comma-separated list>
* A list of columns in the CSV file or fields in the search
  that add descriptor tags to the services.
* There is no default.

service_enabled = <boolean>
* Whether or not imported services are enabled.
* Default: false

service_template_field = <string>
* This setting determines which service template a service is linked to.
* There is no default.

template = <dict>
* A dictionary of key:value pairs that maps entity rules to service templates.
* For example,
  {"test_template_2":{"entity_rules":[{"rule_items":
  [{"rule_type":"matches","field_type":"alias","field":"whoa","value":"doe"}],
  "rule_condition":"AND"}]},"test_template_1":{"entity_rules":[{"rule_items":
  [{"rule_type":"matches","field_type":"alias","field":"blah","value":"da"}],
  "rule_condition":"AND"}]}}
* CAUTION: Do not change this setting.
* There is no default.

backfill_enabled = <boolean>
* This setting determines whether to enable backfill on all
  Key Performance Indicators (KPIs) in linked service templates.
* Backfill is the process of getting historical KPI data.
* ITSI backfills the KPI summary index (itsi_summary). You must have
  indexed adequate raw data for the backfill period.
* There is no default.

update_type = <APPEND|UPSERT|REPLACE>
* The update/insertion method when uploading entities.
* This setting is required, and the input will not run if the setting is
  not present.
* APPEND: ITSI makes no attempt to identify commonalities between entities.
  All information is appended to the table.
* UPSERT: ITSI appends new entries.  Existing entries (based on the value
  found in the title_field) have additional information appended
  to the existing record.
* REPLACE: ITSI appends new entries. Existing entries (based on the value
  found in the title_field) are replaced by the new record value.
* There is no default.

interval = <integer>
* The interval, in seconds, that determines how often this input runs.
* There is no default.

[itsi_async_csv_loader]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_async_csv_loader://<name>]
* A modular input that periodically uploads CSV data into the KV store.
* The file must contain headers for the import to work properly.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: WARN

import_from_search = <boolean>
* Indicates whether to import data from a CSV file or a Splunk search.
* If "true", this input imports data from the search specified by 'search_string'.
* If "false", this input imports CSV data from the path specified by  'csv_location'.
* This setting is required, and the input does not run if the setting is
  not present.
* There is no default.

csv_location = <path>
* The location on disk of the CSV file to import.
* NOTE: The disk must be local to the search head. Cloud storage is unacceptable.
* This setting is required if you import data from a CSV file
  (if you set 'import_from_search' to "false").
* There is no default.

search_string = <string>
* The Splunk search string that generates the data to import.
* This setting is required if you import from a search string
  (if you set 'import_from_search' to "true").
* There is no default.

index_earliest = <integer>
* Specify the earliest _indextime, in minutes, for the time range of your search.
* This setting is required if you import from a search string
  (if you set 'import_from_search' to "true").
* Default: -15m

index_latest = <integer>
* Specify the latest _indextime, in minutes, for the time range of your search.
* This setting is required if you import from a search string
  (if you set 'import_from_search' to "true").
* Default: now

entity_title_field = <string>
* The column name in the CSV file, or the field in the search, to import
  the entity title from.
* This field serves as the informal identifier of the entity.
* There is no default.

entity_merge_field = <string>
* The column name in the CSV file, or the field in the search, to import
  the entity merge field from.
* There is no default.

entity_relationship_spec = <dict>
* A dictionary of key:value pairs that specifies how
  'entity_title_field' associates with other fields and in what relationship.
* NOTE: This setting is unused.
* For example,
  {"hosts": "vm1, vm2", "hostedBy": "host_id"}, or
  {"hosts": ["vm1", "vm2"], "hostedBy": "host_id"}.
* For a record that has values for fields: vm1, vm2, host_id,
  <'entity_title_field' value>, three relationships are extracted:
  <value for 'entity_title_field'> hosts <value for vm1>
  <value for 'entity_title_field'> hosts <value for vm2>
  <value for 'entity_title_field'> hostedBy <value for host_id>
* There is no default.

selected_services = <comma-separated list>
* A list of existing services to associate the imported entities with.
* DEPRECATED.
* There is no default.

service_rel = <comma-separated list>
* A list of existing service relationships.
* DEPRECATED.
* Use this setting to represent service dependencies in ITSI.
* There is no default.

service_dependents = <comma-separated list>
* A list of child columns in the CSV file, or child fields in the search,
  that indicate service dependencies.
* There is no default.

entity_service_columns = <comma-separated list>
* A list of services found in the CSV file or search that are to be
  associated with the entity for the row.
* DEPRECATED.
* There is no default.

entity_identifier_fields = <comma-separated list>
* A list of columns found in the CSV file or fields in the search
  that identify the entities (entity aliases).
* There is no default.

entity_description_column = <comma-separated list>
* A list of columns found in the CSV file or fields in the search
  that describe the entities.
* There is no default.

entity_informational_fields = <comma-separated list>
* A list of informational columns in the CSV file or fields in the search.
* These are non-identifying fields for the entities.
* There is no default.

entity_field_mapping = <key-value pairs>
* A key-value mapping of fields to re-map to other fields in your data.
* Follows a <CSV field> = <Splunk search field> format.
* For example, ip1 = dest, ip2 = dest, storage_type = volume
* Use this setting to rename a field or column to an alias or info value.
* There is no default.

field_level_update_type = <dict>
* A dictionary of key:value pairs that specifies how alias/informational fields
  should be resolved if duplicate entities merge.
* For example,
  {"<field_name>": "<update_type>", "host": "replace", "ip": "skip", ...}
* There is no default.

service_title_field = <string>
* The field to import the service title from.
* This field is the informal identifier of the service.
* There is no default.
* This setting is required if you import services.

service_description_column = <comma-separated list>
* A list of columns in the CSV file or fields in the search
  that describe the services.
* There is no default.

service_tags_field = <comma-separated list>
* A list of columns in the CSV file or fields in the search
  that add descriptor tags to the services.
* There is no default.

update_type = <APPEND|UPSERT|REPLACE>
* The update/insertion method when uploading entities.
* This setting is required, and the input will not run if the setting is
  not present.
* APPEND: ITSI makes no attempt to identify commonalities between entities.
  All information is appended to the table.
* UPSERT: ITSI appends new entries.  Existing entries (based on the value
  found in the title_field) have additional information appended
  to the existing record.
* REPLACE: ITSI appends new entries. Existing entries (based on the value
  found in the title_field) are replaced by the new record value.
* There is no default.

[itsi_migration_queue]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_migration_queue://<name>]
* A modular input that checks the ITSI migration queue
* If the queue is not empty, start a migration with params stored in the queue.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_refresher]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_refresher://<name>]
* A modular input that processes deferred methods using a single queue processor.
* Tracks relational objects and dependencies.
* This input detects conflicts and ensures consistency across ITSI.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_consumer]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_consumer://<name>]
* A modular input that processes deferred methods using multiple queues
  across the Splunk environment.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

number_of_thread = <integer>
* Sets the thread pool count, or the number of actions that can execute in
  parallel within a single job. For example, multiple independent actions
  on different entities can execute at once.
* Default: 8

high_job_ratio = <integer>
* Executes high priority jobs N:1 compared to normal priority jobs.
* Setting this value to 0 causes all jobs to execute regardless of priority.
* Default: 0

job_timeout = <integer>
* The maximum amount of time, in seconds, that a job can execute. Jobs that
  exceed this time limit will not run, and generate a timeout error.
* Setting this value to 0 turns off the job timeout.
* Default: 0

max_retries = <integer>
* The number of times a failed job can automatically attempt to run again.
* Setting this value to 0 turns off retry attempts.
* Default: 1

[itsi_backup_restore]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_backup_restore://<name>]
* A modular input that performs backup and restore operations by
  managing backup/restore jobs.
* If you restore ITSI from a backup of an older version of ITSI,
  migration begins during the restore process.
* The input runs runs every 5 seconds to check for the scheduled job.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_scheduled_backup_caller]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_scheduled_backup_caller://<name>]
* A modular input that manages ITSI backup schedules.
* For example, you might use this input if you want to back up ITSI
  every night at 1 am.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_service_template_update_scheduler]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_service_template_update_scheduler://<name>]
* A modular input that performs a scheduled sync from
  service templates to services every 15 minutes.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_backfill]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_backfill://<name>]
* A modular input that manages KPI backfill jobs.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_notable_event_archive]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_notable_event_archive://<name>]
* A modular input that moves notable events from the KV store
  to the index every hour.

owner = <string>
* Splunk cannot read the modular name unless a parameter is specified.
  Therefore, ITSI passes 'owner = <string>'.

[maintenance_minder]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[maintenance_minder://<name>]
* A modular input that runs every 60 seconds and populates
  the operative maintenance log based on configured maintenance windows.
* This input is responsible for putting services into maintenance mode.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[custom_threshold_window_minder]
python.version = python3
python.required = 3.9

[custom_threshold_window_minder://name]
* A modular input that runs every 60 seconds and populates
  the operative Custom threshold Window log based on configured custom threshold windows.
* This input is responsible for putting KPIs into custom threshold window.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[custom_threshold_window_overlaps_detector://name]
* A modular input that runs every 86400 seconds (24 hours) to populate
  the overlapping KPI for Custom threshold Windows.
* This input is responsible for updating the overlapping KPIs

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[service_sandbox_status_updater://name]
* A Job that will move all the Service Sandbox Objects
  to edit mode at restart.
* This is responsible for updating the Service Sandbox objects status.
log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_default_event_management_objects_loader]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_default_event_management_objects_loader://<name>]
* A modular input that loads the default aggregation polices and data integration connections.
* The default aggregation policy receives notable events that do
  not match the filtering criteria of any other aggregation policies.
* A data integration connection takes raw events from given source, applies the specified field mappings,
  and converts the raw events to notable events.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_default_correlation_search_acl_loader]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_default_correlation_search_acl_loader://<name>]
* A modular input that loads the Access Control List (ACL)
  for the default correlation searches provided with ITSI:
  "Monitor Critical Services Based on Health Score",
  "Splunk App for Infrastructure Alerts", and
  "Normalized Correlation Search".
* This input pulls ACL information from the KV store.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_notable_event_hec_init]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_notable_event_hec_init://<name>]
* A modular input that initializes HEC client on a search head by creating and
  showing pertinent HEC tokens.
* A new HEC token is acquired during a Splunk restart.
* The internal system populates the new HEC token automatically.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_hec_init]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_hec_init://<name>]
* A modular input that initializes HEC client on a search head by creating and
  showing pertinent HEC tokens.
* A new HEC token is acquired during a Splunk restart.
* The internal system populates the new HEC token automatically.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_queue_consumer_size_checker]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 18.0 and later, this attribute lets you select
  which Python version to use.

[itsi_queue_consumer_size_checker://name]
* A modular input that checks the size of the queue consumer.
* This input is responsible for showing the splunk message when the collection
  crosses the provided threshold

timeout = <integer>
* The timeout period, in seconds, that ITSI uses when a
  user reclaims an expired job.
* Default: 7200 (2 hours)

system_user_name = <string>
* The username of the system.
* Default: splunk-system-user

collection_size_initial_threshold = <integer>
* The size of the collection, in integer, to specify the limit after which message will be shown
* Default: 10000 (10K)

collection_size_final_threshold = <integer>
* The size of the collection, in integer, to specify the limit after which message will be shown
* Default: 100000 (100K)

[itsi_notable_event_actions_queue_consumer]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_notable_event_actions_queue_consumer://name]
* A modular input that acts as a consumer of the queue for executing
  notable event actions, such as pinging a host or running a script.
* This setting is primarily used by the rules engine.

exec_delay_time = <integer>
* The amount of time, in seconds, to delay execution of a notable event action.
* Default: 0

batch_size = <integer>
* The number of jobs to pick up in a single request from the
  notable event actions queue.
* Default: 5

timeout = <integer>
* The timeout period, in seconds, that ITSI uses when a
  user reclaims an expired job.
* Default: 7200 (2 hours)

system_user_name = <string>
* The username of the system.
* Default: splunk-system-user

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_notable_event_actions_consumer_assigning]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_notable_event_actions_consumer_assigning://name]
* A modular input used for High Scale Event Analytics. This assigns consumer IDs to
notable event actions, and queues those actions to be executed in a separate queue.
Notable event actions are executed on episodes, for example: adding a comment, creating
a ServiceNow incident, or changing the episode severity.

consumer_refresh_interval = <integer>
* The amount of time, in seconds, to wait before fetching a list of action consumers that
are enabled. Action consumers are modular inputs that execute actions on
episodes, and are not often turned on or off.
* Default: 60

delete_objects_interval = <integer>
* The amount of time, in seconds, to wait before objects are deleted in the actions queue.
* Objects marked for deletion are actions that have consumer IDs already assigned and have
been picked up from the temporary actions queue, and are now stored in the regular
actions queue.
* Keep delete intervals to a minimum.
* Default: 600

batch_size = <integer>
* The number of action objects to pick up in a single request from the temporary action queue (KV Store collection).
* Assign consumers to these action objects and batch save the objects in a single request to different action
queue (KV Store collection).
* Default: 1000

read_delay_time = <integer>
* The amount of time, in seconds, to delay reading actions from the KV Store collection.
* Default: 0.1

system_user_name = <string>
* The username of the system.
* Default: splunk-system-user

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_age_kpi_alert_value_cache]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_age_kpi_alert_value_cache://<name>]
* A modular input that cleans up the aged entries in the KPI summary cache.

retentionTimeInSec = <integer>
* Aging/retention time for entries present in the KPI summary cache.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_summary_metrics_backfill]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_summary_metrics_backfill://<name>]
* A modular input that migrates data from the itsi_summary index to the
  itsi_summary_metrics index by checking the metrics_backfill queue.

disabled = <boolean>
* Whether or not the modular input for metrics backfill is disabled
* Default : 1

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

metrics_backfill_throttle = <integer>
* The amount of time, in seconds, that the backfill function pauses between executing metrics backfill searches.
* Default: 10

metrics_backfill_length = <integer>
* The amount of time, in days, that the metrics backfill searches look back to migrate data
  into the itsi_summary_metrics index.
* Default: 3

metrics_backfill_concurrent_searches = <integer>
* The number of concurrent searches the backfill function runs at the same time. Having more
  concurrent searches allows backfill searches to complete faster but puts more load on the indexers.

[itsi_suite_enforcer]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_suite_enforcer://<name>]
* A modular input that enforces suite editions.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_backfill_record_cleanup]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_backfill_record_cleanup://<name>]
* A modular input that cleans backfill record.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

interval = <integer>
* The interval, in seconds, that determines how often this input runs.
* There is no default.

[itsi_content_pack_authorship]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

build_timeout = 3600
* If content pack stuck in build state for more than build_timeout
* which is default to 1 hour (3600 seconds) then it will be marked as Failed

[itsi_content_pack_authorship://<name>]
* A modular input that checks the ITSI content pack authorship queue
* If the queue is not empty, start a process to create content packs in the queue

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_upgrade_readiness]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

[itsi_upgrade_readiness://<name>]
* A modular input that checks for malformed KVStore objects in preparation for upgrade

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

interval = <integer>
* The interval, in seconds, that determines how often this input runs.
* There is no default.

[itsi_nats_mod_input]
python.version = {default|python|python2|python3}
python.required = 3.9

[itsi_nats_mod_input://name]
* Modular input that turns on NATS server for Event Analytics
  When the input is turned on, NATS server is started
* Interval is not specified. It will run only on start-up or when its enabled from UI (Data Inputs).

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_at_saved_search_rewriter]
python.version = {default|python|python2|python3}
python.required = 3.9

[itsi_at_saved_search_rewriter://<name>]
* This Modular Input rewrites AT saved searches based on the feature flag itsi-at-outlier-removal.
  If the flag is enabled it uses 'applyat' command for the AT saved searches which is a new command
  starting in 4.17.0 which provides outlier removal feature before Adaptive Thresholding,
  else it uses 'itsiat', the older version of AT.

* Interval is not specified - It will run only on start-up & when its enabled from UI (Data Inputs)

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[script://$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_adhoc_re_init.py]
* This Modular Input script triggers the Rules Engine java process. Use the itsichangerulesengineprocess
  command which is used to toggle the itsi-rulesengine-adhoc feature and switch between Realtime mode and
  Adhoc mode.

shcluster_status_check = <boolean>
* Whether or not the ModInput performs a SHCluster status check
* Default: true

pulse_frequency = <integer>
* Frequency at which the script performs periodic SHCaptain status checks
* Default: 20

command.arg.1 = <string>
* First command line argument provided to initialize Rules Engine. Do not change.
* Default: -J-Xmx8192M

command.arg.2 = <string>
* Second command line argument provided to initialize Rules Engine. Do not change.
* Default: -Dlog4j.configurationFile=../default/log4j_rules_engine.xml

command.arg.3 = <string>
* Third command line argument provided to initialize Rules Engine. Do not change.
* Default: -DitsiRulesEngine.configurationFile=../default/itsi_rules_engine.properties

command.arg.4 = <string>
* Fourth command line argument provided to initialize Rules Engine. Do not change.
* Default: -Dfile.encoding=UTF-8

command.arg.5 = <string>
* Fifth command line argument provided to initialize Rules Engine. Do not change.
* Default: -Dconfig.file=../lib/java/event_management/pekko_application.conf

command.arg.6 = <string>
* Sixth command line argument provided to initialize Rules Engine. Do not change.
* Default: -DitsiRulesEngine.localConfigurationFile=../local/itsi_rules_engine.properties

command.arg.7 = <string>
* Seventh command line argument provided to initialize Rules Engine. Do not change.
* Default: modInput

[itsi_entities_status_cache_cleanup]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

interval = <integer>
* The interval, in seconds, that determines how often this input runs. By default it runs every day.
* Default: 86400

[itsi_entities_status_cache_cleanup://<name>]
* A modular input that helps in removing deleted entities reference from the
  itsi_bulk_import_entities_status_cache collection

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_duplicate_entities_manager]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

interval = <integer>
* The interval, in seconds, that determines how often this input runs. By default it runs every day.
* Default: 5

[itsi_duplicate_entities_manager://<name>]
* A modular input that computes duplicate entities, aliases and remediates them

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_duplicate_entities_nightly_job_scheduler]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

interval = <cron|integer>
* The cron expression or integer in seconds, that determines how often this input runs. By default it runs every night 12:00 AM.
* Default: 0 0 * * *

[itsi_duplicate_entities_nightly_job_scheduler://<name>]
* A modular input that enqueues a duplicate entities generation job

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[script://$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py]
* This Modular Input script triggers the Rules Engine java process. Use the itsichangerulesengineprocess
  command which is used to toggle the itsi-rulesengine-queue feature and switch between Realtime mode and
  Queue mode.

shcluster_status_check = <boolean>
* Whether or not the ModInput performs a SHCluster status check
* Default: true

pulse_frequency = <integer>
* Frequency at which the script performs periodic SHCaptain status checks
* Default: 20

enable_java_version_check = <boolean>
* Validates if Java version 1.8 and above is installed and running.
* true

command.arg.1 = <string>
* First command line argument provided to initialize Rules Engine. Do not change.
* Default: -J-Xmx8192M

command.arg.2 = <string>
* Second command line argument provided to initialize Rules Engine. Do not change.
* Default: -Dlog4j.configurationFile=../default/log4j_rules_engine.xml

command.arg.3 = <string>
* Third command line argument provided to initialize Rules Engine. Do not change.
* Default: -DitsiRulesEngine.configurationFile=../default/itsi_rules_engine.properties

command.arg.4 = <string>
* Fourth command line argument provided to initialize Rules Engine. Do not change.
* Default: -Dfile.encoding=UTF-8

command.arg.5 = <string>
* Fifth command line argument provided to initialize Rules Engine. Do not change.
* Default: -Dconfig.file=../lib/java/event_management/akka_application.conf

command.arg.6 = <string>
* Sixth command line argument provided to initialize Rules Engine. Do not change.
* Default: -DitsiRulesEngine.localConfigurationFile=../local/itsi_rules_engine.properties

command.arg.7 = <string>
* Seventh command line argument provided to initialize Rules Engine. Do not change.
* Default: -Dlog4j2.contextSelector=org.apache.logging.log4j.core.async.AsyncLoggerContextSelector

command.arg.8 = <string>
* eighth command line argument provided to initialize Rules Engine. Do not change.
* Default: itsiRulesEngine.natsCertDir=../../../auth/nats

command.arg.9 = <string>
* ninth command line argument provided to initialize Rules Engine. Do not change.
* Default: queueMode

[itsi_sandbox_sync_log_cleaner]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

  interval = <integer>
* The interval, in seconds, that determines how often this input runs. By default it runs every day.
* Default: 86400

[itsi_sandbox_sync_log_cleaner://<name>]
* A modular input that helps in removing sandbox sync logs from
  itsi_sandbox_sync_log collection

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_exported_episode_files_cleaner]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

interval = <integer>
* The interval, in seconds, that determines how often this input runs. By default it runs every day.
* Default: 86400

[itsi_exported_episode_files_cleaner://name]
log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_entity_AT_auto_onboarding://name]
log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_nats_certificates_auto_rotation]
* The interval, in seconds, that determines how often this input runs. By default it runs every 15 days.
* Default: 1296000

[itsi_nats_certificates_auto_rotation://nats_certificates_auto_rotation]
log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO


[itsi_maintenance_calendar_retention]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

interval = <cron|integer>
* The cron expression or integer in seconds, that determines how often this input runs. By default it runs every night 12:00 AM.
* Default: 0 0 * * *

disabled = 0|1
* Whether this stanza is enabled or disabled.
* If "1", the stanza is disabled.
* If "0", the stanza is enabled.

[itsi_maintenance_calendar_retention://<name>]
* A modular input that runs every 60 seconds and populates
  the operative maintenance log based on configured maintenance windows.
* This input is responsible for putting services into maintenance mode.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO

[itsi_episode_summarization_cleanup]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.

interval = <cron|integer>
* The cron expression or integer in seconds, that determines how often this input runs. By default it runs every 5 minutes.
* Default: */5 * * * *

[itsi_episode_summarization_cleanup://<name>]
* A modular input that helps in cleaning up summarization jobs that have been running for an extended duration.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO
