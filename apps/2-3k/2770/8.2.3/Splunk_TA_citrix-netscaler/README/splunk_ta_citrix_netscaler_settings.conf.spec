##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[logging]
loglevel = <string> Log level: INFO, DEBUG, ERROR

[proxy]
proxy_enabled = <bool> Enable or disable proxy.
proxy_type = <string> Proxy type (http, socks5).
proxy_url = <string> Proxy URL.
proxy_port = <integer> Port for configuring proxy.
proxy_username = <string> Username for configuring proxy.
proxy_password = <string> Password for configuring proxy.
proxy_rdns = <bool> Remote DNS resolution.

[additional_parameters]
http_scheme = <string> http_scheme of citrix netscaler server: http or https
disable_ssl_certificate_validation = <bool> To disable or enable SSL certification validation: True or False
ca_certs_path = <string> Custom path to CA certificate
