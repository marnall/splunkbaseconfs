##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[proxy]
proxy_enabled =
proxy_type =
proxy_url =
proxy_port =
proxy_username =
proxy_password =
proxy_rdns =

[logging]
loglevel =

[general]
csv_limit = <integer> Maximum bytes allowed while reading the CSV files for the EventLog input. Default: 10485760. Maximum: 2147483647.
ca_certs_path = <string> Custom path to CA certificate.
