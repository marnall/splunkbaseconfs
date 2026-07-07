[cyera_collector://<name>]
cyera_account = Create an API clientID and Secret through your Cyera Application by following the KB article here: (https://support.cyera.io/hc/en-us/articles/20612742894231-Cyera-API).
enable_events = Enable collection of Cyera events.
enable_issues = Enable collection of Cyera issues.
enable_datastores = Enable collection of Cyera datastores.
enable_classifications = Enable collection of Cyera classifications.
enable_audit = Enable collection of Cyera audit logs.
retrieve_all_datastores = Retrieve all datastores every run instead of incremental changes.
interval_events = Collection interval for events in seconds. Leave blank to use the base interval.
interval_issues = Collection interval for issues in seconds. Leave blank to use the base interval.
interval_datastores = Collection interval for datastores in seconds. Leave blank to use the base interval.
interval_classifications = Collection interval for classifications in seconds. Leave blank to use the base interval.
interval_audit = Collection interval for audit logs in seconds. Leave blank to use the base interval.
index_events = Target index for events. Leave blank to use the default index.
index_issues = Target index for issues. Leave blank to use the default index.
index_datastores = Target index for datastores. Leave blank to use the default index.
index_classifications = Target index for classifications. Leave blank to use the default index.
index_audit = Target index for audit logs. Leave blank to use the default index.

[cyera_events://<name>]
cyera_account = Create an API clientID and Secret through your Cyera Application by following the KB article here: (https://support.cyera.io/hc/en-us/articles/20612742894231-Cyera-API).

[cyera_classifications://<name>]
cyera_account = Create an API clientID and Secret through your Cyera Application by following the KB article here: (https://support.cyera.io/hc/en-us/articles/20612742894231-Cyera-API).

[cyera_issues://<name>]
cyera_account = Create an API clientID and Secret through your Cyera Application by following the KB article here: (https://support.cyera.io/hc/en-us/articles/20612742894231-Cyera-API).

[cyera_audit://<name>]
cyera_account = Create an API clientID and Secret through your Cyera Application by following the KB article here: (https://support.cyera.io/hc/en-us/articles/20612742894231-Cyera-API).

[cyera_datastores://<name>]
cyera_account = Create an API clientID and Secret through your Cyera Application by following the KB article here: (https://support.cyera.io/hc/en-us/articles/20612742894231-Cyera-API).
retrieve_all_data_every_time = Retrieve all datastores every run instead of incremental changes. Requires daily interval (86400+ seconds).