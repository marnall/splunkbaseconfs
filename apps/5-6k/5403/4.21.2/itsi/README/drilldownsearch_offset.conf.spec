# This file contains attributes and values for configuring time range picker
# presets for correlation search drilldown offsets. 
#
# There is a drilldownsearch_offset.conf in $SPLUNK_HOME/etc/apps/itsi/default/.
# To set custom configurations, place a drilldownsearch_offset.conf in
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

[<offset-period-number>]
timeInSecs = <integer>
* The offset time, in seconds.
* Required.

description = <string>
* The description that is shown in the UI for the earliest and latest offset
  dropdown. The earliest offset prepends "Last" to the description and the 
  latest offset prepends "Next" to the description.
* Required if the 'earliest_description' and 'latest_description' settings
  are not defined below.

earliest_description = <string>
* A description for the earliest offset dropdown.
* Optional.

latest_description = <string>
* A description for the latest offset dropdown.
* Optional.
