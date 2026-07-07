[sandfly_ssh_keys://<name>]
sandfly_server_url = Enter the Sandfly Server URL, including the API version (e.g., https://SERVER.sandflysecurity.com/v4).
global_account = 
enable_ssl_verification = Enable SSL certificate verification when connecting to the Sandfly Server URL. Leave unchecked when using self signed certificates (generally not recommended). Verification enforced on Splunk Cloud.

[sandfly_hosts://<name>]
sandfly_server_url = Enter the Sandfly Server URL, including the API version (e.g., https://SERVER.sandflysecurity.com/v4
global_account = 
enable_ssl_verification = Enable SSL certificate verification when connecting to the Sandfly Server URL. Leave unchecked when using self signed certificates (generally not recommended). Verification enforced on Splunk Cloud.
create_csv_lookup_files = Enable to automatically create sandfly_hosts.csv and sandfly_assets.csv in the TA lookups directory. May not work properly on Search Head cluster environments

[sandfly_sandflies://<name>]
sandfly_server_url = Enter the Sandfly Server URL, including the API version (e.g., https://SERVER.sandflysecurity.com/v4).
global_account = 
enable_ssl_verification = Enable SSL certificate verification when connecting to the Sandfly Server URL. Leave unchecked when using self signed certificates (generally not recommended). Verification enforced on Splunk Cloud.

[sandfly_audit_logs://<name>]
sandfly_server_url = Enter the Sandfly Server URL including the API version (e.g., https://SERVER.sandflysecurity.com/v4)
global_account = 
start_time = The date (UTC in "YYYY-MM-DDThh:mm:ssZ" format) from when to start collecting data.  Default is last 24 hours if date is not specified.
enable_ssl_verification = Enable SSL certificate verification when connecting to the Sandfly Server URL. Leave unchecked when using self signed certificates (generally not recommended). Verification enforced on Splunk Cloud.

[sandfly_error_logs://<name>]
sandfly_server_url = Enter the Sandfly Server URL including the API version (e.g., https://SERVER.sandflysecurity.com/v4)
global_account = 
start_time = The date (UTC in "YYYY-MM-DDThh:mm:ssZ" format) from when to start collecting data.  Default is last 24 hours if date is not specified.
enable_ssl_verification = Enable SSL certificate verification when connecting to the Sandfly Server URL. Leave unchecked when using self signed certificates (generally not recommended). Verification enforced on Splunk Cloud.

[sandfly_alarms://<name>]
sandfly_server_url = Enter the Sandfly Server URL, including the API version (e.g., https://SERVER.sandflysecurity.com/v4).
global_account = 
sandfly_results = 
sandfly_results_summary_data = Enable to ingest summary data only, leave disabled to ingest full result data.
duplicate_alerts = Enable to ingest duplicate Alerts. Duplicate Alerts are ingested when the Last Seen time for an existing Alert is updated.
duplicate_alerts_summary_data = Enable to ingest summary data only, leave disabled to ingest full result data.
start_time = The date (UTC in "YYYY-MM-DDThh:mm:ssZ" format) from when to start collecting data.  Default is last 24 hours if date is not specified.
enable_ssl_verification = Enable SSL certificate verification when connecting to the Sandfly Server URL. Leave unchecked when using self signed certificates (generally not recommended). Verification enforced on Splunk Cloud.
test_mode = Enable test mode to stop data ingestion after 999 events.  Not recommended for production environments.