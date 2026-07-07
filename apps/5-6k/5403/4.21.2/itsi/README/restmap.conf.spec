# This file contains possible attribute/value pairs for creating new
# Representational State Transfer (REST) endpoints.
#
# There is a restmap.conf in $SPLUNK_HOME/etc/apps/itsi/default/.
# To set custom configurations, place an restmap.conf in
# $SPLUNK_HOME/etc/apps/itsi/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# NOTE: You must register every REST endpoint via this file to make it available.

[admin_external:itsi]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select 
  which Python version to use.
