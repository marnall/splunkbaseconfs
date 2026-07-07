# This file describes the snowtbl.conf file that is included
# with the SNOW Table for Splunk app.
# 

# ---- Main Stanza ----
# Contains global variables for the app.

[main]

snow_user= <username>
* ServiceNow user

snow_url = <url>
* ServiceNow URL, for example, https://myaccount.service-now.com

snow_timeout = <integer>
* ServiceNow timeout

proxy_enabled = <no | yes>
* Proxy enable

proxy_type = <http | https>
* Proxy Type

proxy_host = <host> 
* Proxy IP address

proxy_port = <integer>
* Proxy port
