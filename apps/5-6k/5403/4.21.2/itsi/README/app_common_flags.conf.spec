# This file contains attributes and values for disabling (feature flagging)
# certain ITSI features.
#
# There is an app_common_flags.conf in $SPLUNK_HOME/etc/apps/itsi/default.
# To set custom configurations, place an app_common_flags.conf in
# $SPLUNK_HOME/etc/apps/itsi/local/. You must restart Splunk software to
# enable configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# CAUTION: This is an internal configuration file used to turn off certain ITSI
# features that are incomplete. Do NOT edit or remove this file.

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

[<app_common_flag>]
* Each stanza represents a feature within Splunk IT Service Intelligence (ITSI).
* If the feature is disabled, it is currently incomplete and should NOT be enabled.

feature = <string>
* The name of the feature.

description = <string>
* A description of what the feature does.

disabled = <boolean>
* Whether the feature is enabled or disabled.
* If "1", the feature is disabled.
* If "0", the feature is enabled.
