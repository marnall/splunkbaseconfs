Copyright (C) 2005-2014 Splunk Inc. All Rights Reserved.

Add-on:             Splunk for Cisco Security
Last Modified:	    2016-07-22
Splunk Version:	    6.0 or Higher
Author:             Splunk Labs

The Splunk for Cisco Security app provides reports and dashboards that give you visual insight into your data from Cisco 
Security Devices, including the Cisco ASA, PIX, FWSM, ESA, ISE, IPS, Sourcefire, and WSA devices.

=======
Last Modified:	    July 22, 2016
Splunk Version:	    6.0 or higher
Author:             Splunk

The Cisco Security Suite provides a single pane of glass interface into Cisco security data. It supports Cisco ASA and PIX firewall appliances, the FWSM firewall services module, the WSA web security appliance, and the Cisco Identity Services Engine (ISE).

##### Known Issues ####
3.1.2
- Package name still has "Splunk_" prefix. This is required if keeping same Splunkbase path yet this app is no longer Splunk supported
- splunkdConnectionTimeout may still need to be set artificially high on Windows boxes for setup experience 

##### What's New #####
3.1.2
- Moved root README to README.txt
- Removed the transforms "cisco-wsa-usage" as it was not used in any props, views, searches, or macros
- Removed cisco_wsa_usage.csv from lookups as it was not used in any transforms, views, searches, or macros
- Restored transforms stanza cisco-wsa-userid which was merged with and corrupting stanza cisco-wsa-ntdomain
- Removed transforms stanza cisco-wsa-category as it was not used in any props, views, searches, or macros
- Removed cisco_wsa_categories.csv from lookups as it was not used in any views, searches, or macros
- Removed cisco_wsa_categories from transforms
- Removed README file from lookups folder
- Removed message_catalog.csv from lookups as it was not used in any transforms, views, searches, or macros
- Renamed transforms stanza cisco_wsa_proxy_action_lookup to css_wsa_proxy_action_lookup, renamed its lookup filename from cisco_wsa_proxy_action_lookup.csv to css_wsa_proxy_actions.csv, and updated props entry to match (per best practices & to avoid conflict with WSA TA)
- Introduced event type named css-wsa-squid to replace cisco-wsa-squid (was in WAS TA version 3.1 and dropped in WSA TA version 3.2) && updated saved searches and views to use the new event type 
- Introduced event type named css-ise to replace cisco-ise (was in ISE TA version 2.1 and dropped in ISE TA version 2.2) && updated saved searches and views to use the new event type 
- Appended SfeS-estreamer-logs macro with "OR sourcetype=cisco:sourcefire" to accommodate latest versions of TA source typing

3.1.1
- Report Acceleration in saved searches where applicable
- Warning message on setup page for uninstalled Add-on
3.1.0
- Support for Cisco IPS added
- Setup routine added

3.0.2
- Support for Cisco ESA added
- Documentation updates

3.0.1
- Support for Cisco ISE added
- WSA Add-on moved to a separate package

3.0.0 (02.20.2014)
- Major update to the app.
- Completely rewritten for Splunk Enterprise 6 with support for Cisco ASA, PIX, FWSM and WSA

2.0 (04.01.12)
- Major updaate to the app.
- Completely change the look and feel of the app.
- Refactor the code base.
>>>>>>> develop


+++ Initial Configuration +++

1) Install the Splunk_CiscoSecuritySuite App
2) Install the approprite TAs
3) Restart your server
4) Logon to your Splunk Instance
5) Follow the instructions within the app under Cisco Security Suite -> Documentation

+++ Important Note about Upgrading +++

Several of the Cisco TA's in the past recorded events with a sourcetype of (for example) cisco_asa.  The new TA's use
the ES3 compliant sourcetype (for example) cisco:asa.  If you want to view your old events, then alter the various
eventtypes included in the packages so that they include the old data.
=======

Documentation is now included in the app.  Once the app is installed, navigate to the “Help” menu.

