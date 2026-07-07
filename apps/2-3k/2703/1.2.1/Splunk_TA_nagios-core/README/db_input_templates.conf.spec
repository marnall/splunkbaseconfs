##
## SPDX-FileCopyrightText: 2020 Splunk, Inc. <sales@splunk.com>
## SPDX-License-Identifier: LicenseRef-Splunk-1-2020
##
##

# NDOUtils tables
# Central Tables
@placement forwarder, search-head
[nagios:instances]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:objects]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

# Historical Tables
@placement forwarder, search-head
[nagios:history:commenthistory]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:history:contactnotificationmethods]
description = <string>
interval = <non-negative integer>
mode = rising
index_time_mode = <string>
query = <string>
sourcetype = <string>
rising_column_index = <non-negative integer>

@placement forwarder, search-head
[nagios:history:downtimehistory]
description = <string>
interval = <non-negative integer>
mode = rising
index_time_mode = <string>
query = <string>
sourcetype = <string>
rising_column_index = <non-negative integer>

@placement forwarder, search-head
[nagios:history:eventhandlers]
description = <string>
interval = <non-negative integer>
mode = rising
index_time_mode = <string>
query = <string>
sourcetype = <string>
rising_column_index = <non-negative integer>

@placement forwarder, search-head
[nagios:history:hostchecks]
description = <string>
interval = <non-negative integer>
mode = rising
index_time_mode = <string>
query = <string>
sourcetype = <string>
rising_column_index = <non-negative integer>

@placement forwarder, search-head
[nagios:history:notifications]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:history:processevents]
description = <string>
interval = <non-negative integer>
mode = rising
index_time_mode = <string>
query = <string>
sourcetype = <string>
rising_column_index = <non-negative integer>

@placement forwarder, search-head
[nagios:history:servicechecks]
description = <string>
interval = <non-negative integer>
mode = rising
index_time_mode = <string>
query = <string>
sourcetype = <string>
rising_column_index = <non-negative integer>

@placement forwarder, search-head
[nagios:history:systemcommands]
description = <string>
interval = <non-negative integer>
mode = rising
index_time_mode = <string>
query = <string>
sourcetype = <string>
rising_column_index = <non-negative integer>

@placement forwarder, search-head
[nagios:history:timedevents]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

# Current Status Tables
@placement forwarder, search-head
[nagios:status:comments]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:status:customvariablestatus]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:status:hoststatus]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:status:programstatus]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:status:runtimevariables]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:status:scheduleddowntime]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:status:servicestatus]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:status:timedeventqueue]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>


# Configuration Tables
@placement forwarder, search-head
[nagios:config:commands]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:files]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:filevariables]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:contact_addresses]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:contact_notificationcommands]
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:contactgroup_members]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:contactgroups]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:contacts]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:customvariables]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:host_contactgroups]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:host_contacts]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:host_parenthosts]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:hostdependencies]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:hostescalation_contactgroups]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:hostescalation_contacts]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:hostescalations]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:hostgroup_members]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:hostgroups]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:hosts]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:service_contactgroups]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:service_contacts]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:servicedependencies]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:serviceescalation_contactgroups]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:serviceescalation_contacts]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:serviceescalations]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:servicegroup_members]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:servicegroups]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:services]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:timeperiod_timeranges]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>

@placement forwarder, search-head
[nagios:config:timeperiods]
description = <string>
interval = <non-negative integer>
mode = <string>
index_time_mode = <string>
query = <string>
sourcetype = <string>
