# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# This file contains possible settings you can use to configure how
# the Data Collection Scheduler (DCS) allocates jobs, including how worker
# processes collect data.
#
# There is a inframon_hydra_node.conf in $SPLUNK_HOME/etc/apps/SA-Hydra-inframon/default. To set custom
# configurations, place an inframon_hydra_node.conf in $SPLUNK_HOME/etc/apps/SA-Hydra-inframon/local.

# You must restart Splunk to enable new configurations.

[<name>]
capabilities = <value>
* This is the comma-delimited list of actions that the worker can perform (hostvmperf, clusterperf, etc.)

log_level = <value>
* The level at which the worker will log data.
