[ninja_apps://default]
* Get data from Splunk Apps installed in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_authtokens://default]
* Get data about the Splunk Authentication Tokens set up in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_configdir://default]
* Get data about the various knowledge objects in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_dashboards://default]
* Get data from Splunk Dashboards (Classic or Dashboard Studio) in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_datamodels://default]
* Get data from Splunk Datamodels configured in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_ds_apps://default]
* Get data about deployment apps deployed from your deployment servers.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_ds_clients://default]
* Get data about Splunk Deployment Clients reporting to your deployment server.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_ds_serverclasses://default]
* Get data from serverclasses configured on your Deployment Server.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_eventtypes://default]
* Get data from Splunk Eventtypes configured in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_hec_tokens://default]
* Get data about Splunk HEC Tokens configured in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_indexes://default]
* Get data about Splunk Indexes configured in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_kvstatus://default]
* Get the current status/health of the KV Store on your Splunk install.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_license_pools://default]
* Get the current status/configuration of Splunk license pools in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_licenses://default]
* Get the current status of installed Splunk Licenses in your Splunk Enterprise environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_lookups://default]
* Get data about Splunk Lookups configured in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_macros://default]
* Get data from Splunk Macros defined in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_messages://default]
* Get data from alerts and messages occurring across your Splunk Environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_partitions://default]
* Get data about the Disk Partitions Splunk is mounted on.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_roles://default]
* Get data about Splunk Roles being used in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_savedsearches://default]
* Get data about Splunk Alerts, Reports & Savedsearches configured in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_server_info://default]
* Get server and architecture info about Splunk instances your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_users://default]
* Get data about Splunk Users created in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)

[ninja_appsupport://default]
* Get data from Splunkbase about the version support & support type of Apps installed in your environment.
apps_lookup = <value>
* Please enter the lookup file with a unique list of apps installed in your environment. Admin Ninja App provides one: 'admin_ninja_unique_apps.csv' The lookup file CANNOT be private.
lookup_located_app = <value>
* Please enter the app FOLDER NAME that houses the previously entered lookup file.

[ninja_calcfields://default]
* Get data about configured Calculated Fields in your environment.
maximum_entries = <value>
* Limits number of entries returned. (In all cases but testing, this should be 0)