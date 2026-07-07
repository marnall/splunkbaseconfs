**About Us:**

CyberCX is the Australia’s greatest force of cyber security. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Unified Splunk Add-On for Citrix looks to provide a single field extraction bundle for Citrix Systems.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for;
- Citrix Systems - Syslog

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Inventory, Intrusion Detection (IDS), Malware, Network Traffic, Network Session, and Web.

**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Service Provider | CyberCX |
| Vendor Products | Citrix Systems |

**Requirements:**

- This Add-On is intended to be installed on Heavy Forwarders and Search Heads.

**Installation:**

- This Add-On is intended to be installed on Heavy Forwarders and Search Heads.
- Is recommended to use separate index per Citrix Systems technology.

**Known issues:**

- Currently not parsing truncated "Message" events for Citrix Netscaler ADC.

**Addressed Issues:**

- Revised REGEX extractions.   
- Additional and revised CIM fields covering Citrix Netscaler ADC log verbosity.
- New eventtypes and revised tags.
 