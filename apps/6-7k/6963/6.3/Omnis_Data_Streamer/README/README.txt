# Copyright (C) 2023 Netscout Systems Inc. All Rights Reserved.
#
# App for NetScout Omnis Data Streamer
#
# Provides dashboard visualization and investigation drill downs for CI log data in Splunk.
#
# Depends On: OmnisCyberInvestigator.

CHANGELOG
6.3.4 (24/08/22) - Initial release of Omnis Data Streamer App
6.3.5 (20/06/23) - Updates to support Omnis Data Streamer release 6.3.5


INSTALLATION

Install this app on search heads.

CONFIGURATION

Edit the macro NetScoutNsaIndex to set the index to search for netscout:nsa data in the dashboards.  This is based on where you are sending the data to be indexed (typically in an inputs.conf in TA-netscout_nsa.)
