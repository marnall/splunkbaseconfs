##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[was_global_settings]
index = <String> Select index for the input (single Select)
was_install_dir = <String> IBM WebSphere application server installation directory
log_level = <String> Log Level having default value INFO

[was_hpel_settings]
excluded_profiles = <String> Profiles to exclude from HPEL data collection separated by commas
start_date = <Date> HPEL logs start date (UTC) in "MM/dd/yy H:m:s:S" format
level = <String> Log level to collect from the HPEL log data. This argument overrides any values in min_level and max_level
min_level = <String> Minimum log level to collect from the HPEL log data
max_level = <String> Maximum log level to collect from the HPEL log data
duration = <Integer> Collection interval in seconds for the HPEL input
excluded_servers = <String> Servers to exclude from HPEL data collection separated by commas specified in the format <Profile>:<ServerDir>. E.g., ProfileA:ServerA1,ProfileB:ServerB3
