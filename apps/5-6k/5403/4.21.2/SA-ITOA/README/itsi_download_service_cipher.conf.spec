# This file contains possible attributes and values for the cipher key for the
# client ID and secret key that ITSI generates during the one-time cloud setup.
#
# There is an itsi_download_service_cipher.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_download_service_cipher.conf in
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

[download_cipher_key]
cipher_key = <string>
* The cipher encryption key for the client ID and secret key in the one-time cloud setup.
* The value must be the same in $SPLUNK_HOME/etc/apps/Splunk_Multicloud_Infra_Download/default/.
