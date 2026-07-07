[duo_input://default]
ikey = <string>
* Integration Key for the Duo Admin API

skey = <string>
* Secret Key for the Duo Admin API. Keep this secure, and do not store this in plaintext on your machine if possible.

api_host = <string>
* API hostname for the Duo Admin API

logging_level = <DEBUG|INFO|WARN|ERROR|FATAL>
* Severity level for duo_input log messages written to $SPLUNK_HOME/var/log/splunk/duo_splunkapp/*.log

index = <string>
* Name of Splunk index pointing to logs

interval = <integer>
* Log refresh interval, in seconds.

source = <string>
* Name of data source

sourcetype = <string>
* Source type, ie, _json

host = <string>
* Name of host

python.version = <default|python|python2|python3>
* Which python version to use. For Python scripts only.

account_log = <0|1>
* Flag to indicate whether Account logs should be extracted from the Duo Admin API.

activity_log = <0|1>
* Flag to indicate whether Activity logs should be extracted from the Duo Admin API

administrator_log = <0|1>
* Flag to indicate whether Administrator logs should be extracted from the Duo Admin API

authentication_log = <0|1>
* Flag to indicate whether Authentication logs should be extracted from the Duo Admin API

authentication_v2_log = <0|1>
* Flag to indicate whether Authentication v2 logs should be extracted from the Duo Admin API

telephony_log = <0|1>
* Flag to indicate whether Telephony logs should be extracted from the Duo Admin API

telephony_v2_log = <0|1>
* Flag to indicate whether Telephony v2 logs should be extracted from the Duo Admin API

trust_monitor_log = <0|1>
* Flag to indicate whether Trust Monitor logs should be extracted from the Duo Admin API. This should only be enabled for the Duo Premier or Duo Advantage plan.

endpoint_log = <0|1>
* Flag to indicate whether Endpoints should be extracted from the Duo Admin API. This should only be enabled for the Duo Premier or Duo Advantage plan.
