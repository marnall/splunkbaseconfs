Cato Networks Security App for Splunk
======================================

Version: 1.0.0
Author: Cato Networks
Support: support@catonetworks.com

OVERVIEW
--------
Cato Networks provides a cloud-native, single-vendor SASE platform that converges networking and security in a global cloud service.

The Cato Networks Security App for Splunk provides dashboards, searches, and visualizations for monitoring and investigating activity across the Cato platform.

This application helps security and operations teams analyze network and security events,
investigate threats, and monitor activity across their Cato deployment.

Current content includes a threats dashboard that provides an overview of security threats and related activity across the Cato platform.
The dashboard presents aggregated insights such as threat volumes, timelines, top affected entities (for example hosts, users, or domains),
and other high-level security indicators.

REQUIREMENTS
------------
- Splunk Enterprise 8.0 or later
- Cato Networks data ingested via HEC (HTTP Event Collector)

INSTALLATION
------------
Install from Splunkbase or upload the .spl file via Apps → Manage Apps → Install app from file.

CONFIGURATION
-------------
1. Ensure Cato Networks data is being ingested into Splunk via HEC
2. Navigate to the "Cato Networks Security App for Splunk" in Splunk
3. Access the Threats dashboard to view security activity

FEATURES
--------
- Threats Dashboard: Real-time view of security threats detected by Cato SASE
- Pre-configured searches for Cato security events
- Drill-down capabilities for detailed threat investigation

SUPPORT
-------
For support, please contact: support@catonetworks.com
Documentation: https://support.catonetworks.com/

RELEASE NOTES
-------------
Version 1.0.0
- Initial release
- Threats dashboard with real-time threat detection and analysis
- Aggregated insights including threat volumes, timelines, and top affected entities

