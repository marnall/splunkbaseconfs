#
# Proxy settings
#
[proxy]
* Settings in this stanza control the proxy settings for calls to Recorded
  Future's API.

proxy_enabled = <bool>
* Determines whether a proxy is used.

proxy_type = <string>
* The type of proxy, currently not used.

proxy_url = <string>
* The hostname/ip of the proxy. Hostnames, IP numbers (including IPv6)
  are allowed.

proxy_port = <integer>
* The IP number of the proxy.

proxy_username = <string>
* The username to the proxy. If authentication is not required,
  leave this unset or empty. The password will be stored in Splunk's
  password store.

proxy_rdns = <bool>
* Not used.

proxy_proto = <string>
* Indicate the proxy protocol, http or https

ssl_verify_proxy = <bool>
* Whether to verify the SSL certificates of the proxy server or not.
  Default is true.

#
# Log related settings
#
[logging]
loglevel = <string>
* Log level may be one of DEBUG, INFO, WARNING, ERROR or CRITICAL.

#
# Mirrors settings from app.conf
#
[app_conf]
version = <string>
* The current version of the app.

#
# Settings
#
[settings]
* These are the common settings for the app.

recorded_future_api_url = <string>
* The URL used to access Recorded Future's API. This may be changed under
  some circumstances.

verify_ssl = <bool>
* From old version of integration. Whether SSL verification is enabled or not.
  This may be disabled in some circumstances.

ssl_verify = <bool>
* Whether SSL verification is enabled or not. This may be disabled in some
  circumstances.

es_enabled = <bool>
* If Splunk Enterprise Security is present on the system this option can be
  set to true. This will enable the Splunk Enterprise Security specific
  features of the app.
* This field is only used on a Splunk Enterprise Security system.

enrichment_mode = <string>
* This can be share-data, cached-share, or cached-not-share. This value
  indicates how enrichment using AR is performed. Naming is bad.
* share-data indicates that it is using realtime data.
* cached-share indicates that it is using cached data
* cached-not-share is deprecated since 2.0.1
* This field is only used on a Splunk Enterprise Security system.

force_es = <bool>
* In some cases, detection of Splunk Enterprise Security can fail. Setting
  this to true will force enablement of Splunk Enterprise Security features
  in the app.
* This field is only used on a Splunk Enterprise Security system.

v2_upgrade = <bool>
* This indicates whether the Upgrade script (from v1.* to v2) has been run.

rfclient_timeout = <integer>
* The timeout for getting completing requests to recordedfuture api.

asi_project_id = <string>
* DEPRECATED since v2.9.0. ID of the project in ASI (SecurityTrails).
asi_ssl_verify = <bool>
* Whether SSL verification is enabled or not for ASI API. This may be disabled in some
  circumstances.
asi_client_timeout = <integer>
* The timeout for getting completing requests to ASI api.
asi_config_migrated = <bool>
* Indicates whether the ASI config from old app was migrated before.


[privacy]
* These are privacy settings / sharing settings for metrics.

share_intelligence = <string>
* Indicates if the user is sharing data for adaptive response enrichment and threat hunt
* risk based alerting, correlations and sigma rule detections.

share_ti_data_model_matches = <string>
* Indicates if the user is sharing data from Splunk ES TI threat datamodel.

es_tracking = <string>
* Legacy tracking setting, no longer used since splunk 2.1.


[correlations]
* Settings for Correlations feature.

enabled = <bool>
* Indicates whether the Correlations feature is enabled.

es_deprecation_banner_dismissed = <bool>
* Indicates whether the ES Deprecation banner was dismissed.

#
# Enrichment Use Cases
#
[enrichment:<name>]
* Configures an enrichment view.
* <name> is the usecase_id associated with the view

desc = <string>
* A text describing the Enrichment view.

id = <string>
* The id of the view, should be identical to <name>

ioc_type = <string>
* The type of IOC. Supported values are ip, domain, hash, vulnerability,
  malware and url.

label = <string>
* The name of the view (used in the menu and view title).

menu_label = <string>
* The parent menu label (default Enrich).

menu_sort_order = <integer>
* Entries in the Enrich menu are sorted numerically using this value.

view_id = <string>
* This is the id of the view that corresponds to the use case.

#
# Correlation Use Cases
#
[correlation:<name>]
* Configures a Correlation Use Case <name>
* <name> is the usecase_id

cached = <bool>
* Specifies if the correlation is cached

category = <string>
* This is the type of IOC.
* Supported types: ip, domain, hash, vulnerability and url

selection = <string>
* This indicates whether the event selection as been guided or if it is custom.
* Supported types: guided and search

search = <string>
* This is the search used when selection is set to search.

field = <string>
* Deprecated since v2.4, use "fields" for Datamodel or "events" for Regular correlation types instead.
* This is the field name which value is correlated with
  the risk list that corresponds to the Use Case.

fields = <string>
* These are the field names which values are correlated with
  the risk list that corresponds to the Use Case.
* This is a JSON-encoded array.
* This field is required for Datamodel correlation type.

selected_event_fields = <string>
* These are the field names that are visible in the Correlation Dashboard.
* This is a JSON-encoded array.
* This field is required for Datamodel correlation type.

correlation_type = <string>
* This indicates the type of correlation.
* Supported types are Regular, Accelerated (deprecated as of v2.9.0) or Datamodel

id = <string>
* The id of the correlation, must be identical to <name>

events = <string>
* This is the configuration for events that will be correlated.
* This is a JSON-encoded array.
* This field is required for Regular correlation types.

delay_seconds = <integer>
* This is the offset correlation search time to compensate for event indexing delays.
* Special value -1 means that delay is deactivated.
* This field is Optional.

filter_search = <string>
* This is the search that is used for filtering out the events that should not be correlated.
* This field is required for Regular and Datamodel correlation types.

index = <string>
* Deprecated since v2.4, use "events" instead.
* This is the index containing the events that will be correlated.
* This field is required for Regular correlation types.

datamodel = <string>
* This is the data model that contains the events that will be correlated.
* This field is required for Datamodel correlation types.

section = <string>
* This is the section in the data model that contains the events that will
  be correlated.
* This field is required for Datamodel correlation types.

label = <string>
* This is the label of the Correlation view.

menu_label = <string>
* This field is not currently used.

search_id = <string>
* This is the id of the saved search used to implement the correlation
  search.
* A corresponding saved search is required and is created by the app.

sourcetype = <string>
* Deprecated since v2.4, use "events" instead.
* This is the source type used to select the events that will be correlated.

use_case = <string>
* This is the correlation feed use case id.
* A corresponding correlation_feed must be configured, the app configures one
  if needed.

view_id = <string>
* This is the view id.

disabled = <integer>
* Boolean integer deciding whether the correlation produces correlations or not.

[correlation_age_out:<datatype>]
* Correlation use cases write correlations to correlation cache files.
  There is one cache file per datatype. These cache files store a set
  number of lines of data and only for a set number of days.
  Entries outside the limits are pruned from the collection nightly.
* <datatype> is one of ip, domain, hash, vulnerability, url.
days = <integer>
rows = <integer>

#
# Correlation Feeds
#
[correlation_feed:<name>]
* Several functions requires risk lists to be downloaded. Correlation feeds
  serves this purpose.
* <name> is the usecase_id required by the API.
category = <string>
* Indicator category ('ip, domain, vulnerability, hash or url'
enabled = <bool>
* This indicates whether the feed will be downloaded or not.

#
# Search use cases
#
[search:<name>]
* Search use cases provides specialized search views.
* <name> is the usecase_id required by the API.

desc = <string>
* The title of the view.

id = <string>
* The usecase_id, must be identical to <name>.

label = <string>
* Label of the view.

menu_label = <string>
* Label of the parent menu.

menu_sort_order = <integer>
* Entries in the Search menu are sorted numerically using this value.

view_id = <string>
* This is the view id.

#
# Alert Use Cases
#
[alert:<name>]
* Implements Alert use cases
* <name> is an alert profile.
* Each profile defines a filter for which alerts to retrieve.

id = <string>
* Profile name, should be identical to <name>.

title = <string>
* Label of the profile.

view_id = <string>
* This is the view id.

alert_rule_id = <string>
* Alert Rule id as seen in the API.

alert_rule_igl = <string>
* Alert rule IGL

alert_rule_name = <string>
* Alert rule name

alert_status = <string>
* Select only alerts with this status.

enabled = <string>
* Indicates whether the profile is active or not.

version = <string>
* Integration version for which the alert was created.

limit = <integer>
* Fetch at most this many alerts.

triggered = <string>
* Select only alerts triggered in the indicated time range.

type = <string>
* Type of alert

ingestion_enabled = <bool>
* DEPRECATED. Ignored in v2.8.0+. Indicates whether the profile is enabled for ingestion (storing in KV store collection).

#
# Playbook Alert Use Cases
#
[playbook_alert:<name>]
* Contains information about available Playbook Alert category
* <name> is an alert category ID (e.g. domain_abuse).

alert_rule_id = <string>
* Alert ID as seen in the API.

alert_rule_name = <string>
* Alert name

enabled = <string>
* Indicates whether the profile is active or not.

version = <string>
* Integration version for which the alert was created.

alert_rule_igl = <string>
* Alert rule IGL

type = <string>
* Type of alert

ingestion_enabled = <bool>
* Indicates whether the alert is enabled for ingestion (storing in KV store collection).

#
# Feeds for the Threat Intelligence framework
#
[tifeed:<name>]
* Setup ingestion of a risk list into the TI framework.
category = <IOC_category>
id = <name>
label = <label>
rba = <rba_enabled bool>
use_case = <risklist>
threshold = <integer>
* risk threshold, anything above produces a finding (Notable event).


category = <string>
* The type of IOCs.

id = <string>
* Same as <name>

label = <string>
* Title of the feed

use_case = <string>
* The usecase_id of a corresponding correlation feed. If missing it will be
  added.

#
# Sigma Detection Rules use cases
#
[sigma:<name>]
* Sigma Detection Rules use cases that have either been dismissed or configured
id = <name>

* state can be active or inactive
state = <string>

* specifies if the configured rule has updates available
is_update_available = <bool>

* The original search before index and field substitution were performed.
* Ex: "CommandLine=\"* /C tasklist /FO TABLE > *AppData\\\\Local\\\\Temp\\*\\\\processes.txt\""
original_search = <string>

* The modified search with substitutions applied
* Ex: "index=main CommandLine=\"* /C tasklist /FO TABLE > *AppData\\\\Local\\\\Temp\\*\\\\processes.txt\""
modified_search = <string>

* title is the title of the rule
* Ex: "Sigma Rule: Babax / Osno  execution"
title = <string>

* form.* is the mapping for substituting the original search into the modified search
* Ex: form.index = main
*     form.%name0% = CommandLine
form.index = <string>
form.%name0% = <string>
form.%name1% = <string>
form.%name2% = <string>
form.%name3% = <string>
form.%name4% = <string>
form.%name5% = <string>
form.%name6% = <string>
form.%name7% = <string>
form.%name8% = <string>
form.%name9% = <string>
form.%name10% = <string>
form.%name11% = <string>
form.%name12% = <string>
form.%name13% = <string>
form.%name14% = <string>
form.%name15% = <string>

* querytab.* is to handle custom searches
* Ex: querytab.enabled = false
querytab = <bool>

#
# Miscellaneous Sigma Detection Rules settings - not accessible via GUI
#
[sigma_detection_age_out]
* Sigma detections are stored in a cache file. This cache file stores a set number
  of lines of data and only for a set number of days.
  Entries outside the limits are pruned from the collection nightly.
days = <integer>
rows = <integer>

[threat_hunt_result_age_out]
* Threat Hunt results are stored in a KV collection. This collection stores a set number
  of lines of data.
  Entries outside the limits are pruned from the collection nightly.
rows = <integer>

[alert_ingested_age_out]
* Ingested alerts are stored in a KV collection. This collection stores a set number
  of lines of data and only for a set number of days.
  Entries outside the limits are pruned from the collection nightly.
rows = <integer>
days = <integer>

[playbook_alert_ingested_age_out]
* Ingested playbook alerts are stored in a KV collection. This collection stores a set number
  of lines of data and only for a set number of days.
  Entries outside the limits are pruned from the collection nightly.
rows = <integer>
days = <integer>

[conf_version]
*
version = <float>
fail_counter = <integer>
lock = <bool>
* used during migrations between versions of the integration

[hidden_global_banner]
* Contains information about the hidden global banner
banner = <string>
* JSON of the hidden global banner

[alert_center_banner]
* DEPRECATED since v2.8.0. Contains details about the alert center banner if it has been dismissed
dismissed = <bool>
* dismissed is bool whether the banner is clicked away
options = [list]
*options is a list options that were available when the banner was dismissed

[playbook_alerts]
* Contains information about the playbook alerts
last_sync = <string>
* Date time string when the last sync for playbook alerts was performed


[alerts_ingestion]
* Contains information about the alert ingestion
last_sync_classic = <string>
* Date time string when the last ingestion for classic alerts occured
last_sync_playbook = <string>
* Date time string when the last ingestion for playbook alerts occured

[alert_index_settings]
playbook_index_enabled = <bool>
* playbook_index_enabled is playbook alerts enabled for indexing from KV store
classic_index_enabled = <bool>
* classic_index_enabled is classic alerts enabled for indexing from KV store

[autonomous_threat_operation_settings]
automatic_threat_hunt_run = <bool>
* Whether automatic threat hunt execution from Autonomous Threat Operation is enabled
* Requires default indicator settings to be configured
* Default: 1 (enabled)

ato_datamodel_delay_seconds = <integer>
* This is the offset correlation search time to compensate for event indexing delays for Datamodels.

[default_sigma_rule_indexes]
data = <jsonstring>
* An empty list by default. This contains data that the user have selected
* as default indexes to be used when running Sigma searches, together with the
* for said index.
