# Copyright (C) 2022 Netscout Systems Inc. All Rights Reserved.
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

INSTALLATION

Install this app on search heads.

CONFIGURATION

Edit the macro NetScoutNsaIndex to set the index to search for netscout:nsa data in the dashboards.  This is based on where you are sending the data to be indexed (typically in an inputs.conf in TA-netscout_nsa.)
