[heat_proxy]
proxy_enabled = true|false

proxy_host = <url>
* URL for a proxy server which includes protocol and port (http://my-proxy.mycompany.com:3128)

proxy_auth_enabled = true|false
* Enable authentating with the proxy.  If the proxy is enabled and this property is configured, the proxy_username property and proxy_password secret must also be configured.

proxy_username = <string>
* The username for authentating with the proxy.  If the proxy is enabled and this property is configured, the proxy_password secret must also be configured.  If either the proxy_username or proxy_passowrd are missing, the proxy will be used without authentication.


