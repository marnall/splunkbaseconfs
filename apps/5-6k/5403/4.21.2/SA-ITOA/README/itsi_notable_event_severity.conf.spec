# This file contains attributes and values for defining the colors associated with
# different episode and event severity levels in Episode Review.
#
# There is an itsi_notable_event_severity.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_notable_event_severity.conf in
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

[<name>]
color = <string>
* A valid color code to represent an episode or event with this severity.
* The color determines the episode's color in Episode Review.
* Required.

lightcolor = <string>
* A valid color code to represent an episode's severity in prominent mode. 
* Required.

label = <string>
* The severity label displayed in Episode Review.
* For example, Info, Medium, Critical.

default = 0|1
* Set this flag to indicate the default severity of an event or episode.
