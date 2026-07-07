# This file contains possible settings you can use to upload sample
# KPI templates to the KV store.
#
# There is an itsi_kpi_template.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To set custom
# configurations, place an itsi_kpi_template.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
# You must restart ITSI to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles.

[<name>]
description = <string>
* The description of the KPI template bundle.

title = <string>
* The title of the bundle.

_owner = <string>
* The owner of the bundle.

kpis = <json>
* A JSON blob that specifies the array of KPI definitions.

source_itsi_da = <string>
* The ITSI module that is the source defining this KPI template.
