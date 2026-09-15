# Copyright (C) 2026 Netscout Systems Inc. All Rights Reserved.
#
# Technology Add-on for NETSCOUT OMNIS Streamer
#
# Enables collection and parsing of data for integration into Splunk.

CHANGELOG
1.0.1 (09/05/25) - Initial release of OMNIS AI Streamer
2.1.0 (03/08/26) - Updates for 2.1.0 release of OMNSI Streamer

INSTALLATION
Install this TA on your indexers, heavy forwarders, and search heads.


CONFIGURATION
Getting Data In:  Copy input stanzas from default/inputs.conf into local/inputs.conf and modify as appropriate for your environment, then push the TA out to your heavy forwarders via the configuration tool of your choice.  (If using Splunk Forwarder management, copy the configured copy of the TA into etc/deployment apps, then use the Forwarder management to assign it to the appropriate server class.
