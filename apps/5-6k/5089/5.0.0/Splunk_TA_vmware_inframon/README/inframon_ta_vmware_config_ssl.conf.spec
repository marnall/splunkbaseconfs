# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# This file contains possible attributes and values for configuring 
# SSL certificate validation.
#
# There is a inframon_ta_vmware_config_ssl.conf in $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/default.
# To set custom configurations, place a inframon_ta_vmware_config_ssl.conf in 
# $SPLUNK_HOME/etc/apps/Splunk_TA_vmware_inframon/local.
# 
# You must restart Splunk software to enable configurations, unless you are
# editing them through the Splunk manager.

[general]
validate_ssl_certificate = <bool>
* Whether or not to enable SSL certificate validation.
* Set true to enable SSL certificate validation.
* Defaults to false.