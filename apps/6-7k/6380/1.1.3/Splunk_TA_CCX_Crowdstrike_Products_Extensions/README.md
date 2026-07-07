**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Crowdstrike Products Extensions looks to provide additional field extraction and CIM compliance for Crowdstrike log sources captured via the Add-on CrowdStrike Falcon Event Streams Technical Add-On or CrowdStrike Falcon Spotlight Vulnerability Data.

This Technical Add-on does not replace the public Splunk Add-on for CrowdStrike Falcon Event Streams (https://splunkbase.splunk.com/app/5082/) or CrowdStrike Falcon Spotlight Vulnerability Data (https://splunkbase.splunk.com/app/6167) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sourcetypes "crowdstrike:spotlight:vulnerability:json", "CrowdStrike:Event:Streams:JSON", and "crowdstrike:filevantage:json" including the following log subtypes:

- ActivityAuditEvent
- IdentityProtectionEvent
- CustomerIOCEvent
- IdpDetectionSummaryEvent
- IncidentSummaryEvent
- ScheduledReportNotificationEvent
- RemoteResponseSessionStartEvent
- RemoteResponseSessionEndEvent
- EppDetectionSummaryEvent
- XdrDetectionSummaryEvent
- DataProtectionDetectionSummaryEvent

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Authentication, Change, Alerts, Data Acess, Data Loss Prevention (DLP), Vulnerabilities, Intrusion Detection (IDS) and Malware.

**Compatibility:**
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Crowdstrike |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed following the installation guidance.
- Install Add-on CrowdStrike Falcon Event Streams Technical Add-On (https://splunkbase.splunk.com/app/5082/) version 2.1.2 or higher
- Install Add-on CrowdStrike Falcon Spotlight Vulnerability Data (https://splunkbase.splunk.com/app/6167) version 3.1.5 or higher

**Installation**
This Add-on is intended to be installed as follows:

- Splunk Cloud Victoria STACKs: Installed on Search Head
- Splunk Cloud Classic STACKs: Installed on Search Heads, IDM and Indexers
- Splunk Enterprise: Installed on Search Heads, Forwarders, and Indexers

This Add-on is intended to be installed as a companion for the following add-ons:

- Install Add-on CrowdStrike Falcon Event Streams Technical Add-On (https://splunkbase.splunk.com/app/5082/) version 2.1.2 or higher
- Install Add-on CrowdStrike Falcon Spotlight Vulnerability Data (https://splunkbase.splunk.com/app/6167) version 3.1.5 or higher

**New Release**

- Enhacements on CIM compliance fields and values for CrowdStrike Event Streams logs (sourcetype "CrowdStrike:Event:Streams:JSON")
- Remap legacy fields in the Event Stremas API

**Known issues:**

- Modify manually "Field Alias": FIELDALIAS-src CrowdStrike:Event:Streams:JSON : FIELDALIAS-src - event.UserIp ASNEW ip
- Modify manually "Eventtype": copy the eventtype search from authentication_audit_event from CCX Extensions Add-on into default authentication_audit_event
- Modify manually "Calculated Field": copy "Calculated Fields" search "action", "user", "description", and "severity" from CCX Extensions Add-on into the default configuration

**Addressed issues:**

- Additional evaluation for field "aid" - "event.AgentId" from "EppDetectionSummaryEvent"
