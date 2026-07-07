[proxy]
proxy_enabled = Boolean to decide if proxy is enabled or not
proxy_type = Proxy type
proxy_url = Proxy URL
proxy_port = Proxy port
proxy_username = Proxy username
proxy_password = Proxy password
proxy_rdns = Boolean for remote DNS resolution

[logging]
loglevel = Log level

[additional_parameters]
authorization_type = The Authorization type - Basic or OAuth
username = The username of the ThreatQ server
password = The password of the ThreatQ server
server_url = The URL of the ThreatQ server
client_id = The client ID of the ThreatQ server
client_secret = The Client Secret of the ThreatQ server

[import_timeout]
timeout_value = reading timeout value which will be use in ThreatQ API calls

[splunk_rest_host]
splunk_username = The username of the Splunk server
splunk_password = The password of the Splunk server
splunk_rest_host_url = The URL of the Splunk server
splunk_rest_port = The Management port of teh Splunk server
splunk_verify_cert = Boolean to decide if SSL certificate validation should be done or not