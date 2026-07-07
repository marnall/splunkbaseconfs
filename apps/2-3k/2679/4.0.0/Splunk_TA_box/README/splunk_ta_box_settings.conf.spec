##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[proxy]
proxy_enabled = <bool> [ false | true | 0 | 1 ] Enable or disable proxy (without inverted commas).
proxy_type = <string> [ http | socks5 ] Mention the type of Proxy server (without inverted commas).
proxy_url = <string> Proxy URL (without inverted commas).
proxy_port = <integer> Port for configuring proxy (without inverted commas).
proxy_username = <string> Username for configuring proxy (without inverted commas).
proxy_password = <string> Password for configuring proxy (without inverted commas).
proxy_rdns = <bool> [ false | true | 0 | 1 ] Flag for determining whether to use Proxy for DNS Resolution (without inverted commas).

[logging]
loglevel = <string> [ DEBUG | INFO | WARN | ERROR | CRITICAL ] Select log level (all caps) (without inverted commas).

[additional_parameters]
ca_certs_path = <string> Custom path to CA certificate
