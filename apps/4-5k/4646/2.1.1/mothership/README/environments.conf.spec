[mothership]
mgmt_scheme_host_port = <scheme://IP:port>
* Location of the remote splunkd server.
* Include the http[s]://
splunk_web_uri = <scheme://IP:port>
* Location of the remote splunkweb.
username = <username string>
* Username to login into the remote instance.
tags = <comma seperated alphanumeric strings (underscores and dashes supported)>
* User and/or system provided tags associated with the remote instance
password_link_alternate = <link alternate>
* Splunk link alternate of the password associated with this environment
hec_url = <schem://IP:port>
hec_token = token