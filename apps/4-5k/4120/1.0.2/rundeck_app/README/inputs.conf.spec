#
# Spec file for Rundeck Modular Input for polling the Rundeck REST API
#

[rundeck://<name>]

# note : the authentication token is not stored in this file,  this gets encrypted and stored in  passwords.conf during the setup of the App.

# your Rundeck host or a comma delimited list of hosts , ie: foo.myrundeck.com (don't include 'https://' , this is hardcoded by default to satisfy Splunk certification requirements for secure network communications).You can also specify an alternative port with the host , foo.myrundeck.com:1234
https_api_host = <value>

# endpoint with tokens for dynamic properties. Current tokens supported are $api_version$ and $project$
# ie: /api/$api_version$/system/info
endpoint = <value>

# In format : prop=value,prop2=value2 , defaults to Content-Type=application/json,Accept=application/json
http_header_propertys= <value>

# In format : arg=value,arg2=value2
url_args= <value>

# in seconds or a standard cron syntax
polling_interval= <value>

# optional Proxy addresses , ie: (http://10.10.1.10:3128 or http://user:pass@10.10.1.10:3128 or https://10.10.1.10:1080 etc...)
http_proxy= <value>
https_proxy= <value>

# whether multiple requests spawned by tokenization are run in parallel or sequentially. Defaults to false (0)
sequential_mode= <value>

# an optional stagger time period between sequential requests.Defaults to 0 (seconds)
sequential_stagger_time= <value>

# request timeout in seconds , defaults to 30
request_timeout= <value>

# time to wait for reconnect in seconds after timeout or error, defaults to 10
backoff_time = <value>

# whether or not to index http error response codes , 0(false) or 1(true).Defaults to 0
index_error_response_codes= <value>

# Python classname of custom response handler declared in responsehandlers.py
response_handler= <value>

# Custom Response Handler arguments string in format key=value,key2=value2
response_handler_args= <value>

# Python Regex pattern, if present , the response will be scanned for this match pattern, and indexed if a match is present
response_filter_pattern = <value>

# Delimiter to use for any multi "key=value" field inputs , defaults to ','
delimiter= <value>

# Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/rundeck_app_modularinput.log , defaults to 'INFO'
log_level= <value>

# used internally to read/persist state of endpoints , could use KV store also , buit that is overkill for our very simple state management requirements
endpoint_state = <value>

# whether or not to backfill the entire history (true) or just start from now (false)
backfill = <value>