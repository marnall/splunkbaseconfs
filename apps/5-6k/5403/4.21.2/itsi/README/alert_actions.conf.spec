# This file contains possible attributes and values for summarizing KPI
# searches into the ITSI summary index.
#
# There is an alert_actions.conf in $SPLUNK_HOME/etc/apps/itsi/default/.
# To set custom configurations, place an alert_actions.conf in
# $SPLUNK_HOME/etc/apps/itsi/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#  * You can also define global settings outside of any stanza, at the top
#    of the file.
#  * Each .conf file should have at most one default stanza. If there are
#    multiple default stanzas, attributes are combined. In the case of
#    multiple definitions of the same attribute, the last definition in the
#    file wins.
#  * If an attribute is defined at both the global level and in a specific
#    stanza, the value in the specific stanza takes precedence.

[indicator]
_name = <string>
* The name of the summary index where Splunk will write the events.
* Default: itsi_summary

inline = [1|0]
* Specifies whether the summary index search command will run as part
  of the scheduled search or as a follow-on action. This is useful
  when the results of the scheduled search are expected to be large.
* Default: 1 (true)

ttl = <integer> [p]
* The minimum time to live (TTL), in seconds, of the search artifacts
  if this action is triggered.
* If p follows the integer, then the integer is the number of scheduled periods.
* Default: 120 (2 minutes)

####
# Per Splunk Enterprise implementation of summary index alert action in alert_actions.conf
####

_itsi_kpi_id  = <string>
* The KPI ID.
* Required.
* There is no default.

_itsi_service_id = <string>
* The service ID.
* Required.
* There is no default.
