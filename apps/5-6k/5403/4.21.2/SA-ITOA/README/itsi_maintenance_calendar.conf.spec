# This file contains attributes and values for purging/archiving of completed maintenance_calendar
# in the KV store before they get deleted (if archival is disabled) or moved to the 'maintenance_calendar' collection (if archival is enabled).
# The moved entries will further gets deleted once they cross the retention period.
#
# There is an itsi_maintenance_calendar.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_maintenance_calendar.conf in
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

[retention_settings]

retentionTimeInDays = <days>
* The amount of time in days, to retain the completed maintenance_calendar entries.
* Default: 180

disabled = 0|1
* Whether this stanza is enabled or disabled.
* If "1", the stanza is disabled.
* If "0", the stanza is enabled.

archivalTimeInDays = <days>
* The amount of time in days, to archive the completed maintenance_calendar entries.
* Default: 30

disableArchival = 0|1
* Whether this archival is enabled or disabled.
* Default: 1 (archival is disabled by default)
* If "1", the archival is disabled.
* If "0", the archival is enabled.

batch_size = <integer>
* The size of each batch of KV store objects recycled to the archive collection or for deletion at a time.
* Default: 500
