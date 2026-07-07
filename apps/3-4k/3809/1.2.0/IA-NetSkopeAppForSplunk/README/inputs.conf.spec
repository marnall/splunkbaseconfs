[netskope://default]
*This is how the Netskope Modular Input is configured

tenanturl = <value>
*This is the tenanturl to connect to

token = <value>
*The authorization token

limit = <value>
*The maximum number of events for each collection interval (max 5000)

event_type = <value>
*The type of events to collect. Options are: connection, audit, application, alert

proxy_name = <value>
* Optional. The name of the proxy server. If present and not "null", it will automatically be used.

query = <value>
* Optional. This is the Netskope query used to restrict returned results.

enable_id_tracking = <bool>
* Optional and Advanced. Only use at direction of support.

time_offset = <value>
* Optional and Advanced. Only use at direction of support

[netskope_webtransactions://default]
*This is how the Netskope App For Splunk is configured

tenanturl = <value>
*This is the tenanturl to connect to

token = <value>
*The authorization token

proxy_name = <value>
* Optional. The name of the proxy server. If present and not "null", it will automatically be used.