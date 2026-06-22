# catonetworks_security_settings.conf.spec
#
# Configuration file for Cato Networks Security App settings

[general]
# Index where Cato Networks data is stored
# This should be the index where your Splunk HEC is sending Cato events
configured_index = <string>
* The Splunk index containing Cato Networks security events
* Required: Must be set during app setup

