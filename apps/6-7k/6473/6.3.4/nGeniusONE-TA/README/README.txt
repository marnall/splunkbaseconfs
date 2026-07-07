#Copyright (C) 2022 Netscout Systems Inc. All Rights Reserved.
#
# App for NetScout nGeniusONE Service Assurance
#
# Provides dashboard visualization and investigation drill downs for nGeniusONE syslog data in Splunk.
#
# Depends On: nGeniusONE-TA

CHANGELOG
0.1.0 - Initial Release
6.3.0 - Updates to labeling and branding
        Context sensitive search parameters
        Supports notifictions from 6.3.0 patch nG1
6.3.3 - Updates to support release 6.3.3
6.3.4 - Updates to support release 6.3.4

Install this TA on your indexers, heavy forwarders, and search heads.


CONFIGURATION

Getting Data In:  Copy input stanzas from default/inputs.conf into local/inputs.conf and modify as appropriate for your environment, then push the TA out to your heavy forwarders via the configuration tool of your choice.  (If using Splunk Forwarder management, copy the configured copy of the TA into etc/deployment apps, then use the Forwarder management to assign it to the appropriate server class.

Eventgen:  This TA includes sample log data and an eventgen.conf for use with SA-eventgen.  You can use this to generate sample data for demonstration/testing purposes.  Use SA-eventgen v6.3.0, NOT 6.3.1 or 6.3.2.  See eventgen.conf for notes on why.  After installing eventgen, to start generating data, enable the SA-Eventgen modinput by going to Settings > Data Inputs > SA-Eventgen and by clicking “enable” on the default modular input stanza.  Generated data is currently being sent to the main index.
