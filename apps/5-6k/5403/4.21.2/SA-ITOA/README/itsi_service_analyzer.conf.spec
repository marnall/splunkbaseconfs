# This file contains attributes and values for configuring the
# auto-refresh interval, or disabling auto-refresh.
# It also contains a setting that determines whether the
# First Time Run modal displays on the service analyzer.
# Lastly, this file contains an attribute that determines whether
# the cycles warning displays on the service analyzer.
#
# There is an itsi_service_analyzer.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_service_analyzer.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk to enable
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

[auto_refresh]
* A setting that you want to enable for the Service Analyzer.
* Currently, 'auto_refresh' is the only supported setting.
* NOTE: Auto-refresh is automatically disabled in real-time search mode
  for the Service Analyzer.

disabled = 0|1
* Whether this setting is disabled for the Service Analyzer.
* Required.
* If "1", the setting is disabled.
* If "0", the setting is enabled.
* Default: 1

interval = <seconds>
* The interval, in seconds, at which auto-refresh occurs for Service Analyzer.
* Required.
* Default: 120 (2 minutes)

[settings]
ftr_override = [0|1]
* Whether or not to always display the First Time Run (FTR)
  modal in the Service Analyzer.
* If "1", every time you navigate to the Service Analyzer, the First
  Time Run modal is displayed.
* If "0", the behavior defaults to showing the FTR modal only when
  services are not present.
* Default: 0 (false)

show_cycles_warning = [0|1]
* Whether to display a warning banner on the Service Analyzer
  when there are one or more cyclic dependencies in the service topology.
* After the warning is ignored in the UI, this flag is set to "0" and the
  warning is never shown again unless manually changed.
* If "1", every time a cyclic dependency exists, a warning banner
  appears on the Service Analyzer.
* If "0", the banner never appears on the Service Analyzer.
* Default: 1 (true)

search_timeout = <integer>
* The maximum amount of time, in seconds, that a search job of the service analyzer homeview page can execute. Jobs that
  exceed this time limit will not run, and generate a timeout error.
* Setting this value to 0 turns off the job timeout.
* Default: 90
