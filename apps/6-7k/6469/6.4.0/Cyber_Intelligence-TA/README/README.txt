# Copyright (C) 2024 Netscout Systems Inc. All Rights Reserved.
#
# Technology Add-on for NetScout Omnis Cyber Intelligence
#
# Enables collection and parsing of CI log data for integration into Splunk.
# See also: netscout_nsa app for visualizations.

CHANGELOG
0.1.0 - Initial Release
0.1.1 - Added sample inputs at default/inputs.conf, added copyright/do not edit headers to all default config files, updated installation instructions.  Removed extraneous sample files.
0.1.2 (2/23/19) - Added a field alias for NetScoutNsaUrl to accommodate variations in source data.
0.1.8 (9/27/19) - changed source field for alias NetScoutNsaUrl. Added "Cyber Threats" view to dashboard
0.1.9 (31/10/19) - changed views to not use the cat field, as it is no longer supported, catogories now being Cyber Threats, Threat Indicators or Security Risks.
0.1.10 (12/11/19) - added user defined metrics screens to "Security Risks" view
6.2.2 (03/12/19) - changed version to match ATA version
6.3.0 (26/02/20) - updated to support 6.3.0, fixed issue with drilldowns from Splunk 8.0.x
6.3.0 (14/05/20) - Name and branding changes to sGenius Cyber Investigator
6.3.2 (18/03/21) - Name and branding changes to Omnis Cyber Investigator
6.3.3 (27/08/21) - Updates to support new format of events in release 6.3.3
6.3.4 (06/06/23) - Updates to support release 6.3.4, name change to Omnis Cyber Intelligence
6.3.5 (05/05/23) - Updates and new views for release 6.3.5, events format changes
6.4.0 (18/03/24) - Updates to support new event type File Detection

INSTALLATION
Install this TA on your indexers, heavy forwarders, and search heads.


CONFIGURATION

Getting Data In:  Copy input stanzas from default/inputs.conf into local/inputs.conf and modify as appropriate for your environment, then push the TA out to your heavy forwarders via the configuration tool of your choice.  (If using Splunk Forwarder management, copy the configured copy of the TA into etc/deployment apps, then use the Forwarder management to assign it to the appropriate server class.

