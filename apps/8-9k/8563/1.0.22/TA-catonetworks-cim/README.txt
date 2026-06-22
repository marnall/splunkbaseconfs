================================================================================
Cato Networks CIM Add-on for Splunk
================================================================================

Version: 1.0.0
Author: Cato Networks
Support: support@catonetworks.com

================================================================================
OVERVIEW
================================================================================

Cato Networks provides a cloud-native, single-vendor SASE platform that converges networking and security in a global cloud service. The Cato Networks CIM Add-on for Splunk normalizes Cato platform events and flow telemetry to the Splunk Common Information Model (CIM).

The add-on includes field extractions, tags, and data model mappings that enable Cato telemetry to integrate with CIM-based applications such as Splunk Enterprise Security.

The add-on maps Cato networking and security events to the following CIM data models:
* Network Traffic
* Intrusion Detection
* Network Resolution (DNS)
* Web
* Authentication
* Malware
* Change (Account Management)

================================================================================
SUPPORTED CIM DATA MODELS
================================================================================

1. Network Traffic (All_Traffic)
   - Flow data from Cato network sessions
   - Internet Firewall events
   
2. Intrusion Detection (IDS_Attacks)
   - IPS events
   - Suspicious Activity events
   - Adaptive Threat Prevention events
   
3. Network Resolution (DNS)
   - DNS Protection events
   
4. Web (Web)
   - Apps Security (CASB) events
   - SaaS Security API Data Protection events
   
5. Authentication (Authentication)
   - Application Sign-In events
   - Connected events (VPN/Site connections)
   
6. Malware (Malware_Attacks)
   - Anti-Malware events
   - NG Anti-Malware events
   
7. Change (Account_Management)
   - Admin user management events
   - User account events
   - Account operations events
   - LDAP/SCIM provisioning events

================================================================================
REQUIREMENTS
================================================================================

- Splunk Enterprise 8.0+ or Splunk Cloud 9.0+
- Splunk Common Information Model (CIM) Add-on 4.0+
- Cato Networks data ingested via HEC (HTTP Event Collector)

================================================================================
INSTALLATION
================================================================================

This Technology Add-on is available on Splunkbase and can be installed directly
from the Splunk Web interface.


================================================================================
CONFIGURATION
================================================================================

No additional configuration is required after installation.

The add-on automatically applies CIM mappings to:
- Source: cato:hec:events (Cato security events)
- Source: cato:hec:flows (Cato network flow data)

Ensure your Cato data is being ingested with these source values.

================================================================================
DATA SOURCES
================================================================================

This add-on expects data from Cato Networks with the following characteristics:

Events (source=cato:hec:events):
- JSON format
- Contains event_type and event_sub_type fields
- Ingested via Splunk HEC

Flows (source=cato:hec:flows):
- JSON format
- Contains network flow/session data
- Ingested via Splunk HEC

================================================================================
VERIFICATION
================================================================================

After installation, verify the CIM mappings are working:

1. Check Network Traffic data model:
   | datamodel Network_Traffic All_Traffic search
   | search vendor="Cato Networks"
   | head 10

2. Check Intrusion Detection data model:
   | datamodel Intrusion_Detection IDS_Attacks search
   | search vendor="Cato Networks"
   | head 10

3. Check DNS data model:
   | datamodel Network_Resolution DNS search
   | search vendor="Cato Networks"
   | head 10

4. Check Web data model:
   | datamodel Web Web search
   | search vendor="Cato Networks"
   | head 10

5. Check Authentication data model:
   | datamodel Authentication Authentication search
   | search vendor="Cato Networks"
   | head 10

6. Check Malware data model:
   | datamodel Malware Malware_Attacks search
   | search vendor="Cato Networks"
   | head 10

7. Check Change data model:
   | datamodel Change All_Changes search
   | search vendor="Cato Networks"
   | head 10

================================================================================
TROUBLESHOOTING
================================================================================

No data appearing in CIM data models:
--------------------------------------
1. Verify Cato data is being ingested:
   source=cato:hec:events OR source=cato:hec:flows | head 10

2. Check that events have the correct source:
   index=* sourcetype=cato:* | stats count by source

3. Verify the Cato Networks Technical Add-On is enabled:
   Settings → Apps → Manage Apps → Find "Cato Networks"

4. Restart Splunk after installation

Field mappings not working:
----------------------------
1. Check props.conf is being applied:
   | rest /services/properties/props/source::cato:hec:events

2. Verify field aliases are active:
   index=* source=cato:hec:events | head 1 | fields src dest action

3. Check for conflicting apps that might override field mappings

CIM data model searches are slow:
----------------------------------
1. Enable data model acceleration:
   Settings → Data models → Select model → Edit → Acceleration
   
2. Ensure sufficient time range for acceleration to build

3. Consider using tstats for better performance:
   | tstats count from datamodel=Network_Traffic where vendor="Cato Networks"

================================================================================
SUPPORT
================================================================================

For issues, questions, or feature requests:

- Email: support@catonetworks.com
- Documentation: https://support.catonetworks.com
- Cato Management Application: https://cc2.catonetworks.com

================================================================================
RELEASE NOTES
================================================================================

Version 1.0.0 (Current)
-----------------------
- Initial release with CIM mappings for 7 data models
- Support for Cato security events and network flows
- Field aliases for all CIM-required fields
- Event type and tag definitions
- Splunk Cloud compatible

================================================================================
LICENSE
================================================================================

Copyright (c) 2026 Cato Networks
All rights reserved.

This Technology Add-on is proprietary software owned by Cato Networks.
Unauthorized copying, distribution, or modification is prohibited.

================================================================================

