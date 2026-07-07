# This file contains attributes and values for configuring label descriptions
# and episode status in Episode Review.
#
# There is an itsi_notable_event_status.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_notable_event_status.conf in
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

[<id>]
label = <string>
* A valid label for the episode status.
* Required.

default = <boolean>
* Indicates the initial status of an episode when it is generated in
  Episode Review.
* Set this value to "1" if this label is the default label.

description = <string>
* A description of the episode label.

end = <boolean>
* Indicates the last status in the Episode Review workflow.
* Set this value to "1" if this label is the end of the
  episode management workflow.
* If a status has an end flag enabled, any episode with that status is automatically
  broken. This means that no more events will flow into that episode. This rule
  applies to status changes in Episode Review as well as through aggregation
  policy action rules.
* CAUTION: If you remove the "end" tag from the "Closed" status, you will no
  longer be able to close episodes through the Episode Review UI. It is
  recommended that you do not remove or change the location of this tag.



