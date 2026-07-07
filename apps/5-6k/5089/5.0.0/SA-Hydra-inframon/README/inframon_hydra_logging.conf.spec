# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# This file contains possible settings you can use to configure log levels
# for non-modinput Hydra components.
#
# There is an inframon_hydra_logging.conf in $SPLUNK_HOME/etc/apps/SA-Hydra-inframon/default.
# To set custom configurations, place an inframon_hydra_logging.conf in
# $SPLUNK_HOME/etc/apps/SA-Hydra-inframon/local.

# You must restart Splunk to enable new configurations.

[logging]
default_log_level = <value>
* Default log level for non-modinput Hydra components when no component-specific override is set.

runtime_rest_log_level = <value>
* The level at which the Hydra runtime REST handler will log data.

models_log_level = <value>
* The level at which hydra_inframon.models will log data.

hierarchy_agent_log_level = <value>
* The level at which ta_vmware_hierarchy_agent.py will log cache distribution and fallback-auth data.
