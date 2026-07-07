# Copyright (C) 2024 Netscout Systems Inc. All Rights Reserved.
#
# App for NetScout Omnis Cyber Intelligence
#
# Provides dashboard visualization and investigation drill downs for CI log data in Splunk.
#
# Depends On: OmnisCyberInvestigator.

CHANGELOG
0.1.0 - Initial Release
0.1.1 - Added copyright/do not edit headers to all default config files, updated installation instructions.  Adjusted layout of threat_indicators dashboard to better accommodate smaller screens.
0.1.2
  - Threat Indicators Dashboard:
    - Removed mapping.
    - Added panels for summary counts for Protocol Risk and DDoS to top of page.  Click to reveal the relevant details.
    - For each category's panels: Changed from single value with sparkline to single value stats sum with a timechart.
    - Rewrote searches to utilize a base search.
  - Threat Drilldown Dashboard:
    - Turned on auto-run.
    - Removed "other" from time charts
    - Added conditions to show/hide IP addresses in the table based on aggregated vs base events.
  - Added link in nav bar to go straight to CyberInvestigator web UI.  On first click it will bring you to the NAV customization page to enter your URL.
0.1.8 (9/27/19) - changed source field for alias NetScoutNsaUrl. Added "Cyber Threats" view to dashboard
0.1.9 (31/10/19) - changed views to not use the cat field, as it is no longer supported, catogories now being Cyber Threats, Threat Indicators or Security Risks.
0.1.10 (12/11/19) - added user defined metrics screens to "Security Risks" view
6.2.2 (03/12/19) - changed version to match ATA version
6.3.0 (26/02/20) - updated to support 6.3.0, fixed issue with drilldowns from Splunk 8.0.x
6.3.0 (14/05/20) - Name and branding changes to sGenius Cyber Investigator
6.3.2 (18/03/21) - Name and branding changes to Omnis Cyber Investigator
6.3.3 (27/08/21) - Updates to support new format for events in release 6.3.3
6.3.4 (24/03/22) - Updates to support new features in release 6.3.4, Attack surface discovery and IDS, name change to Omnis Cyber Intelligence
6.3.5 (05/05/23) - Updates and new views for release 6.3.5, events format changes
6.4.0 (18/03/24) - Updates to support new event type File Detection


INSTALLATION

Install this app on search heads.

CONFIGURATION

Edit the macro NetScoutNsaIndex to set the index to search for netscout:nsa data in the dashboards.  This is based on where you are sending the data to be indexed (typically in an inputs.conf in TA-netscout_nsa.)
