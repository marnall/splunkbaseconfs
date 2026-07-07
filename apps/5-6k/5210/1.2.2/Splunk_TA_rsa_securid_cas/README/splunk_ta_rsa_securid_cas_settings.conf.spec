##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
@placement forwarder, search-head
[proxy]
proxy_enabled = <bool>
* Provide 0 to disable the proxy and 1 to enable it.
* Example: 1

proxy_url = <string>
* Provide URL for Proxy.
* Example: http://demo-proxy.com

proxy_port = <integer>
* Port for configuring proxy.
* Example: 5000

proxy_username = <string>
* Username for configuring proxy.
* Example: user1

proxy_password = <string>
* Password for configuring proxy.
* Example: abc123

proxy_rdns = <bool>
* Provide 1 for enable and 0 to disable Remote DNS resolution.
* Example: 0

proxy_type = <string>
* Provide a proxy type. The possible values are http, socks4, and socks5
* Example: http

@placement forwarder, search-head
[logging]
loglevel = <string>
* Provide the log level. The possible values are INFO, DEBUG, WARNING, and ERROR
* Default value of loglevel is INFO.
* Example: loglevel = DEBUG
