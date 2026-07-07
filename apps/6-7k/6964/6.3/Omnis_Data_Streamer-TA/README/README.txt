# Copyright (C) 2023 Netscout Systems Inc. All Rights Reserved.
#
# Technology Add-on for NetScout Omnis Data Streamer
#
# Enables collection and parsing of CI log data for integration into Splunk.
# See also: netscout_nsa app for visualizations.

CHANGELOG
6.3.4 (24/08/22) - Initial release of ODS
6.3.5 (20/06/23) - Updates to support ODS release 6.3.5

INSTALLATION
Install this TA on your indexers, heavy forwarders, and search heads.


CONFIGURATION

Getting Data In:  Copy input stanzas from default/inputs.conf into local/inputs.conf and modify as appropriate for your environment, then push the TA out to your heavy forwarders via the configuration tool of your choice.  (If using Splunk Forwarder management, copy the configured copy of the TA into etc/deployment apps, then use the Forwarder management to assign it to the appropriate server class.

