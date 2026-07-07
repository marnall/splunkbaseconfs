[akamai_guardicore://<name>]
guardicore_api_account = 
guardicore_management_server = IP or FQDN of the  Guardicore management server
port = 
start_date = Specify the start date for data retrieval in the YYYY/MM/DD format. By default, data is imported from one year ago for unaggregated connections and three days ago for daily connections.
end_date = Specify an end date for additional data retrieval between start and end date in YYYY/MM/DD format. (Applies only  to daily connections)
request_timeout = Specify time before request timeout (seconds).
log_export_delay = Indicates the time in minutes to delay the latest logs
event_limit = Specify maximum number of events per batch.
connection_type = Filter by the selected connection types. If 'Any' is selected, all types will be collected.
policy_verdict = Filter by the selected verdicts. If 'Any' is selected, all verdicts will be collected.
filter_by_labels = Specify a comma separated list of "Key1:value1,Key2:value2,.."
use_daily_connections = Check to use the daily connections endpoint. The most recent data available is from the previous day.
maximum_task_retries_per_date = The maximum number of times to attempt download connections on the same date before skipping it (Applies only to daily connections).
use_proxy = Tick the box to use your defined proxy.