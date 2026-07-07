
[splunk_ta_o365_management_activity://<name>]
tenant_name = Which Office 365 tenant will be used
content_type = What kind of activity will be ingested. [Audit.AzureActiveDirectory | Audit.Exchange | Audit.SharePoint | Audit.General | DLP.All]
number_of_threads = The number of threads used to download content blob in parallel
token_refresh_window = The number of seconds before the token's expiration time when the token should be refreshed. For example if the token is expiring at 01:00 PM and user has entered the 600 as a value of parameter token_refresh_window then the token will be refreshed at 12:50 PM. The range for the parameter is from 400 seconds to 3600 seconds.
request_timeout = The number of seconds to wait before timeout while getting response from the subscription api. The range for the parameter is from 10 seconds to 600 seconds.
is_migrated = [0|1] Whether checkpoint has been migrated or not.
start_date_time = Date to start collecting management activity events. If no date/time is given, the input will start 4 hours in the past.

[splunk_ta_o365_management_activity]
python.version = python3
python.required = 3.9, 3.13
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[splunk_ta_o365_service_status://<name>]
tenant_name = Which Office 365 tenant will be used
content_type = What kind of status will be ingested. [Current | Historical].

[splunk_ta_o365_service_status]
python.version = python3
python.required = 3.9, 3.13
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[splunk_ta_o365_service_message://<name>]
tenant_name = Which Office 365 tenant will be used

[splunk_ta_o365_service_message]
python.version = python3
python.required = 3.9, 3.13
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[splunk_ta_o365_graph_api://<name>]
tenant_name = Which Office 365 tenant will be used
content_type = Which Graph API Report will be called
request_timeout = <integer> the request timeout parameter that specifies the maximum amount of time to wait for a response from the API when reading data. The range for the parameter is from 10 seconds to 600 seconds.
start_date = Start Date value from where the data collection will start.
delay_throttle = Microsoft generally reports events with a delay of at least 2 days. Applicable for reporting inputs.
query_window_size = Specify how many minutes worth of data to query
delay_throttle_min = Specify delay throttle based on the latency observed in Audit Logs. Applicable for Audit Logs input.

[splunk_ta_o365_graph_api]
python.version = python3
python.required = 3.9, 3.13

[splunk_ta_o365_cloud_app_security://<name>]
tenant_name = Which Office 365 tenant will be used
content_type = Which Cloud Application Security API will be called

[splunk_ta_o365_cloud_app_security]
python.version = python3
python.required = 3.9, 3.13

[splunk_ta_o365_message_trace://<name>]
tenant_name = Which Office 365 tenant will be used
start_date_time = UTC date/time to start collecting message traces in YYYY-MM-DDTHH:MM:SS format. If no date/time is given, the input will start 5 days in the past
end_date_time = Only specify an end date if using the Index Once option. Use the same UTC format as start_date_time.
query_window_size = Specify how many minute's worth of data to query each interval
input_mode = Index Once|Continuous Monitor.Selecting Index Once ignores Query window size and Delay throttle. Additionally, Start date and End date are required for Index Once
delay_throttle = Microsoft may delay trace events up to 24 hours

[splunk_ta_o365_message_trace]
python.version = python3
python.required = 3.9, 3.13

[splunk_ta_o365_microsoft_entra_id_metadata://<name>]
tenant_name = Which Office 365 tenant will be used
entra_id_type = Metadata to be collected
query_parameters = Query Filters to be used while retrieving the events
api_version = Graph API endpoint version.

[splunk_ta_o365_microsoft_entra_id_metadata]
python.version = python3
python.required = 3.9, 3.13

[script://$SPLUNK_HOME/etc/apps/splunk_ta_o365/bin/conf_migration.py]
python.version = python3
python.required = 3.9, 3.13
