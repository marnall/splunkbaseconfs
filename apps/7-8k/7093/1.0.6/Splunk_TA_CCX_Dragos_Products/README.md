**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Splunk Add-on for Dragos Products looks to provide a single field extraction bundle for Dragos logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA avaliable for:

- Dragos Sitestore - Syslog

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts and Intrusion Detection (IDS), and Vulnerability.

**Compatibility:**

| Splunk Enterprise versions | 10.0, 9.4 9.3, 9.2, 9.1 |
| -------------------------- | ----------------------- |
| CIM                        | 6.x, 5.x                |
| Platforms                  | Platform independent    |
| Vendor Products            | Dragos                  |
| Service Provider           | CyberCX                 |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and Splunk Forwarder where syslog input is configured.

**Installation**
The CCX Add-on for Dragos Products supports the following inputs:

**Dragos SiteStore (HEC inputs)**
- Splunk Cloud Victoria or Classic STACKs: Installed on Search Heads.
- Splunk Enterprise: Installed on Search Heads and Splunk Forwarder.
- Main sourcetype to be selected as part of inputs configuration: "ccx:dragos:sitestore".

**Dragos OT Threat Intelligence (Dragos OT Add-On for Splunk - API Inputs)**
- Install the Add-on Dragos OT Add-On for Splunk (https://splunkbase.splunk.com/app/6450) on Splunk Heavy Forwarder.

- Install CCX Add-on for Dragos Products on the SH (Splunk Cloud or Enterprise)

**Known issues:**
- (none)

**Addressed Issues**
- Fixed reference cycle issue in the lookup for sourcetype "dragos:notifications"
