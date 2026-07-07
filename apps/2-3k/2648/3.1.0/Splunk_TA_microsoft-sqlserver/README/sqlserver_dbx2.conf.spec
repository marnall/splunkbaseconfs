##
## SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

@placement forwarder, search-head
[<name>]
connection = <string>
index = <string>
interval = <non-negative integer>
max_rows = <non-negative integer>
mode = <string>
output_timestamp_format = <string>
query = <string>
source = <string>
sourcetype = <string>
ui_query_mode = <string>
disabled = <boolean>
tail_follow_only = <non-negative integer>
tail_rising_column_name = <string>
tail_rising_column_number = <non-negative integer>
