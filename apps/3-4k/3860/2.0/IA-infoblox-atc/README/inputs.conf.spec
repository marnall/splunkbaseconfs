[infoblox://default]
*This is how the Infoblox Modular Input is configured

tenanturl = <value>
*This is the tenanturl to connect to

token = <value>
*The authorization token

interval = <value>
* The polling frequency in seconds

t0 = <value>
*t0 is start time for the first poll - unix timestamp (Note that after the first poll the value is stored in the modular input checkpoint)

t1 = <value>
* t1 is end time for the first poll - unix timestamp (max delta is 24h)

proxy_name = <value>
* Optional. The name of the proxy server. If present and not "null", it will automatically be used.

use_mi_kvstore = <bool>
* Optional and Advanced. Only use at direction of support.