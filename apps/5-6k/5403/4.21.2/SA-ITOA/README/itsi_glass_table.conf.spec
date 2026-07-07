# This file contains possible attributes and values for uploading sample
# glass tables to the KV store.
#
# To upload glass tables to the KV store, place an
# itsi_glass_table.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
#
# You must restart Splunk software to enable configurations, unless you are
# editing them through the Splunk manager.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# WARNING: Manual editing of this file is not recommended. Contact Support before proceeding.

[<name>]
svg_content = <value>
* The SVG content settings.

latest = <value>
* The latest time in the time range.

earliest = <value>
* The earliest time in the time range.

svg_coordinates = <value>
* The SVG coordinate settings.

title = <string>
* The user-defined title of the glass table.

description = <string>
* The user defined description of the glass table.

mod_time = <value>
* Last modified time.

acl = <value>
* Access control information.

_owner = <string>
* The user account this deep dive belongs to.

source_itsi_da = <string>
* The ITSI module which is the source defining this glass table.
