# This file contains possible attribute/value pairs for blacklisting 
# notable event fields from the Common Fields section of episodes.
#
# There is a notable_event_commonality.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place a notable_event_commonality.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local. You must restart Splunk software to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

[common_event_fields]
black_list_fields = <comma-separated list>
* A list of field names in a notable event that will not appear in the 
  Common Fields section of an episode.
* By default, ITSI blacklists fields that are not core to the raw event
  itself, or ones that are mainly used internally. 
* Add fields here that you don't necessarily care about, but that you know
  will probably appear in most of your events.
