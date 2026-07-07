##
## SPDX-FileCopyrightText: 2026 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

@placement forwarder, search-head
[logging]
loglevel = <String> Log Level having default value INFO

@placement forwarder, search-head
[general]
display_destination_app = <String> This parameter is used to show/hide destination app selection box for inputs, server and template configuration

@placement forwarder, search-head
[java_sys_prop]
ks_password = <String> Password to access the KeyStore, that is, jmx_client.ks file in Splunk_TA_jmx/bin/ directory.
ts_password = <String> Password to access the TrustStore, that is, jmx_client.ks file in Splunk_TA_jmx/bin/ directory.
cert_length = <String> Maximum number of certificates that are allowed in certificate store.
