[code42://default]
*This is how the Code42 App For Splunk is configured
hostname = <value>
* The Code42 server to connect with.

data_keys = <value>
* The data keys to pull from the API.

report_user = <value>
* Username for running reports

proxy_name = <value>
* The stanza name for a configured proxy.

credential_realm = <value>
* Stanza Name to use for credentials

use_mi_kvstore = <boolean>
* Optional and Advanced. This is set to "true" if you need to use the KVStore due to volume of Internal IDs.

historical_lookback = <value>
* Defaults to 60. Number is in days, and is controls how far back to pull the information.

ssl_verify = <boolean>
* Allows an admin to disable the SSL Certificate check. Default is "True"

use_http = <boolean>
* Use HTTP (not HTTPS) when connecting to Code42. Not supported in Splunk Cloud. Default is "False"
