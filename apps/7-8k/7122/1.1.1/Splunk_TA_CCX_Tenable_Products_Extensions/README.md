**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Tenable Products looks to provide additional field extraction and CIM compliance for Tenable log sources captured via "Tenable Add-On for Splunk" and "Tenable WAS Add-On for Splunk".

This Technical Add-on does not replace the public Splunk Add-on for Tenable (https://splunkbase.splunk.com/app/4060) or Tenable WAS Add-On for Splunk (https://splunkbase.splunk.com/app/6884) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sourcetypes:

- "tenable:ot:alerts" (Tenable.ot)
- "tenable:io:vuln:was" (Tenable WAS)

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Data Acess, Intrusion Detection (IDS), Malware, Network Traffic, and Vulnerability .

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Tenable |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed following the installation guide.
- Install Tenable Add-On for Splunk (https://splunkbase.splunk.com/app/4060) version 8.0.0 or higher
- Install Tenable WAS Add-On for Splunk (https://splunkbase.splunk.com/app/6884) version 1.1.0 or higher

**Installation**
This Add-on is intended to be installed as follows:
- Splunk Cloud Victoria or Classic STACKs: Installed on Search Heads
- Splunk Enterprise: Installed on Search Heads

This Add-on is intended to be installed as a companion for the following add-ons:
- Install Tenable Add-On for Splunk (https://splunkbase.splunk.com/app/4060) version 8.0.0 or higher
- Install Tenable WAS Add-On for Splunk (https://splunkbase.splunk.com/app/6884) version 1.1.0 or higher

**Known issues:**
- Disable Field Transformation "auto_kv_tenable_ot" from TA-tenable to stop field extraction conflict
- Modify permissions on Field extractions "auto_kv_tenable_ot" from TA-tenable to App (Global >> App)
