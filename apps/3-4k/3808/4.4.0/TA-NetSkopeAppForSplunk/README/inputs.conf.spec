[netskope_events_v2://<name>]
global_account = Select the account for which you want to collect data.
interval = <integer>
start_datetime = Only Events after this DateTime will be fetched. UTC Format: YYYY-MM-DDTHH:MM:SSZ (E.g. 2020-02-22T05:40:58Z)
event_type = Types of events to collect. Default will be all types of events if no option is selected.
timeout = <integer> sleep time in seconds. collection will wait till timeout if it not gets successful response.
end_datetime = Only Events till this DateTime will be fetched. UTC Format: YYYY-MM-DDTHH:MM:SSZ (E.g. 2020-02-22T05:40:58Z)
retry_count = <integer> Number of times the input should retry during data collection.
fields_include_exclude = <string> Option to modify input fields.
fields_include = <string> Fields to include.
fields_exclude = <string> Fields to exclude.
is_first_call_page = <string> Flag to determine is this a first call for this input or not
is_first_call_application = <string> Flag to determine is this a first call for this input or not
is_first_call_audit = <string> Flag to determine is this a first call for this input or not
is_first_call_infrastructure = <string> Flag to determine is this a first call for this input or not
is_first_call_network = <string> Flag to determine is this a first call for this input or not
is_first_call_incident = <string> Flag to determine is this a first call for this input or not
is_first_call_endpoint = <string> Flag to determine is this a first call for this input or not

[netskope_events_v2_csv://<name>]
global_account = Select the account for which you want to collect data.
interval = <integer>
event_type = Types of events to collect. Default will be all types of events if no option is selected.
timeout = <integer> sleep time in seconds. collection will wait till timeout if it not gets successful response.
retry_count = <integer> Number of times the input should retry during data collection.
netskope_connection_index_name = <string> Netskope Connection CSV Index
netskope_application_index_name = <string> Netskope Application CSV Index
netskope_network_index_name = <string> Netskope Connection CSV Index

[netskope_events_v2]
thread_count = Number of threads to use for data collection

[netskope_alerts_v2://<name>]
global_account = Select the account for which you want to collect data.
interval = <integer>
start_datetime = Only Events after this DateTime will be fetched. UTC Format: YYYY-MM-DDTHH:MM:SSZ (E.g. 2020-02-22T05:40:58Z)
timeout = <integer> sleep time in seconds. collection will wait till timeout if it not gets successful response.
alert_type = <string> Types of alert to collect (separted by "~").
end_datetime = Only Events till this DateTime will be fetched. UTC Format: YYYY-MM-DDTHH:MM:SSZ (E.g. 2020-02-22T05:40:58Z)
retry_count = <integer> Number of times the input should retry during data collection.
fields_include_exclude = <string> Option to modify input fields.
fields_include = <string> Fields to include.
fields_exclude = <string> Fields to exclude.
is_first_call_all = <string> Flag to determine is this a first call for this input or not
is_first_call_compromisedcredential = <string> Flag to determine is this a first call for this input or not
is_first_call_ctep = <string> Flag to determine is this a first call for this input or not
is_first_call_dlp = <string> Flag to determine is this a first call for this input or not
is_first_call_malsite = <string> Flag to determine is this a first call for this input or not
is_first_call_malware = <string> Flag to determine is this a first call for this input or not
is_first_call_policy = <string> Flag to determine is this a first call for this input or not
is_first_call_quarantine = <string> Flag to determine is this a first call for this input or not
is_first_call_remediation = <string> Flag to determine is this a first call for this input or not
is_first_call_securityassessment = <string> Flag to determine is this a first call for this input or not
is_first_call_uba = <string> Flag to determine is this a first call for this input or not
is_first_call_watchlist = <string> Flag to determine is this a first call for this input or not
is_first_call_device = <string> Flag to determine is this a first call for this input or not
is_first_call_content = <string> Flag to determine is this a first call for this input or not


[netskope_alerts_v2_csv://<name>]
global_account = Select the account for which you want to collect data.
interval = <integer>
timeout = <integer> sleep time in seconds. collection will wait till timeout if it not gets successful response.
alert_type = <string> Types of alert to collect (separted by "~").
retry_count = <integer> Number of times the input should retry during data collection.
netskope_alert_csv_index_name = <string> Netskope Alerts CSV Index

[netskope_clients://<name>]
global_account = <string> Netskope Account from where data will be collected.
interval = <integer | cron> Time interval of input in seconds or cron schedule. E.g. for every day at 1 am cron schedule will be "0 1 * * *"
start_datetime = <string> Only Events after this DateTime will be fetched. \n UTC Format: YYYY-MM-DDTHH:MM:SSZ (E.g. 2020-02-22T05:40:58Z)
offset = <integer> In Seconds. The maximum time an event takes from generation to insertion into Netskope DB.
limit = <integer> Maximum events to fetch in one request Allowed Range [1-5000]
query = <string> This is the Netskope Query that will restrict the returned results. E.g. "user eq Tom and email like gmail.com"
api_request_timeout = <integer> API Request timeout period in seconds. This will be used in API call as wait time period for any response.
sourcetype = <string> Source type description.
failed_window_retries = <integer> How many time to retry before dropping the timerange having errors

[netskope_clients]
python.version = Select which Python version to use. {default|python|python2|python3}

[netskope_webtransactions://<name>]

[netskope_webtransactions]
global_account = <string> Netskope Account from where data will be collected.
interval = <integer | cron> Time interval of input in seconds or cron schedule. E.g. for every day at 1 am cron schedule will be "0 1 * * *"
api_request_timeout = <integer> API Request timeout period in seconds. This will be used in API call as wait time period for any response.
sourcetype =  <string> Source type description.
python.version = Select which Python version to use. {default|python|python2|python3}

[netskope_webtransactions_v2://<name>]
global_account = <string> Netskope Account from where data will be collected.
sourcetype =  <string> Source type description.
idle_connection_timeout = <integer> Idle Connection Timeout.
parallel_ingestion_pipeline = <integer> Number of parallel pipelines.
max_webtxn_files = If Splunk can't keep up with webtxn data ingestion and files exceed Max Webtxn Files, collection pauses until space is available. On setting value as 0, these restrictions won't be applied.
enable_custom_spool_path = Custom path to store the Webtransaction log files before it gets ingested into the Splunk.
custom_spool_path = <integer> Enter the the location to store the Webtransaction log files. E.g.: opt/splunk/var/target_dir
fields_include_exclude = <string> Option to modify input fields.
fields_include = <string> Fields to include.
fields_exclude = <string> Fields to exclude.
subscription_key = <string> Subscription key obtained using token
subscription_path = <string> Subscription path obtained using token

[netskope_webtransactions_v2]
python.version = Select which Python version to use. {default|python|python2|python3}
subscription = <string> Copy the Subscription Endpoint from Netskope > Settings > Tools > Event Streaming page.

[netskope_clients_iterator://<name>]
global_account = Select the account for which you want to collect data.
interval = <integer>
timeout = <integer> sleep time in seconds. collection will wait till timeout if it not gets successful response.
retry_count = <integer> Number of times the input should retry during data collection.
netskope_iterator_name = <string> Name of Netskope iterator collector.

[netskope_events_multi_iterator://<name>]
global_account = <string> Select the account for which you want to collect data.
interval = <integer> Time interval of input in seconds. Set it to 0 for one-time collection.
event_type = <string> Type of event to collect. Valid values: connection, application, network.
timeout = <integer> Sleep time in seconds. Collection will wait till timeout if it not gets successful response.
retry_count = <integer> Number of times the input should retry during data collection.
netskope_iterator_name = <string> Name of Netskope iterator collector.
