[API]
api_key = <string>
# API Key to request for creating an exclusion on Checkpoint Dome9.

msg_time = <int>
# msg_time is related to setup_success or setup_error. It is the latest time when one of these messages are updated.

setup_success = <string>
# Success message if the API Key and Secret Key got stored successfully from setup page of the App.

setup_error = <string>
# Error message if the incorrect API Key and Secret Key was entered from setup page of the App.

is_proxy_enabled = <bool> 
# Flag for enabling/disabling proxy

proxy_scheme = <string> 
# Protocol used in proxy connection (http/https/socks4/socks5)

proxy_ip = <string> 
# IP address/host of the proxy server

proxy_port = <number> 
# Port used to connect to the proxy server (0-65535)

proxy_is_auth_required = <bool>
# Flag for enabling/disabling proxy authentication

proxy_username = <string> 
# Username used to connect to proxy

[connection_params]
base_url = <string>
# Base URL of Checkpoint Dome9.

timeout = <int>
# Timeout for HTTP connection in seconds.

ssl_verify = <bool>
# Whether to verify SSL client cert with HTTPS.
