# Copyright (C) 2025 Netscout Systems Inc. All Rights Reserved.
#
# Technology Add-on for NETSCOUT OMNIS AI Streamer
#
# Enables collection and parsing of data for integration into Splunk.

CHANGELOG
6.4.0 (09/05/25) - Initial release of OMNIS AI Streamer TA

INSTALLATION
Install this TA on your indexers and heavy forwarders.


CONFIGURATION:
Getting Data In:  Copy input stanzas from default/inputs.conf into local/inputs.conf and modify as appropriate for your environment, then push the TA out to your heavy forwarders via the configuration tool of your choice.  (If using Splunk Forwarder management, copy the configured copy of the TA into etc/deployment apps, then use the Forwarder management to assign it to the appropriate server class.
