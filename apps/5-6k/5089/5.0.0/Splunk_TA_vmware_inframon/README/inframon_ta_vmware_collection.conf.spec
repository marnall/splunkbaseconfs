# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# This file contains possible attributes and values for configuring 
# indexes and data collection for VMware vSphere integrations.
#
# There is a inframon_ta_vmware_collection.conf in $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/default.
# To set custom configurations, place a inframon_ta_vmware_collection.conf in 
# $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/local.
# 
# You must restart Splunk software to enable configurations, unless you are
# editing them through the Splunk manager.

[<name>]
hostinv_confirmation_expiration = <value>
vminv_confirmation_expiration = <value>
* Atomic task confirmation expirations automatically unlock jobs after the elapsed time even if a completion or failure has not been logged.

perf_index = <value>
inv_index = <value>
taskevent_index = <value>
* These are the destination indexes for the different data types

inv_maxObjUpdates = <value>
* Object count value in API response for inventory collector

task_priority = <value>
event_priority = <value>
hierarchyinv_priority = <value>
* The number to add to the priority number for jobs of a given task, negative number makes higher priority

perf_format_type = csv
* This is the value of performance format type. This is used to define format which is used to retrieve perf data from vmware. Make sure it has value either csv or normal

host_instance_allowlist = <value>
vm_instance_allowlist = <value>
cluster_instance_allowlist = <value>
* This is the value for allowlist instances of different entities. Value is provided as a regex.

host_instance_denylist = <value>
vm_instance_denylist = <value>
cluster_instance_denylist = <value>
* This is the value for Denylist instances of different entities. Value is provided as a regex.

managed_host_excludelist = <value>
* This value is the regex for excluded hosts, For this hosts data will not be collected.

managed_host_includelist = <value>
* This value is the regex for included hosts, For this hosts data will be collected.

perf_entity_denylist = <value>
* This value is the regex for excluded entities, For those entities (ie HostSystem, VirtualMachine or ClusterComputeResource), performance data will not be collected.

pool_name = <value>
* This value shows the pool name of the vcenter.

username = <value>
* This value indicates the username with which vcenter is configured.

##########INTERNAL USE ONLY##########

autoeventgen = <value>
* This is the boolean value(true or false) to enable/disable autoeventgen data.

autoeventgen_poweroff_vmcount = <value>
* This is used while generating in autoeventgen data.

deployment_type = <value>
* This is parameter used for UI configuration.

[<vcenter name>]
credential_validation = <value>
* This is the credential validation status for the vcenter.
* <value> = 1 indicates that vcenter is reachable from scheduler and provided credentials for vcenter is correct.
* <value> = 0 indicates that either vcenter is not reachable from scheduler or provided credentials for vcenter is incorrect.

last_connectivity_checked = <value>
* This value indicates the time when vcenter connectivity was last checked by scheduler.

target = <value>
* This value indicates the ip of the vcenter.

target_type = <value>
* This value is for target type field.