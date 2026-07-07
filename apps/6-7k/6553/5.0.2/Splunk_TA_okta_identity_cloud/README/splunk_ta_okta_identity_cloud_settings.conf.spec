##
## SPDX-FileCopyrightText: 2025 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[additional_parameters]
user_limit = Number of Items to collect per call for the specific data type.
group_limit = Number of Items to collect per call for the specific data type.
app_limit = Number of Items to collect per call for the specific data type.
log_limit = Number of Items to collect per call for the specific data type.
log_history = Number of days in the past to collect logs when a new input is created for an account. (Deprecated)
rate_limit_pct = Used to adjust rate limit avoidance target. Tells add-on to use ONLY this percentage of API calls.
dynamic_rate_enabled = Dynamically adjust the request rate to avoid exceeding API throttling warning limits

[proxy]
proxy_enabled = Provide 0 to disable the proxy and 1 to enable it.
proxy_url = Provide URL for Proxy.
proxy_port = Port for configuring proxy.
proxy_username = Username for configuring proxy.
proxy_password = Password for configuring proxy.

[logging]
loglevel = Provide the log level. The possible values are DEBUG, INFO, WARNING, ERROR, and CRITICAL
