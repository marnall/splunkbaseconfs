[sources_input://<name>]
interval = <integer> Time Interval for invocation of Data-collection.  
index = <string> Index in which events get ingested in splunk.
google_scc_account = <string> GoogleSCC Account from where data will be collected.

[findings_input://<name>]
interval = <integer> Time Interval for invocation of Data-collection.
index = <string> Index in which events get ingested in splunk.
google_scc_account = <string> GoogleSCC Account from where data will be collected.
findings_subscription_id = <string> Subscription ID for which data will be collected.
maximum_fetching = <integer> Maximum number of events that is to be fetched for that Input.

[assets_input://<name>]
interval = <integer> Time Interval for invocation of Data-collection.
index = <string> Index in which events get ingested in splunk.
google_scc_account = <string> GoogleSCC Account from where data will be collected.
assets_subscription_id = <string> Subscription ID for which data will be collected.
maximum_fetching = <integer> Maximum number of events that is to be fetched for that Input.

[auditlog_input://<name>]
interval = <integer> Time Interval for invocation of Data-collection.
index = <string> Index in which events get ingested in splunk.
google_scc_account = <string> GoogleSCC Account from where data will be collected.
audit_logs_subscription_id = <string> Subscription ID for which data will be collected.
maximum_fetching = <integer> Maximum number of events that is to be fetched for that Input.

[sources_input]
python.version = python3