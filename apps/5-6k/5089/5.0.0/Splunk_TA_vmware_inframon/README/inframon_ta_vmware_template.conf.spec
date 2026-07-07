# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# This file contains possible attributes and values for configuring 
# inventory and performance fields for pools.
#
# There is a inframon_ta_vmware_template.conf in $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/default.
# To set custom configurations, place a inframon_ta_vmware_template.conf in 
# $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/local.
# 
# You must restart Splunk software to enable configurations, unless you are
# editing them through the Splunk manager.

[<pool name>]
host_ui_fields = <value>
vm_ui_fields = <value>
datastore_ui_fields = <value>
cluster_ui_fields = <value>
* This is the comma delimited list of UI names of configured additional inventory fields.

host_inv_fields = <value>
vm_inv_fields = <value>
datastore_inv_fields = <value>
cluster_inv_fields = <value>
* This is the comma delimited list of backend names of configured additional inventory fields.

host_metric_allowlist = <value>
vm_metric_allowlist = <value>
cluster_metric_allowlist = <value>
vc_metric_allowlist = <value>
* This is the value for allowlist metrics of different entities. Value is provided as a regex.

host_metric_denylist = <value>
vm_metric_denylist = <value>
cluster_metric_denylist = <value>
vc_metric_denylist = <value>
* This is the value for denylist metrics of different entities. Value is provided as a regex.