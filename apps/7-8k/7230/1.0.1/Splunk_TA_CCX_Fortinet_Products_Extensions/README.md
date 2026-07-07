**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Fortinet Products looks to provide additional field extraction and CIM compliance for Fortinet Fortigate syslog logs preparsed using the Add-on "Fortinet FortiGate Add-On for Splunk".

This Technical Add-on does not replace the public Splunk Add-on for Fortinet FortiGate (https://splunkbase.splunk.com/app/2846) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance support for the following sourcetypes:  

- fortigate_traffic
- fortigate_utm
- fortigate_anomaly
- fortigate_event

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Email, Intrusion Detection (IDS), Malware, Network Traffic, Network Session, Performance, and Web.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Fortinet Firewall |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed following the installation guide.
- Install Add-on Fortinet FortiGate Add-On for Splunk (https://splunkbase.splunk.com/app/2846) version 1.6.9 or higher

**Installation**
This Add-on is intended to be installed as follows:
- Splunk Cloud Victoria STACKs: Installed on Search Head
- Splunk Cloud Classic STACKs: Installed on Search Heads
- Splunk Enterprise: Installed on Search Heads

This Add-on is intended to be installed as a companion for the following add-on:
- Install Add-on Fortinet FortiGate Add-On for Splunk (https://splunkbase.splunk.com/app/2846) version 1.6.9 or higher


**Known issues:**
- Modify manually "Tags": disable tag value paris for the eventtype "ftnt_fortigate_virus"
- Modify manually "Calculated Field" (fortigate_utm): copy "Calculated Fields" search "signature", "category", and app from CCX Add-on for Fortinet Products into the default configuration
