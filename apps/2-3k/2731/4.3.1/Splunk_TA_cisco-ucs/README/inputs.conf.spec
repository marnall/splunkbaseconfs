##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##

[cisco_ucs_task://<Cisco UCS Task name, using only letters, numbers, and underscores>]
description = <string>
* A brief description of the Task

interval = <integer>
* How often, in seconds, to poll for new data.

servers = <string>
* |(Pipe) separated Cisco UCS Server names
* For example: Splunk_TA_cisco-ucs:manager1 | Splunk_TA_cisco-ucs:manager2

templates = <string>
* |(Pipe) separated Cisco UCS Template names
* For example: Splunk_TA_cisco-ucs:UCS_Fault | Splunk_TA_cisco-ucs:UCS_Inventory | Splunk_TA_cisco-ucs:UCS_Performance
