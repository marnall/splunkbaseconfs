# This file contains possible attributes and values for configuring
# inputs for the IT Service Intelligence (ITSI) license checker, which
# checks for a valid ITSI license.
#
# There is an inputs.conf in $SPLUNK_HOME/etc/apps/SA-ITSI-Licensechecker/default/.
# To set custom configurations, place an inputs.conf in
# $SPLUNK_HOME/etc/apps/SA-ITSI-Licensechecker/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

# Use the [default] stanza to define any global settings.
#  * You can also define global settings outside of any stanza, at the top
#    of the file.
#  * Each .conf file should have at most one default stanza. If there are
#    multiple default stanzas, attributes are combined. In the case of
#    multiple definitions of the same attribute, the last definition in the
#    file wins.
#  * If an attribute is defined at both the global level and in a specific
#    stanza, the value in the specific stanza takes precedence.

[itsi_license_checker]
python.version = {default|python|python2|python3}
python.required = 3.9
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which Python version to use.
* Default: python3

[itsi_license_checker://<name>]
* A modular input that checks for a valid ITSI license.

app_name = <string>
* The app name for which license is being checked.
* Default: itsi

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO
