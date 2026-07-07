[proxy]
enabled = <boolean>
* Enable proxy utilization for commands
* Default: 0

proxy_url = <string>
* Proxy URL to connect to
* Must be HTTPS 
 
user = <string>
* value is used as the username to login to the proxy

[quotas]
quota_limit = <integer>
* The quota-value must be an integer indicating the number of results to limit the queries to.
* This is used to manage how many API queries the commands use at a time. 
* Example: 
 * 35000
* Default: 1000

[logging]
level = DEBUG | INFO | WARN | ERROR
* Minimum log level to set for the script(s)
* Default: INFO

