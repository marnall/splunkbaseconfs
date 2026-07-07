# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
# This file contains attributes and values for configuring the IT Service
# Intelligence (ITSI) app.
#
# There is an itsi_settings.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_settings.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk software to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# CAUTION: You can drastically affect your Splunk installation by changing these settings.
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how
# to configure this file.

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

[datamodels://<app>]
* 'app' is the ID for the app containing the datamodel.

blacklist = <datamodel_names_list>
* A pipe-separated list of data model external authentication interface
  (EAI) names (IDs) to blacklist.
* NOTE: Data model names do not contain pipe characters.
* The blacklisted data models will not be supported and remain hidden
  from the ITSI UI.

[cloud]
show_migration_message  = <boolean>
* Removes Cloud migration messages about deprecated files or apps from
  the logs because this process is done internally.

[backup_restore]
* Defines settings related to ITSI backup/restore.

job_queue_timeout = <seconds>
* The amount of time, in seconds, before the backup/restore job queue
  times out if the node owning the job has been down for too long to
  allow other jobs to proceed.
* The minimum supported timeout period is 3600 seconds (1 hour). The system
  sets the timeout to 3600 seconds when a value lower than this is set.
* Default: 43200 (12 hours)

max_workers_for_kpi_base_search_creation = <integer>
* Specifies the number of worker threads allocated to the ThreadPoolExecutor
  during the restore process. These threads are responsible for creating KPI Base Searches
  in parallel, helping to optimize performance and reduce restore time.
* It is recommended to set this value in line with the number of available CPU cores
  to avoid excessive context switching and ensure optimal performance.
* Default: 5

[import]
* Defines limits for import behavior.

import_batch_size = <integer>
* The minimum number of objects the importer should analyze before
  attempting a save to the KV store.
* Default: 1000

preview_sample_limit = <integer>
* The maximum number of rows that are returned from a preview request
  for a pending import.
* Default: 100

asynchronous_processing_threshold = <integer>
* The number of rows after which the bulk importer reads and stores the
  inbound content so that it can be processed at a more convenient time,
  rather than processing it immediately.

enable_empty_replace = <boolean>
* Defines whether to empty or keep the entity data during
  replace conflict resolution for inactive entities.
* If "1", inactive entities meta data (info, alias and entity-types fields) would be deleted.
* If "0", inactive entities meta data (info, alias and entity-types fields) would not be deleted.
* Default: 0

[metric_backfill]
* Defines backfill settings.

pre_calculation_window = <seconds>
* The size, in seconds, of the pre-calculation window for metric backfill.
* The smallest accepted value is 1. Increasing this value makes the
  backfill search faster, but less accurate.
* Default: 1

[sai_integration]
* DEPRECATED
* Defines Splunk App for Infrastructure (SAI) settings.

show_detection_modal = <boolean>
* DEPRECATED
* Whether or not to show the Splunk App for Infrastructure integration
  modal when the Service Analyzer loads.
* If "1", ITSI displays the integration modal.
* If "0", ITSI does not display the integration modal.
* Default: 1

[synced_kpi_scheduling]
disabled = <boolean>
* Indicates whether KPI saved searches have a randomized schedule or the same schedule.
* If "1", KPI saved searches run at staggered times throughout the scheduled interval.
* If "0", KPI saved searches all run at the same time during each scheduled interval.
* CAUTION: Changing this value to "0" can have a significant performance impact. KPI saved
* searches are designed to run at different times to prevent the search scheduler
  from becoming overloaded.
* Default = 1

[customsearch]
timeout_read = <seconds>
* The maximum number of seconds that an ITSI custom search command will attempt to
  read a chunk from the "chunked" custom search command protocol.
* Default: 3600

[episode_action_dispatch]
* Enables the ability to dispatch actions from a Splunk instance to be executed on
  another instance.
* Configure these settings in this stanza if you want to specify whether this Splunk
  instance will read actions and execute actions from another instance or dispatch
  actions to another Splunk instance.
* The settings in this stanza define the host's role. If configured as an 'executor' they
  also define the URI and username of the host for consuming Event Analytics episode actions.

role = <executor|manager|both>
* Whether the machine is executing actions, running core event analytics
  services, or both.
* If "executor", the host is only executing actions.
* If "manager", the host is only running core event analytics services.
* Default: both

remote_ea_mgmt_uri = <string>
* The Splunkd management URI from which to pull action jobs, in addition
  to other core event analytics services.
* The URI must include a scheme, host, and port.
* If an empty string, ITSI uses the local Splunk address to avoid the
  necessity of an update if a custom port or scheme is in use on the local
  Splunk instance.
* This setting is only required if 'role' is set to "executor".
* Default: empty string

remote_ea_username = <string>
* The username to use when communicating with the remote host for
  actions and updates.
* If you're on localhost, ITSI always uses the past session from Splunkd
  (the provided username is ignored in this case).
* This setting is only required if 'role' is set to "executor".
* Default: empty string

remote_ea_search_timeout = <integer>
* The timeout in seconds for executor host to wait for search results from the manager host.
* Default: 120

[lock]
service_template_sync_in_progress = <boolean>
* Whether a service template is currently syncing.
* If "1", at least one service template is syncing and it is not safe to upgrade.
* If "0", no service templates are syncing and it is safe to upgrade.
* CAUTION: Do not change this setting. It is updated dynamically by ITSI.
* Default: 0

[suite_configuration]
suite_level = <string>
* ITSI Cloud Suite level.
* CAUTION: This is not user changeable setting.

[object_batch_sizes]
* The values in this stanza control the size of batches (number of objects) fetched from the
* KVStore. For example, at a batch size of 1,000, a request that fetches 2,500 objects would be
* separated into two fetches of 1,000 and one fetch of 500.

* Object types come from SUPPORTED_ITSI_OBJECT_TYPES in statestore.py.

* These numbers are calculated with an assumption of a limit of 500 MB per query (from
* max_size_per_result_mb in limits.conf).
*   max_size_per_result_mb / max size of ITSI object = max batch size
*   Example: For services <= 2 MB, 500 MB / 2 MB = 250

default = <int>
* Default: 1000

entity = <int>
* Default: 50000

entity_filter_rule = <int>
* Default: 250

service = <int>
* Default: 250

glass_table = <int>
* Default: 25

kpi_entity_threshold = <int>
* Default: 10000

kpi_at_info = <int>
* Default: 10000

retire_applicable_entities_batch_size = <int>
* Default: 1000

operative_maintenance_log_batch_size = <int>
* Default: 1000

<itsi_object_type> = <int>


[rest]
* The values in this stanza control the timeout of rest calls.
* The value is in seconds.
* For example, if the rest_timeout is set to 300 means we will have a
* timeout set for rest calls will be 5 mins.

rest_timeout = <int>
* Default: 300


[upgrade_readiness]
kpi_base_search_threshold = <integer>
* Threshold for kpi base search to pose precheck failure on upgrade readiness dashboard.
* Default: 50000

dangling_service_reference_in_entities_disabled = <boolean>
* If true, the check will simply pass on the upgrade readiness dashboard.
* Default: 0

max_workers = <integer>
* Number of workers to be used in ThreadPoolExecutor for the pre-check Incorrect service linked to entity.
* Default: empty


[applyat]
* The values in this stanza control the settings related to the applyat custom
* search command used when creating and updating adaptive KPI thresholds.
kpi_level_batch_size = <int>
* The number of KPIs to be sent in each staggered batch processed by the applyat command.
* The batch size is based off a 7 day training window and should be scaled down when using
* 14, 30, and 60 day training windows.
* Default: 1000

entity_level_batch_size = <int>
* The number of Entity Configs to be sent in each staggered batch processed by the applyat command.
* The batch size is based off a 7 day training window and should be scaled down when using
* 14 day training windows.
* Default: 500

batch_timeout = <int>
* The number in seconds before the sub-searches dispatched by the itsibatchat custom search command
* will timeout.
* Default: 3600


[clear_pyc]
* The values in this stanza control the settings related to clear .pyc files
clearpyc_post_upgrade = <boolean>
* Whether or not to apply the clear pyc files
* If "1", the changes to clear pyc will be applied
* If "0", the changes to clear pyc will not be applied


[auto_remediate_upgrade_readiness]
* The values in this stanza control the settings related to Upgrade Readiness Mod Input MODES
auto_remediate_upgrade_readiness_issues = <boolean>
* If "1" Daily upgrade readiness job will run with AUTO_REMEDIATION mode
* If "0" Daily upgrade readiness job will run with PRECHECK mode

[advanced_run_fix_upgrade_readiness]
* The values in this stanza control the settings related to Upgrade Readiness Run Fix functionality
advanced_run_fix_upgrade_readiness_enabled = <boolean>
* If "1" user can see the run fix button for prechecks having advanced run fix capability
* If "0" user will not be able to do run fix for advanced prechecks

[apply_dst_to_at]
* The values in this stanza handles the threshold calculation while the daylight saving time changes.
* As per the provided timezone and offset the thresholds are calculated for the dst change for that timezone.
* Once 60 days has been passed for the DST transition this stanza would be disabled

disabled = <boolean>
* Whether or not to apply the changes done for calculating the thresholds done
* by adaptive thresholding while DST Change
* If "1", the changes done for calculating the threshold while DST Change will not be applied 
* If "0", the changes done for calculating the threshold while DST Change will be applied 
* Once 60 days has been passed for the DST transition this it would be set to 1
* Default: 1

timezone = <string>
* Contains the timezone of the user. Based on the user timezone the threshold calculation done by
* adaptive thresholding will be handled
* The format for the timezone should be "<Continent>/<City>" e.g. America/New_York
* Default: empty string

offset = <int>
* Contains the offset in seconds. Based on the offset the threshold calculation will be done by
* adaptive thresholding
* Default: 0

[upgrade_timeouts]
* The values in the stanza defines the timeout limits for various stages of upgrade

precheck_timeout = <int>
* The number of seconds to wait for the prechecks to complete
* Default: 1800

migration_timeout = <int>
* The number of seconds to wait for the migration to get complete
* Default: 14400

upgrade_timeout = <int>
* The number of seconds to wait for the whole upgrade process to get complete
* Default: 18000

[bulk_save_to_individual_save]
* The values in this stanza defines the ITOA objects supported for bulk save to individual save

itoa_objects = <list>
* List of objects supporting bulk save to individual save
