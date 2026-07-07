[expanse://<name>]
token = Token to authenticate API calls [Being deprecated in a future release]
server_url = Base URL of the API server
start_date_utc = Date format: YYYY-MM-DD
enable_alert_updates = If you are running Splunk in a distributed search environment then this should be enabled on the Heavy Forwarder only. Please reference documentation for more details.
index = Setting the index is required if you are importing Issue Updates into your Splunk Instance.
enable_assets = If you are running Splunk in a distributed search environment then this should be enabled on the Search Head only. Please reference documentation for more details.
enable_services = If you are running Splunk in a distributed search environment then this should be enabled on the Search Head only. Please reference documentation for more details.
utc_offset = UTC offset (in hours) of your system after considering any daylight changes. Default is 0.0, Min offset is -12.0, Max offset is 14.0. Ex: A Splunk server with timezone UTC-2:30 would use -2.5.
global_account =
use_advanced_auth =
api_key_id =
alert_severity = high
