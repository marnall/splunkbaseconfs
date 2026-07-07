# This file contains the list of data integrations that will be presented
# as chiclets on the data integrations page.

# To set custom configurations, place a itsi_data_integrations.conf.spec in
# $SPLUNK_HOME/etc/apps/itsi/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

[<data_integration_name>]
title = <string>
* The title for the data integration chiclet.
* Required.

description = <string>
* The description for the data integration chiclet.
* Required.

icon_path = <string>
* The icon for the data integration chiclet.
* Required.

supported_ingest_methods = <comma-separated list>
* A comma-separated list of supported ingest methods for this data integration.
* Valid values include "webhook" and "splunk-add-on".
* Optional.
