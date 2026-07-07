# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# This file contains possible attributes and values for configuring 
# pools and jobs for the Data Collection Scheduler (DCS).
#
# There is a inframon_ta_vmware_pool.conf in $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/default.
# To set custom configurations, place a inframon_ta_vmware_pool.conf in 
# $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/local.
# 
# You must restart Splunk software to enable configurations, unless you are
# editing them through the Splunk manager.

[<pool name>]
description = <value>
* This is the description of the pool given by user, while creating the pool.

template_name = <value>
* It is the name of the stanza present in inframon_ta_vmware_template.conf. this is a name of the additional fields template.

task = <value>
* This is the comma delimited list of tasks for which scheduler creates the jobs (hostvmperf, clusterperf, etc).

atomic_tasks = <value>
* This is the comma delimited list of tasks, Tasks that should be considered atomic and not generate jobs until the previous run completes(hostinv, vminv).

<task>_interval = <value>
* This is the interval value of <task>. Scheduler creates the job for <task> at a given interval value.

<task>_expiration = <value>
* This is the expiration value of <task>. The queued job for <task> in DCN will be expired after given expiration value.